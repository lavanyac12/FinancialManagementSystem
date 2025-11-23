# main.py
from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.parse import StatementParser
from backend.auth import get_current_user
import os
from dotenv import load_dotenv
from supabase import create_client
import joblib
from pathlib import Path
import json
from pydantic import BaseModel, Field, validator
from decimal import Decimal, ROUND_HALF_UP

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def _normalize_decimal_for_db(d: Decimal):
    """Return an int if `d` has no fractional part, otherwise a float.

    This helps when the Postgres column is integer but our Pydantic model
    uses Decimal with 2 decimal places (e.g. 5.00) which would be sent as
    5.0 and can trigger "invalid input syntax for type integer: \"5.0\"".
    """
    try:
        if d == d.to_integral_value():
            return int(d)
        return float(d)
    except Exception:
        try:
            fv = float(d)
            if fv.is_integer():
                return int(fv)
            return fv
        except Exception:
            return d

# Load category model if present
MODEL_PATH = os.getenv("CATEGORY_MODEL_PATH", "backend/models/tx_category_model.joblib")
category_model = None

# Try to resolve the path relative to the project root
if not os.path.isabs(MODEL_PATH):
    # If running from project root, this should work
    model_path_resolved = Path(MODEL_PATH)
    if not model_path_resolved.exists():
        # Try relative to this file's directory
        model_path_resolved = Path(__file__).parent / "models" / "tx_category_model.joblib"
else:
    model_path_resolved = Path(MODEL_PATH)

if model_path_resolved.exists():
    try:
        category_model = joblib.load(str(model_path_resolved))
        print(f"Loaded category model from {model_path_resolved}")
    except Exception as e:
        print(f"Failed to load category model: {e}")
        category_model = None
else:
    print(f"Category model not found at {model_path_resolved}. Skipping categorization until a model is available.")


# New insert logic using Supabase Python client in batch mode
def insert_transactions_supabase(transactions):
    """Insert a list of transaction dicts into the `transactions` table.
    
    Includes category_id and category_confidence when present from categorization.
    Handles missing column errors gracefully by retrying without the problematic field.
    """
    try:
        # Build payload: include core fields and optional category fields when present
        payload = []
        for tx in transactions:
            mapped = {
                "date": tx.get("date"),
                "description": tx.get("description"),
                "amount": tx.get("amount"),
                "transaction_type": tx.get("transaction_type"),
            }
            # include optional category fields if they exist (added by categorize_transactions)
            if tx.get("category_id") is not None:
                mapped["category_id"] = tx.get("category_id")
            # Note: category_confidence not included - column doesn't exist in DB schema
            payload.append(mapped)

        print(f"🔄 Inserting {len(payload)} transactions. Sample payload: {payload[0] if payload else 'empty'}")
        response = supabase.table("transactions").insert(payload).execute()
        print(f"✓ Insert response: data={len(response.data) if hasattr(response, 'data') and response.data else 0} rows")
        print(f"📋 Full response object: {response}")
        # If PostgREST returned an error object, try to handle missing column errors gracefully
        err = getattr(response, "error", None)
        if err:
            print(f"Error detected: {err}")
            try:
                # error may be dict-like with 'message'
                msg = err.get("message") if isinstance(err, dict) else str(err)
            except Exception:
                msg = str(err)
            # detect missing column pattern
            if msg and "Could not find the '" in msg:
                import re

                m = re.search(r"Could not find the '(.+?)' column", msg)
                if m:
                    col = m.group(1)
                    print(f"Column '{col}' not found in DB, retrying without it...")
                    # remove the offending column from all payloads and retry once
                    for p in payload:
                        if col in p:
                            del p[col]
                    # retry
                    response_retry = supabase.table("transactions").insert(payload).execute()
                    print(f"✓ Retry succeeded: {len(response_retry.data) if hasattr(response_retry, 'data') and response_retry.data else 0} rows")
                    return response_retry
        return response
    except Exception as exception:
        print(f"Exception during insert: {exception}")
        import traceback
        traceback.print_exc()
        return exception


def categorize_transactions(transactions):
    """Add `category_id` (and optional `category_confidence`) to each transaction using the loaded model.
    The model is expected to accept a list of descriptions and produce labels matching your `category_id` values.
    """
    if category_model is None:
        print("Category model not loaded - skipping categorization")
        return transactions

    descriptions = [t.get("description", "") or "" for t in transactions]
    try:
        preds = category_model.predict(descriptions)
        print(f"Model predictions: {preds[:5]}...")  # Show first 5 predictions
    except Exception as e:
        print("Prediction failed:", e)
        return transactions

    # Attempt to get probabilities if supported
    probs = None
    try:
        prob_arr = category_model.predict_proba(descriptions)
        # take max prob for predicted class
        probs = prob_arr.max(axis=1).tolist()
    except Exception:
        probs = [None] * len(preds)

    # Use hard-coded mapping of category name -> id (provided by system)
    hardcoded_map = {
        "transit": 1,
        "dining": 2,
        "food": 2,
        "groceries": 3,
        "grocery": 3,
        "other": 4,
        "shopping": 5,
        "subscription": 6,
        "subscriptions": 6,
        "home": 7,
        "rent": 7,
    }

    for t, p, conf in zip(transactions, preds, probs):
        try:
            # If model returned a numeric label (string digits or int), use it directly
            if isinstance(p, str) and p.isdigit():
                t["category_id"] = int(p)
            elif isinstance(p, int):
                t["category_id"] = p
            else:
                cat_name = str(p).strip()
                if cat_name == "":
                    # leave category unset
                    continue

                # normalize for mapping/lookups
                cat_key = cat_name.lower()

                # first try hardcoded mapping
                if cat_key in hardcoded_map:
                    t["category_id"] = hardcoded_map[cat_key]
                    print(f"✓ Mapped '{cat_name}' -> category_id {hardcoded_map[cat_key]}")
                else:
                    # attempt to find or create the category in the `categories` table
                    try:
                        # Try exact match first
                        resp = supabase.table("categories").select("id,name").eq("name", cat_name).execute()
                        data = None
                        err = None
                        if isinstance(resp, dict):
                            data = resp.get("data")
                            err = resp.get("error")
                        else:
                            data = getattr(resp, "data", None)
                            err = getattr(resp, "error", None)

                        if err:
                            # if there's an error reading categories, fallback to leaving unset
                            print("Category lookup error:", err)
                        else:
                            if data and len(data) > 0:
                                # found existing category
                                t["category_id"] = data[0].get("id")
                            else:
                                # create the category
                                insert_resp = supabase.table("categories").insert({"name": cat_name}).select("id").execute()
                                i_data = None
                                i_err = None
                                if isinstance(insert_resp, dict):
                                    i_data = insert_resp.get("data")
                                    i_err = insert_resp.get("error")
                                else:
                                    i_data = getattr(insert_resp, "data", None)
                                    i_err = getattr(insert_resp, "error", None)

                                if i_err:
                                    print("Category insert error:", i_err)
                                else:
                                    if i_data and len(i_data) > 0:
                                        t["category_id"] = i_data[0].get("id")
                    except Exception as e:
                        print("Category resolution failed:", e)
        except Exception:
            # fallback: assign raw prediction if it's an int-like
            try:
                if isinstance(p, int):
                    t["category_id"] = p
            except Exception:
                pass

        # attach optional confidence if available
        if conf is not None:
            try:
                t["category_confidence"] = float(conf)
            except Exception:
                t["category_confidence"] = None

        # ensure we don't include a 'category' key that could break schema
        if "category" in t:
            t.pop("category")

    return transactions


def update_monthly_income(transactions):
    """Aggregate credit transactions by month (MM-YY) and upsert into public.income.

    - Expects each transaction to have `date`, `transaction_type`, and `amount`.
    - `transaction_type` matching is case-insensitive and checks for the string 'credit'.
    - Month format stored as `MM-YY` (e.g. '03-25').
    """
    from datetime import datetime

    def parse_month_key(date_val):
        if not date_val:
            return None
        if isinstance(date_val, datetime):
            return date_val.strftime("%m-%y")
        s = str(date_val).strip()
        fmts = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
        ]
        for f in fmts:
            try:
                d = datetime.strptime(s, f)
                return d.strftime("%m-%y")
            except Exception:
                continue
        try:
            parts = [p for p in s.replace("-","/").split("/") if p]
            if len(parts) >= 3:
                mm = int(parts[0]); yy = int(parts[2])
                if yy > 31:
                    yy_short = yy % 100
                else:
                    yy_short = yy
                return f"{mm:02d}-{yy_short:02d}"
        except Exception:
            pass
        return None

    monthly = {}
    for t in transactions:
        try:
            ttype = (t.get("transaction_type") or "").strip().lower()
            if ttype != "credit":
                continue
            amt = t.get("amount")
            if amt is None:
                continue
            try:
                a = float(amt)
                # Treat credit amounts as positive values (some feeds use negative numbers for credits)
                a = abs(a)
            except Exception:
                try:
                    a = float(str(amt).replace("$","").replace(",",""))
                    a = abs(a)
                except Exception:
                    continue
            month_key = parse_month_key(t.get("date"))
            if not month_key:
                continue
            monthly[month_key] = monthly.get(month_key, 0.0) + a
        except Exception:
            continue

    for month_key, total in monthly.items():
        try:
            # ensure total is positive and round to 2 decimals for money
            total_pos = round(abs(total), 2)
            resp = supabase.table("income").select("month,income").eq("month", month_key).execute()
            data = None
            err = None
            if isinstance(resp, dict):
                data = resp.get("data")
                err = resp.get("error")
            else:
                data = getattr(resp, "data", None)
                err = getattr(resp, "error", None)

            if err:
                print("Warning: income table lookup error:", err)
                continue

            if data and len(data) > 0:
                upd = supabase.table("income").update({"income": total_pos}).eq("month", month_key).execute()
                print(f"Updated income for {month_key}: {total_pos}", upd)
            else:
                ins = supabase.table("income").insert({"month": month_key, "income": total_pos}).execute()
                print(f"Inserted income for {month_key}: {total_pos}", ins)
        except Exception as e:
            print("Failed to upsert income for", month_key, e)

    # After updating monthly income, recompute and persist amount_saved for all goals
    try:
        try:
            total_income = _get_total_income()
        except Exception as e:
            print("Failed to compute total income for goals update:", e)
            total_income = Decimal("0.00")

        # fetch all goals
        resp = supabase.table("goals").select("goal_id,income_allocation").execute()
        goals_data = None
        if isinstance(resp, dict):
            goals_data = resp.get("data")
        else:
            goals_data = getattr(resp, "data", None)

        if goals_data:
            for g in goals_data:
                try:
                    gid = g.get("goal_id") if isinstance(g, dict) else None
                    raw_alloc = g.get("income_allocation") if isinstance(g, dict) else None
                    if raw_alloc is None:
                        alloc = Decimal("0")
                    else:
                        alloc = Decimal(str(raw_alloc))

                    new_amount = (total_income * (alloc / Decimal(100))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    # write back to DB
                    upd = supabase.table("goals").update({"amount_saved": float(new_amount)}).eq("goal_id", gid).execute()
                    print(f"Updated goal {gid} amount_saved -> {new_amount}", getattr(upd, 'data', None) or (upd.get('data') if isinstance(upd, dict) else None))
                except Exception as e:
                    print("Failed to update goal amount_saved for goal:", g, e)
    except Exception as e:
        print("Failed to persist updated goal savings:", e)


# FastAPI App
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/parse-statement")
async def parse_statement(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Protected endpoint: requires a valid Supabase JWT in the Authorization header."""
    file_bytes = await file.read()
    transactions = StatementParser.parse_statement(file_bytes, file.filename)
    # Diagnostics: show parsed count
    parsed_count = len(transactions)

    if parsed_count == 0:
        return {"message": "No transactions parsed from file.", "parsed_count": 0}

    # categorize transactions using trained model (if available)
    transactions = categorize_transactions(transactions)
    
    # Debug: check if any transactions have category_id
    categorized_count = sum(1 for t in transactions if t.get("category_id") is not None)
    print(f"📊 Categorized {categorized_count}/{parsed_count} transactions")
    
    # Use Supabase batch insert
    result = insert_transactions_supabase(transactions)
    if isinstance(result, Exception):
        return {"error": str(result), "parsed_count": parsed_count}

    # After successful insert, update monthly income aggregates (Credit transactions)
    try:
        update_monthly_income(transactions)
    except Exception as e:
        print("Failed to update monthly income:", e)

    # result.data usually contains inserted rows; result.count may also be present
    inserted_rows = None
    try:
        # Some supabase client returns {'data': [...], 'count': None}
        inserted_rows = result.data
    except Exception:
        inserted_rows = None

    return {
        "message": f"Parsed {parsed_count} transactions.",
        "parsed_count": parsed_count,
        "inserted_count": len(inserted_rows) if inserted_rows is not None else 0,
        "supabase_response": inserted_rows,
        "raw_response": str(result),
    }


@app.get("/")
def read_root():
    return {"message": "API is running"}


# --- Smart Goals API -----------------------------------------------------


class SmartGoalIn(BaseModel):
    name: str = Field(..., max_length=50)
    target_amount: Decimal = Field(...)
    income_allocation: Decimal = Field(...)

    @validator("target_amount")
    def target_amount_positive(cls, v):
        try:
            fv = float(v)
        except Exception:
            raise ValueError("target_amount must be numeric")
        if fv <= 1:
            raise ValueError("target_amount must be greater than 1")
        # round to 2 decimals
        return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @validator("income_allocation")
    def allocation_range(cls, v):
        try:
            fv = float(v)
        except Exception:
            raise ValueError("income_allocation must be numeric")
        if fv < 0 or fv > 99:
            raise ValueError("income_allocation must be between 0 and 99")
        # store as Decimal with up to 2 decimals
        return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _get_total_income():
    """Return the total income sum from `public.income` as Decimal (sum of all months)."""
    try:
        resp = supabase.table("income").select("income").execute()
        data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
        total = Decimal("0.00")
        if data:
            for row in data:
                try:
                    val = row.get("income") if isinstance(row, dict) else None
                    if val is None:
                        continue
                    total += Decimal(str(val))
                except Exception:
                    continue
        return total
    except Exception as e:
        print("Failed to read income table:", e)
        return Decimal("0.00")


@app.get("/smart-goals")
def list_smart_goals():
    """Return list of smart goals from `public.goals`."""
    try:
        resp = supabase.table("goals").select("*").execute()
        data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
        return {"goals": data or []}
    except Exception as e:
        return {"error": str(e)}


def _insert_goal_record(payload: dict):
    # try inserting into public.goals
    try:
        resp = supabase.table("goals").insert(payload).execute()
        return resp
    except Exception as e:
        print("Failed to insert goal:", e)
        raise


@app.post("/smart-goals")
def create_smart_goal(goal_in: SmartGoalIn):
    """Create a Smart Goal, compute allocated amount_saved based on income allocations, and save to DB."""
    total_income = _get_total_income()
    alloc_pct = goal_in.income_allocation
    allocated = (total_income * (alloc_pct / Decimal(100))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    payload = {
        "name": goal_in.name,
        "target_amount": float(goal_in.target_amount),
        "income_allocation": _normalize_decimal_for_db(goal_in.income_allocation),
        "amount_saved": float(allocated),
    }

    try:
        resp = _insert_goal_record(payload)
        return {"message": "Goal created", "goal": getattr(resp, "data", None) or resp.get("data")}
    except Exception as e:
        return {"error": str(e)}


@app.put("/smart-goals/{goal_id}")
def update_smart_goal(goal_id: int, goal_in: SmartGoalIn):
    """Update an existing Smart Goal and recompute amount_saved based on allocation."""
    total_income = _get_total_income()
    alloc_pct = goal_in.income_allocation
    allocated = (total_income * (alloc_pct / Decimal(100))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    payload = {
        "name": goal_in.name,
        "target_amount": float(goal_in.target_amount),
        "income_allocation": _normalize_decimal_for_db(goal_in.income_allocation),
        "amount_saved": float(allocated),
    }

    try:
        resp = supabase.table("goals").update(payload).eq("goal_id", goal_id).execute()
        return {"message": "Goal updated", "result": getattr(resp, "data", None) or resp.get("data")}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/smart-goals/{goal_id}")
def delete_smart_goal(goal_id: int):
    """Delete a Smart Goal by goal_id."""
    try:
        resp = supabase.table("goals").delete().eq("goal_id", goal_id).execute()
        return {"message": "Goal deleted", "result": getattr(resp, "data", None) or resp.get("data")}
    except Exception as e:
        return {"error": str(e)}

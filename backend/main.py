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

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        print(f"✓ Loaded category model from {model_path_resolved}")
    except Exception as e:
        print(f"❌ Failed to load category model: {e}")
        category_model = None
else:
    print(f"⚠️  Category model not found at {model_path_resolved}. Skipping categorization until a model is available.")


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
            print(f"❌ Error detected: {err}")
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
                    print(f"⚠️  Column '{col}' not found in DB, retrying without it...")
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
        print(f"❌ Exception during insert: {exception}")
        import traceback
        traceback.print_exc()
        return exception


def categorize_transactions(transactions):
    """Add `category_id` (and optional `category_confidence`) to each transaction using the loaded model.
    The model is expected to accept a list of descriptions and produce labels matching your `category_id` values.
    """
    if category_model is None:
        print("⚠️  Category model not loaded - skipping categorization")
        return transactions

    descriptions = [t.get("description", "") or "" for t in transactions]
    try:
        preds = category_model.predict(descriptions)
        print(f"✓ Model predictions: {preds[:5]}...")  # Show first 5 predictions
    except Exception as e:
        print("❌ Prediction failed:", e)
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

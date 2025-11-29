# main.py
from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.parse import FileReader
from backend.auth import Authenticator, getCurrentUser
import os
from dotenv import load_dotenv
from supabase import create_client
import joblib
from pathlib import Path
import json
from pydantic import BaseModel, Field, validator
from decimal import Decimal, ROUND_HALF_UP
from backend.insights import Insights

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def _normalize_decimal_for_db(d: Decimal):
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

class Categorizer:
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        MODEL_PATH = os.getenv("CATEGORY_MODEL_PATH", "backend/models/tx_category_model.joblib")
        
        if not os.path.isabs(MODEL_PATH):
            model_path_resolved = Path(MODEL_PATH)
            if not model_path_resolved.exists():
                model_path_resolved = Path(__file__).parent / "models" / "tx_category_model.joblib"
        else:
            model_path_resolved = Path(MODEL_PATH)
        
        if model_path_resolved.exists():
            try:
                self.model = joblib.load(str(model_path_resolved))
                print(f"Loaded category model from {model_path_resolved}")
            except Exception as e:
                print(f"Failed to load category model: {e}")
                self.model = None
        else:
            print(f"Category model not found at {model_path_resolved}. Skipping categorization until a model is available.")
    
    def categorizeTransaction(self, transactions):
        if self.model is None:
            print("Category model not loaded - skipping categorization")
            return transactions
        
        descriptions = [t.get("description", "") or "" for t in transactions]
        try:
            preds = self.model.predict(descriptions)
            print(f"Model predictions: {preds[:5]}...")
        except Exception as e:
            print("Prediction failed:", e)
            return transactions
        probs = None
        try:
            prob_arr = self.model.predict_proba(descriptions)
            probs = prob_arr.max(axis=1).tolist()
        except Exception:
            probs = [None] * len(preds)
        
        categoryMap = {
            "transit": 1, "dining": 2, "food": 2,
            "groceries": 3, "grocery": 3, "other": 4,
            "shopping": 5, "subscription": 6, "subscriptions": 6,
            "home": 7, "rent": 7,
        }
        
        for t, p, conf in zip(transactions, preds, probs):
            try:
                if isinstance(p, str) and p.isdigit():
                    t["category_id"] = int(p)
                elif isinstance(p, int):
                    t["category_id"] = p
                else:
                    cat_name = str(p).strip()
                    if cat_name == "":
                        continue
                    
                    cat_key = cat_name.lower()
                    
                    if cat_key in categoryMap:
                        t["category_id"] = categoryMap[cat_key]
                        print(f"✓ Mapped '{cat_name}' -> category_id {categoryMap[cat_key]}")
                    else:
                        try:
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
                                print("Category lookup error:", err)
                            else:
                                if data and len(data) > 0:
                                    t["category_id"] = data[0].get("id")
                                else:
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
                try:
                    if isinstance(p, int):
                        t["category_id"] = p
                except Exception:
                    pass
            
            if conf is not None:
                try:
                    t["category_confidence"] = float(conf)
                except Exception:
                    t["category_confidence"] = None
            
            if "category" in t:
                t.pop("category")
        
        return transactions

categorizer = Categorizer()
category_model = categorizer.model


class Transaction:
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    def getTransactionData(self, filters=None):
        try:
            query = self.supabase.table("transactions").select("*")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.data if hasattr(response, 'data') else []
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return []
    
    def insertTransaction(self, transactions):
        try:
            payload = []
            for tx in transactions:
                mapped = {
                    "date": tx.get("date"),
                    "description": tx.get("description"),
                    "amount": tx.get("amount"),
                    "transaction_type": tx.get("transaction_type"),
                }
                if tx.get("category_id") is not None:
                    mapped["category_id"] = tx.get("category_id")
                payload.append(mapped)

            print(f"🔄 Inserting {len(payload)} transactions. Sample payload: {payload[0] if payload else 'empty'}")
            response = self.supabase.table("transactions").insert(payload).execute()
            print(f"✓ Insert response: data={len(response.data) if hasattr(response, 'data') and response.data else 0} rows")
            print(f"📋 Full response object: {response}")
            err = getattr(response, "error", None)
            if err:
                print(f"Error detected: {err}")
                try:
                    msg = err.get("message") if isinstance(err, dict) else str(err)
                except Exception:
                    msg = str(err)
                if msg and "Could not find the '" in msg:
                    import re

                    m = re.search(r"Could not find the '(.+?)' column", msg)
                    if m:
                        col = m.group(1)
                        print(f"Column '{col}' not found in DB, retrying without it...")
                        for p in payload:
                            if col in p:
                                del p[col]
                        response_retry = self.supabase.table("transactions").insert(payload).execute()
                        print(f"✓ Retry succeeded: {len(response_retry.data) if hasattr(response_retry, 'data') and response_retry.data else 0} rows")
                        return response_retry
            return response
        except Exception as exception:
            print(f"Exception during insert: {exception}")
            import traceback
            traceback.print_exc()
            return exception
    
    def calculateIncome(self, transactions):
        from datetime import datetime

        def parseMonthKey(date_val):
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
                    a = abs(a)
                except Exception:
                    try:
                        a = float(str(amt).replace("$","").replace(",",""))
                        a = abs(a)
                    except Exception:
                        continue
                month_key = parseMonthKey(t.get("date"))
                if not month_key:
                    continue
                monthly[month_key] = monthly.get(month_key, 0.0) + a
            except Exception:
                continue

        for month_key, total in monthly.items():
            try:
                total_pos = round(abs(total), 2)
                resp = self.supabase.table("income").select("month,income").eq("month", month_key).execute()
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
                    upd = self.supabase.table("income").update({"income": total_pos}).eq("month", month_key).execute()
                    print(f"Updated income for {month_key}: {total_pos}", upd)
                else:
                    ins = self.supabase.table("income").insert({"month": month_key, "income": total_pos}).execute()
                    print(f"Inserted income for {month_key}: {total_pos}", ins)
            except Exception as e:
                print("Failed to upsert income for", month_key, e)

        try:
            try:
                total_income = getTotalIncome()
            except Exception as e:
                print("Failed to compute total income for goals update:", e)
                total_income = Decimal("0.00")

            resp = self.supabase.table("goals").select("goal_id,income_allocation").execute()
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
                        upd = self.supabase.table("goals").update({"amount_saved": float(new_amount)}).eq("goal_id", gid).execute()
                        print(f"Updated goal {gid} amount_saved -> {new_amount}", getattr(upd, 'data', None) or (upd.get('data') if isinstance(upd, dict) else None))
                    except Exception as e:
                        print("Failed to update goal amount_saved for goal:", g, e)
        except Exception as e:
            print("Failed to persist updated goal savings:", e)


transaction = Transaction(supabase_client=supabase)

def insertTransaction(transactions):
    return transaction.insertTransaction(transactions)

def categorizeTransaction(transactions):
    return categorizer.categorizeTransaction(transactions)

def calculateIncome(transactions):
    return transaction.calculateIncome(transactions)

insights = Insights(supabase_client=supabase, transaction_handler=transaction)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/parse-statement")
async def parseTransaction(file: UploadFile = File(...), user=Depends(getCurrentUser)):
    file_bytes = await file.read()
    transactions = FileReader.parseTransaction(file_bytes, file.filename)
    parsed_count = len(transactions)

    if parsed_count == 0:
        return {"message": "No transactions parsed from file.", "parsed_count": 0}

    transactions = categorizeTransaction(transactions)
    
    categorized_count = sum(1 for t in transactions if t.get("category_id") is not None)
    print(f"📊 Categorized {categorized_count}/{parsed_count} transactions")
    
    result = insertTransaction(transactions)
    if isinstance(result, Exception):
        return {"error": str(result), "parsed_count": parsed_count}

    try:
        calculateIncome(transactions)
    except Exception as e:
        print("Failed to update monthly income:", e)

    inserted_rows = None
    try:
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
def readRoot():
    return {"message": "API is running"}

class SmartGoal(BaseModel):
    name: str = Field(..., max_length=50)
    target_amount: Decimal = Field(...)
    income_allocation: Decimal = Field(...)

    @validator("target_amount")
    def validateTargetAmount(cls, v):
        try:
            fv = float(v)
        except Exception:
            raise ValueError("target_amount must be numeric")
        if fv <= 1:
            raise ValueError("target_amount must be greater than 1")
        return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @validator("income_allocation")
    def allocateIncome(cls, v):
        try:
            fv = float(v)
        except Exception:
            raise ValueError("income_allocation must be numeric")
        if fv < 0 or fv > 99:
            raise ValueError("income_allocation must be between 0 and 99")
        return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def getTotalIncome():
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
def listSmartGoals():
    try:
        resp = supabase.table("goals").select("*").execute()
        data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
        return {"goals": data or []}
    except Exception as e:
        return {"error": str(e)}


def insertGoalRecord(payload: dict):
    try:
        resp = supabase.table("goals").insert(payload).execute()
        return resp
    except Exception as e:
        print("Failed to insert goal:", e)
        raise


@app.post("/smart-goals")
def createSmartGoal(goal_in: SmartGoal):
    total_income = getTotalIncome()
    alloc_pct = goal_in.income_allocation
    allocated = (total_income * (alloc_pct / Decimal(100))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    payload = {
        "name": goal_in.name,
        "target_amount": float(goal_in.target_amount),
        "income_allocation": _normalize_decimal_for_db(goal_in.income_allocation),
        "amount_saved": float(allocated),
    }

    try:
        resp = insertGoalRecord(payload)
        return {"message": "Goal created", "goal": getattr(resp, "data", None) or resp.get("data")}
    except Exception as e:
        return {"error": str(e)}


@app.put("/smart-goals/{goal_id}")
def editSmartGoal(goal_id: int, goal_in: SmartGoal):
    total_income = getTotalIncome()
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


@app.get("/categories")
def getCategoryNames(auth_payload: dict = Depends(getCurrentUser)):
    try:
        resp = supabase.table("category").select("category_id, category_name").execute()
        return {"categories": getattr(resp, "data", None) or resp.get("data")}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/smart-goals/{goal_id}")
def deleteSmartGoal(goal_id: int):
    try:
        resp = supabase.table("goals").delete().eq("goal_id", goal_id).execute()
        return {"message": "Goal deleted", "result": getattr(resp, "data", None) or resp.get("data")}
    except Exception as e:
        return {"error": str(e)}

@app.get("/insights")
def getInsights(auth_payload: dict = Depends(getCurrentUser)):
    try:
        budget = None     
        report = insights.generateReport(budget_data=budget)
        return report
    except Exception as e:
        return {"error": str(e), "insights": []}

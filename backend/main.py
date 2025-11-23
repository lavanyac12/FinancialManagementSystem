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
if Path(MODEL_PATH).exists():
    try:
        category_model = joblib.load(MODEL_PATH)
        print(f"Loaded category model from {MODEL_PATH}")
    except Exception as e:
        print("Failed to load category model:", e)
        category_model = None
else:
    print(f"Category model not found at {MODEL_PATH}. Skipping categorization until a model is available.")


# New insert logic using Supabase Python client in batch mode
def insert_transactions_supabase(transactions):
    try:
        # Build payload without category/category_id since source files do not include category.
        # This keeps insert payload minimal and compatible with the current DB schema
        # where category is optional or will be populated later by other logic.
        payload = []
        for tx in transactions:
            mapped = {
                "date": tx.get("date"),
                "description": tx.get("description"),
                "amount": tx.get("amount"),
                "transaction_type": tx.get("transaction_type"),
            }
            payload.append(mapped)

        response = supabase.table("transactions").insert(payload).execute()
        response = supabase.table("transactions").insert(transactions).execute()
        # If PostgREST returned an error object, try to handle missing column errors gracefully
        err = getattr(response, "error", None)
        if err:
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
                    # remove the offending column from all transactions and retry once
                    for t in transactions:
                        if col in t:
                            del t[col]
                    # retry
                    response_retry = supabase.table("transactions").insert(transactions).execute()
                    return response_retry
        return response
    except Exception as exception:
        return exception


def categorize_transactions(transactions):
    """Add `category_id` (and optional `category_confidence`) to each transaction using the loaded model.
    The model is expected to accept a list of descriptions and produce labels matching your `category_id` values.
    """
    if category_model is None:
        return transactions

    descriptions = [t.get("description", "") or "" for t in transactions]
    try:
        preds = category_model.predict(descriptions)
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
            if isinstance(p, str) and p.isdigit():
                t["category_id"] = int(p)
            else:
                cat_name = str(p).strip().lower()
                if cat_name == "":
                    # leave category unset
                    continue
                # first try hardcoded mapping
                if cat_name in hardcoded_map:
                    t["category_id"] = hardcoded_map[cat_name]
                else:
                    # Do not query the `category` table; rely only on the hard-coded map.
                    # If the predicted label doesn't match the hard-coded names, leave `category_id` unset.
                    pass
        except Exception:
            # fallback: assign raw prediction if it's an int-like
            try:
                if isinstance(p, int):
                    t["category_id"] = p
            except Exception:
                pass
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
        "inserted_count": len(inserted_rows) if inserted_rows is not None else None,
        "supabase_response": inserted_rows,
        "raw_response": str(result),
    }


@app.get("/")
def read_root():
    return {"message": "API is running"}

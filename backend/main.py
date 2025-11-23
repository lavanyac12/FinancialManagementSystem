# main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from backend.parse import StatementParser
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
        response = supabase.table("transactions").insert(transactions).execute()
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

    for t, p, conf in zip(transactions, preds, probs):
        # keep types compatible with your DB: if p is numeric string cast to int
        try:
            if isinstance(p, str) and p.isdigit():
                t["category_id"] = int(p)
            else:
                t["category_id"] = p
        except Exception:
            t["category_id"] = p
        if conf is not None:
            try:
                t["category_confidence"] = float(conf)
            except Exception:
                t["category_confidence"] = None
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
async def parse_statement(file: UploadFile = File(...)):
    file_bytes = await file.read()
    transactions = StatementParser.parse_statement(file_bytes, file.filename)
    # categorize transactions using trained model (if available)
    transactions = categorize_transactions(transactions)
    # Use Supabase batch insert
    result = insert_transactions_supabase(transactions)
    if isinstance(result, Exception):
        return {"error": str(result)}
    return {"message": f"Inserted {len(transactions)} transactions into Supabase.", "supabase_response": result.data}


@app.get("/")
def read_root():
    return {"message": "API is running"}

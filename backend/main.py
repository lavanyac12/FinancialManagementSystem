# main.py
from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.parse import StatementParser
from backend.auth import get_current_user
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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
        return response
    except Exception as exception:
        return exception


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

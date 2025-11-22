# main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from backend.parse import StatementParser
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
        response = supabase.table("transactions").insert(transactions).execute()
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
async def parse_statement(file: UploadFile = File(...)):
    file_bytes = await file.read()
    transactions = StatementParser.parse_statement(file_bytes, file.filename)
    # Use Supabase batch insert
    result = insert_transactions_supabase(transactions)
    if isinstance(result, Exception):
        return {"error": str(result)}
    return {"message": f"Inserted {len(transactions)} transactions into Supabase.", "supabase_response": result.data}


@app.get("/")
def read_root():
    return {"message": "API is running"}

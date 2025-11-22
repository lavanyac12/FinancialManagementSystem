# main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from backend.parse import StatementParser

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/parse-statement")
async def parse_statement(file: UploadFile = File(...)):
    file_bytes = await file.read()
    transactions = StatementParser.parse_statement(file_bytes, file.filename)
    return transactions

@app.get("/")
def read_root():
    return {"message": "API is running"}
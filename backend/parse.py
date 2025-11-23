import pandas as pd
import io
from fastapi import HTTPException
from datetime import datetime

MAX_FILE_SIZE_MB = 10
REQUIRED_COLUMNS = ["Date", "Description", "Amount", "Type of Transaction"]

class StatementParser:
    """
    Handles:
    - File validation
    - Structural validation
    - Parsing into clean transaction dictionaries
    """

    @staticmethod
    def validate_file(file_bytes: bytes, filename: str):
        # --- File size validation ---
        size_in_mb = len(file_bytes) / (1024 * 1024)
        if size_in_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum allowed size is 10MB."
            )

        # --- File type validation ---
        if not (filename.endswith(".csv") or filename.endswith(".xlsx") or filename.endswith(".xls")):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Please upload a CSV or Excel file."
            )

    @staticmethod
    def load_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Could not read file. Please upload a valid CSV or Excel file."
            )
        return df

    @staticmethod
    def validate_columns(df: pd.DataFrame):
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file structure. Missing required columns: {', '.join(missing)}."
            )

    @staticmethod
    def clean_and_parse(df: pd.DataFrame):
        transactions = []

        for _, row in df.iterrows():
            # --- Validate each field ---
            if pd.isna(row["Amount"]) or row["Amount"] == "":
                raise HTTPException(
                    status_code=400,
                    detail="Invalid data: Missing or corrupted Amount values."
                )

            try:
                amount = float(row["Amount"])
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Amount format. Amount must be numeric."
                )

            try:
                date_value = pd.to_datetime(row["Date"])
                date_value = date_value.strftime("%Y-%m-%d")
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Date format. Please ensure all dates are valid."
                )

            description = str(row["Description"]).strip()
            tx_type = str(row["Type of Transaction"]).strip()

            transactions.append({
                "date": date_value,
                "description": description,
                "amount": amount,
                "transaction_type": tx_type,
            })

        return transactions

    @staticmethod
    def parse_statement(file_bytes: bytes, filename: str):
        """
        High-level function:
        1. Validate file
        2. Load dataframe
        3. Validate structure
        4. Clean & convert
        5. Return transaction list
        """
        StatementParser.validate_file(file_bytes, filename)
        df = StatementParser.load_dataframe(file_bytes, filename)
        StatementParser.validate_columns(df)

        transactions = StatementParser.clean_and_parse(df)
        return transactions

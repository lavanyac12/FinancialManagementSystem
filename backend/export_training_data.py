# export_training_data.py
# Exports (description, category_id) pairs from Supabase to a CSV for training.
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def exportToCSV(csv_path="training_data.csv"):
    resp = supabase.table("transactions").select("description, category_id").execute()
    if resp.error:
        raise RuntimeError(f"Supabase error: {resp.error}")
    data = resp.data or []
    if not data:
        print("No labeled transactions found in `transactions` table.")
        return
    df = pd.DataFrame(data)
    df = df.dropna(subset=["description", "category_id"])
    df["category_id"] = df["category_id"].astype(str)
    df["description"] = df["description"].astype(str).str.strip().str.lower()
    df.to_csv(csv_path, index=False)
    print(f"Exported {len(df)} rows to {csv_path}")

if __name__ == "__main__":
    exportToCSV()

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import os
import requests
from dotenv import load_dotenv

# Ensure .env is loaded when this module is imported (helps when main.py
# imports this module before calling load_dotenv itself).
load_dotenv()

security = HTTPBearer()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the incoming Supabase JWT by calling Supabase's /auth/v1/user endpoint.

    Requires SUPABASE_URL and SUPABASE_KEY to be configured in environment (.env).
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="SUPABASE_URL and SUPABASE_KEY must be set on the server")

    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_KEY,
    }

    try:
        resp = requests.get(f"{SUPABASE_URL}/auth/v1/user", headers=headers, timeout=5)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Auth provider error: {exc}")

    if resp.status_code != 200:
        # Try to include response body for debugging if present
        detail = resp.text or "Invalid token"
        raise HTTPException(status_code=401, detail=f"Invalid token: {detail}")

    return resp.json()

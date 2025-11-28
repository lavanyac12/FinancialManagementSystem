from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import os
import requests
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class Authenticator:
    
    def __init__(self, supabase_url=None, supabase_key=None):
        self.supabase_url = supabase_url or SUPABASE_URL
        self.supabase_key = supabase_key or SUPABASE_KEY
    
    def verifyCredentials(self, token: str):
        if not self.supabase_url or not self.supabase_key:
            raise HTTPException(status_code=500, detail="SUPABASE_URL and SUPABASE_KEY must be set on the server")
        
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": self.supabase_key,
        }
        
        try:
            resp = requests.get(f"{self.supabase_url}/auth/v1/user", headers=headers, timeout=5)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Auth provider error: {exc}")
        
        if resp.status_code != 200:
            detail = resp.text or "Invalid token"
            raise HTTPException(status_code=401, detail=f"Invalid token: {detail}")
        
        return resp.json()

authenticator = Authenticator()

def getCurrentUser(credentials: HTTPAuthorizationCredentials = Security(security)):
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
        detail = resp.text or "Invalid token"
        raise HTTPException(status_code=401, detail=f"Invalid token: {detail}")

    return resp.json()

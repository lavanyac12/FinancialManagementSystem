from db import supabase

def test_connection():
    response = supabase.table("users").select("*").execute()
    print(response.data)

if __name__ == "__main__":
    test_connection()
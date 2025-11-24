# Add this endpoint to main.py to recategorize existing transactions

@app.post("/recategorize-transactions")
async def recategorize_existing_transactions(user=Depends(get_current_user)):
    """Recategorize all existing transactions that don't have a category_id"""
    try:
        # Fetch transactions without category
        response = supabase.table("transactions").select("*").is_("category_id", "null").execute()
        
        if isinstance(response, dict):
            transactions = response.get("data", [])
        else:
            transactions = getattr(response, "data", [])
        
        if not transactions:
            return {"message": "No uncategorized transactions found", "updated": 0}
        
        # Categorize them
        categorized = categorize_transactions(transactions)
        
        # Update each transaction
        updated_count = 0
        for tx in categorized:
            if tx.get("category_id"):
                update_data = {"category_id": tx["category_id"]}
                # Assuming transactions have an 'id' or unique identifier
                # You may need to adjust this based on your schema
                result = supabase.table("transactions").update(update_data).eq("description", tx["description"]).eq("date", tx["date"]).eq("amount", tx["amount"]).execute()
                updated_count += 1
        
        return {"message": f"Recategorized {updated_count} transactions", "updated": updated_count}
    except Exception as e:
        return {"error": str(e)}

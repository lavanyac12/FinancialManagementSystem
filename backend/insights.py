from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

class Insights:
    def __init__(self, supabase_client, transaction_handler=None, user_id: Optional[str] = None):
        self.supabase = supabase_client
        self.transaction_handler = transaction_handler
        self.user_id = user_id
        self._categories_cache = None
    
    def _fetch_transactions(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch transactions using Transaction class handler."""
        if self.transaction_handler:
            filters = {'user_id': self.user_id} if self.user_id else None
            return self.transaction_handler.getTransactionData(filters=filters)
        else:
            # Fallback to direct query if no transaction handler provided
            try:
                query = self.supabase.table("transactions").select("*")
                if self.user_id:
                    query = query.eq("user_id", self.user_id)
                response = query.execute()
                return response.data if hasattr(response, 'data') else []
            except Exception as e:
                print(f"Error fetching transactions: {e}")
                return []
    
    def _fetch_categories(self, force_refresh: bool = False) -> Dict[int, str]:
        if self._categories_cache is None or force_refresh:
            try:
                response = self.supabase.table("categories").select("id,name").execute()
                data = response.data if hasattr(response, 'data') else []
                self._categories_cache = {cat['id']: cat['name'] for cat in data}
            except Exception as e:
                print(f"Error fetching categories: {e}")
                self._categories_cache = {}
        
        return self._categories_cache
    
    def generateReport(self, transaction_data=None, budget_data=None) -> Dict[str, Any]:
        if transaction_data is None:
            transaction_data = self._fetch_transactions()
        
        try:
            total_expenses = sum(
                abs(t.get("amount", 0)) 
                for t in transaction_data 
                if t.get("transaction_type", "").lower() == "debit"
            )
            
            total_income = sum(
                abs(t.get("amount", 0)) 
                for t in transaction_data 
                if t.get("transaction_type", "").lower() == "credit"
            )
            
            categories = self._fetch_categories()
            category_spending = defaultdict(float)
            for t in transaction_data:
                if t.get("transaction_type", "").lower() == "debit":
                    cat_id = t.get("category_id")
                    amount = abs(t.get("amount", 0))
                    cat_name = categories.get(cat_id, "Uncategorized")
                    category_spending[cat_name] += amount
            
            highest_category = None
            highest_amount = 0
            if category_spending:
                highest_category, highest_amount = max(
                    category_spending.items(), 
                    key=lambda x: x[1]
                )
            
            overspending = total_expenses > budget_data if budget_data else False
            
            insights = []
            
            if total_expenses > 0:
                insights.append(f"Total expenses: ${total_expenses:.2f}")
            
            if total_income > 0:
                insights.append(f"Total income: ${total_income:.2f}")
                
            if total_income > 0 and total_expenses > 0:
                savings = total_income - total_expenses
                savings_rate = (savings / total_income) * 100
                insights.append(f"Net savings: ${savings:.2f}")
                insights.append(f"Savings rate: {savings_rate:.1f}%")
            
            if highest_category:
                insights.append(f"Highest spending: {highest_category} (${highest_amount:.2f})")
            
            if overspending:
                insights.append("⚠️ You are over budget!")
            
            return {
                "total_expenses": round(total_expenses, 2),
                "total_income": round(total_income, 2),
                "net_savings": round(total_income - total_expenses, 2),
                "overspending": overspending,
                "category_spending": dict(category_spending),
                "insights": insights
            }
        except Exception as e:
            print(f"Error generating insights: {e}")
            return {
                "total_expenses": 0,
                "total_income": 0,
                "net_savings": 0,
                "overspending": False,
                "category_spending": {},
                "insights": ["Unable to generate insights"]
            }
    
    def generateGraphReport(self, data=None) -> Dict[str, Any]:
        if data is None:
            data = self._fetch_transactions()
        
        daily_spending = defaultdict(float)
        for t in data:
            if t.get("transaction_type", "").lower() == "debit":
                date = t.get("date")
                amount = abs(t.get("amount", 0))
                daily_spending[date] += amount
        
        return {
            "daily_spending": dict(daily_spending),
            "transaction_count": len(data)
        }
    
    def requestTransaction(self) -> List[Dict[str, Any]]:
        return self._fetch_transactions(force_refresh=True)
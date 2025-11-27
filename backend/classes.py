"""Domain classes wrapping existing functional logic.

These classes are lightweight facades over already implemented functions/endpoints.
They DO NOT introduce new required attributes or behavior; they simply
organize existing logic in an object-oriented manner aligned with the
provided class diagram. Missing diagram methods/attributes are intentionally
omitted if no underlying implementation exists.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from decimal import Decimal

# Import existing logic without altering functionality
from backend.parse import StatementParser
from backend.main import (
    categorize_transactions,
    insert_transactions_supabase,
    update_monthly_income,
    _get_total_income,
)
from backend.auth import get_current_user  # used by Authenticator facade

# Optional import for training model (only if called)
try:
    from backend.train_classifier import build_and_train as _train_model
except Exception:  # pragma: no cover
    _train_model = None

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None

# Supabase client reuse (avoid re-instantiating in endpoints). If existing main creates one, prefer injection.


@dataclass
class FileReader:
    """Facade over statement parsing utilities."""
    filename: Optional[str] = None
    file_bytes: Optional[bytes] = None

    def validate_file(self) -> None:
        if self.file_bytes is None or self.filename is None:
            raise ValueError("file_bytes and filename must be set before validation")
        StatementParser.validate_file(self.file_bytes, self.filename)

    def parse_transactions(self) -> List[Dict[str, Any]]:
        if self.file_bytes is None or self.filename is None:
            raise ValueError("file_bytes and filename must be set before parsing")
        return StatementParser.parse_statement(self.file_bytes, self.filename)


@dataclass
class Transaction:
    """Represents a single financial transaction."""
    date: str
    description: str
    amount: float
    transaction_type: str
    category_id: Optional[int] = None
    category_confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "date": self.date,
            "description": self.description,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
        }
        if self.category_id is not None:
            d["category_id"] = self.category_id
        if self.category_confidence is not None:
            d["category_confidence"] = self.category_confidence
        return d

    def update_category(self, category_id: int, confidence: Optional[float] = None) -> None:
        self.category_id = category_id
        self.category_confidence = confidence

    @staticmethod
    def bulk_insert(transactions: List['Transaction']):
        payload = [t.to_dict() for t in transactions]
        return insert_transactions_supabase(payload)


class Categorizer:
    """Applies ML categorization to parsed transactions and (optionally) retrains model."""

    @staticmethod
    def categorize(raw_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return categorize_transactions(raw_transactions)

    @staticmethod
    def train(csv_path: str, model_out: str = "backend/models/tx_category_model.joblib", **kwargs) -> Optional[str]:
        if _train_model is None:
            raise RuntimeError("Training functionality unavailable: sklearn or training module not loaded")
        _train_model(csv_path, model_out, **kwargs)
        return model_out


@dataclass
class SmartGoal:
    """Represents a savings goal and operations similar to existing endpoints."""
    goal_id: Optional[int] = None
    name: str = ""
    target_amount: Decimal = Decimal("0")
    income_allocation: Decimal = Decimal("0")
    amount_saved: Decimal = Decimal("0")

    @staticmethod
    def compute_allocated_amount(income_allocation: Decimal) -> Decimal:
        total_income = _get_total_income()
        return (total_income * (income_allocation / Decimal(100))).quantize(Decimal("0.01"))

    @classmethod
    def create(cls, supabase_client, name: str, target_amount: Decimal, income_allocation: Decimal):
        allocated = cls.compute_allocated_amount(income_allocation)
        payload = {
            "name": name,
            "target_amount": float(target_amount),
            "income_allocation": float(income_allocation),
            "amount_saved": float(allocated),
        }
        resp = supabase_client.table("goals").insert(payload).execute()
        data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
        first = data[0] if data else {}
        return cls(
            goal_id=first.get("goal_id"),
            name=first.get("name", name),
            target_amount=target_amount,
            income_allocation=income_allocation,
            amount_saved=allocated,
        )

    def update(self, supabase_client):
        allocated = self.compute_allocated_amount(self.income_allocation)
        payload = {
            "name": self.name,
            "target_amount": float(self.target_amount),
            "income_allocation": float(self.income_allocation),
            "amount_saved": float(allocated),
        }
        supabase_client.table("goals").update(payload).eq("goal_id", self.goal_id).execute()
        self.amount_saved = allocated
        return self

    @staticmethod
    def list(supabase_client) -> List[Dict[str, Any]]:
        resp = supabase_client.table("goals").select("*").execute()
        return getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else [])

    def delete(self, supabase_client) -> None:
        if self.goal_id is None:
            raise ValueError("goal_id required to delete")
        supabase_client.table("goals").delete().eq("goal_id", self.goal_id).execute()


class CategoryService:
    """Lightweight access to category data."""
    @staticmethod
    def list_categories(supabase_client) -> List[Dict[str, Any]]:
        resp = supabase_client.table("category").select("category_id, category_name").execute()
        return getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else [])


class Authenticator:
    """Wraps existing token validation for potential OO usage."""
    @staticmethod
    def get_user(credentials):
        return get_current_user(credentials)


class FileCategorizationWorkflow:
    """High-level helper composing FileReader + Categorizer + persistence."""
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def ingest(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        reader = FileReader(filename=filename, file_bytes=file_bytes)
        reader.validate_file()
        transactions = reader.parse_transactions()
        if not transactions:
            return {"parsed_count": 0, "inserted_count": 0, "message": "No transactions parsed"}

        categorized = Categorizer.categorize(transactions)
        insert_result = insert_transactions_supabase(categorized)

        try:
            update_monthly_income(categorized)
        except Exception as e:  # pragma: no cover
            print("Monthly income update failed:", e)

        inserted_rows = getattr(insert_result, "data", None) or (insert_result.get("data") if isinstance(insert_result, dict) else None)
        return {
            "parsed_count": len(transactions),
            "inserted_count": len(inserted_rows) if inserted_rows else 0,
            "supabase_response": inserted_rows,
        }

__all__ = [
    "FileReader",
    "Transaction",
    "Categorizer",
    "SmartGoal",
    "CategoryService",
    "Authenticator",
    "FileCategorizationWorkflow",
]

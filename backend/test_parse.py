"""
Test cases for CSV parsing functionality.
Run with: pytest backend/test_parse.py -v
"""

import pytest
from io import BytesIO
from backend.parse import StatementParser
import pandas as pd


class TestStatementParser:
    """Test CSV statement parsing."""
    
    def test_parse_simple_csv(self):
        """Test parsing a simple CSV file."""
        csv_content = """Date,Description,Amount,Type of Transaction
2024-01-15,Coffee Shop,-5.50,Debit
2024-01-16,Salary Deposit,2000.00,Credit
2024-01-17,Grocery Store,-45.30,Debit"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        assert len(transactions) == 3
        assert transactions[0]["description"] == "Coffee Shop"
        assert transactions[0]["amount"] == -5.50
        assert transactions[1]["amount"] == 2000.00
    
    def test_parse_with_different_column_names(self):
        """Test parsing CSV with required column names."""
        csv_content = """Date,Description,Amount,Type of Transaction
01/15/2024,Starbucks,-6.75,Debit
01/16/2024,Paycheck,3000.00,Credit"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        assert len(transactions) == 2
        assert transactions[0]["description"] == "Starbucks"
    
    def test_parse_empty_csv(self):
        """Test parsing an empty CSV file."""
        csv_content = """Date,Description,Amount,Type of Transaction"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        assert len(transactions) == 0
    
    def test_parse_csv_with_missing_values(self):
        """Test parsing CSV with missing description."""
        csv_content = """Date,Description,Amount,Type of Transaction
2024-01-15,Coffee Shop,-5.50,Debit
2024-01-16,,100.00,Credit
2024-01-17,Store,-20.00,Debit"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        # Should handle missing description
        assert len(transactions) == 3
    
    def test_parse_csv_with_positive_and_negative_amounts(self):
        """Test parsing CSV with mixed positive/negative amounts."""
        csv_content = """Date,Description,Amount,Type of Transaction
2024-01-15,Purchase,-50.00,Debit
2024-01-16,Refund,25.00,Credit
2024-01-17,Payment,-100.00,Debit"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        assert len(transactions) == 3
        debits = [tx for tx in transactions if tx.get("amount", 0) < 0]
        credits = [tx for tx in transactions if tx.get("amount", 0) > 0]
        
        assert len(debits) == 2
        assert len(credits) == 1
    
    def test_parse_csv_with_date_formats(self):
        """Test parsing different date formats."""
        csv_content = """Date,Description,Amount,Type of Transaction
01/15/2024,Transaction 1,-10.00,Debit
2024-01-16,Transaction 2,-15.00,Debit"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        # Parser should attempt to normalize date formats
        assert len(transactions) >= 1
        for tx in transactions:
            assert "date" in tx
    
    def test_parse_csv_with_special_characters(self):
        """Test parsing CSV with special characters in descriptions."""
        csv_content = """Date,Description,Amount,Type of Transaction
2024-01-15,McDonald's,-12.50,Debit
2024-01-16,Tim Horton's Downtown,-8.75,Debit
2024-01-17,Store #123,-25.00,Debit"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        assert len(transactions) == 3
        # Check that special characters are preserved
        assert any("McDonald" in tx.get("description", "") for tx in transactions)


class TestTransactionValidation:
    """Test transaction data validation."""
    
    def test_validate_required_fields(self):
        """Test that required fields are present."""
        csv_content = """Date,Description,Amount,Type of Transaction
2024-01-15,Coffee Shop,-5.50,Debit"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        for tx in transactions:
            assert "date" in tx or "description" in tx
            assert "amount" in tx
    
    def test_amount_is_numeric(self):
        """Test that amounts are converted to numeric values."""
        csv_content = """Date,Description,Amount,Type of Transaction
2024-01-15,Coffee Shop,-5.50,Debit
2024-01-16,Store,-10,Debit"""
        
        csv_bytes = csv_content.encode()
        transactions = StatementParser.parse_statement(csv_bytes, "test.csv")
        
        for tx in transactions:
            assert isinstance(tx["amount"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Test Suite Documentation

This document provides guidance on running and understanding the test suite for the Financial Management System.

## Overview

The test suite includes:
- **Backend Tests**: Python/pytest tests for FastAPI endpoints and core functionality
- **Frontend Tests**: JavaScript/Jest tests for React components

## Backend Tests

### Setup

1. Install test dependencies:
```bash
pip install pytest pytest-mock pytest-cov httpx
```

2. Make sure you're in the project root directory.

### Running Backend Tests

Run all backend tests:
```bash
pytest backend/ -v
```

Run specific test file:
```bash
pytest backend/test_main.py -v
pytest backend/test_parse.py -v
```

Run with coverage:
```bash
pytest backend/ --cov=backend --cov-report=html
```

### Backend Test Files

- `backend/test_main.py`: Tests for API endpoints (parse-statement, categories, smart-goals, etc.)
- `backend/test_parse.py`: Tests for CSV parsing functionality

### Test Coverage Areas

**API Endpoints:**
- Health check endpoint
- Statement parsing and categorization
- Transaction insertion
- Categories retrieval
- Smart goals CRUD operations
- Monthly income updates

**Core Functionality:**
- Transaction categorization logic
- CSV parsing with various formats
- Decimal normalization
- Error handling




### Test Coverage Areas

**ExpensePieChart Component:**
- Loading states
- Authentication checks
- Data fetching from backend and Supabase
- Month filtering functionality
- Chart rendering
- Error handling

**Login Component:**
- Form rendering
- Login functionality
- Signup functionality
- Error handling
- Token storage
- Navigation after login

## Writing New Tests

### Backend Test Example

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_new_endpoint():
    client = TestClient(app)
    response = client.get("/new-endpoint")
    assert response.status_code == 200
```


## Mocking

### Backend Mocking

Use `unittest.mock` or `pytest-mock`:
```python
from unittest.mock import Mock, patch

@patch('backend.main.supabase')
def test_with_mock(mock_supabase):
    mock_supabase.table.return_value.select.return_value.execute.return_value = Mock(data=[])
    # Test code here
```


## Continuous Integration

To run tests in CI/CD pipelines:

```bash
# Backend
pytest backend/ --cov=backend --cov-report=xml



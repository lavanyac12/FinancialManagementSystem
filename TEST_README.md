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

## Frontend Tests

### Setup

Frontend tests are configured with Create React App's built-in testing setup.

Install additional testing libraries if needed:
```bash
cd frontend
npm install --save-dev @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

### Running Frontend Tests

Run all frontend tests:
```bash
cd frontend
npm test
```

Run specific test file:
```bash
npm test ExpensePieChart.test.js
npm test Login.test.js
```

Run tests with coverage:
```bash
npm test -- --coverage --watchAll=false
```

### Frontend Test Files

- `frontend/src/ExpensePieChart.test.js`: Tests for expense pie chart component
- `frontend/src/Login.test.js`: Tests for login/authentication component

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

### Frontend Test Example

```javascript
import { render, screen } from '@testing-library/react';
import MyComponent from './MyComponent';

test('renders component', () => {
  render(<MyComponent />);
  expect(screen.getByText(/hello/i)).toBeInTheDocument();
});
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

### Frontend Mocking

Mock modules in test files:
```javascript
jest.mock('./supabaseClient', () => ({
  supabase: {
    from: jest.fn(),
  },
}));
```

## Continuous Integration

To run tests in CI/CD pipelines:

```bash
# Backend
pytest backend/ --cov=backend --cov-report=xml

# Frontend
cd frontend && npm test -- --coverage --watchAll=false
```

## Troubleshooting

### Common Issues

**Backend:**
- Import errors: Ensure `PYTHONPATH` includes project root
- Missing dependencies: Run `pip install -r requirements.txt`
- Database connection issues: Tests should mock Supabase client

**Frontend:**
- `Cannot find module`: Ensure all dependencies are installed
- Async tests failing: Use `waitFor` from `@testing-library/react`
- Chart rendering errors: Mock recharts components

### Tips

- Run tests in isolated environment (virtual env for backend)
- Clear cache if tests behave unexpectedly: `pytest --cache-clear`
- Use `-v` flag for verbose output to debug failures
- Check console logs in frontend tests for debugging

## Best Practices

1. **Write tests for new features**: Add tests whenever you add new endpoints or components
2. **Test edge cases**: Include tests for error conditions, empty data, invalid inputs
3. **Keep tests independent**: Each test should be able to run standalone
4. **Use meaningful test names**: Describe what the test is verifying
5. **Mock external dependencies**: Don't make real API calls or database queries in tests
6. **Aim for high coverage**: Try to maintain >80% code coverage

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/react)
- [Jest Documentation](https://jestjs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

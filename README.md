# Financial Management System

## Overview

Financial Management System is a full-stack web application designed to help users manage their finances efficiently. It provides secure authentication, transaction categorization, statement uploads, smart goal tracking, and real-time data visualization.

## Features

- User authentication and secure access
- Upload and parse bank statements
- Automated transaction categorization
- Smart goals tracking and management
- Interactive dashboards with expense pie charts and transaction tables
- Export and analyze financial data

## Tech Stack

- **Backend:** Python (Flask), Supabase
- **Frontend:** React.js
- **Database:** Supabase (PostgreSQL)
- **Machine Learning:** Joblib models for transaction categorization

## Folder Structure

- `backend/`: Python backend APIs, authentication, parsing, ML models
- `frontend/`: React.js frontend, UI components, charts, tables
- `models/`: Pre-trained ML models for categorization

## Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/lavanyac12/FinancialManagementSystem.git
   ```
2. Set up Python environment and install backend dependencies:
   ```
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Start the backend server:
   ```
   python main.py
   ```
4. Set up frontend dependencies:
   ```
   cd ../frontend
   npm install
   npm start
   ```

## Usage

1. Register or log in to your account.
2. Upload your bank statement and view categorized transactions.
3. Track your expenses, set smart goals, and visualize your financial data.

## License

This project is licensed under the MIT License.

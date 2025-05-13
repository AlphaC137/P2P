# P2P Lending Platform

## Overview

This is a comprehensive peer-to-peer (P2P) lending platform built with Django. The platform connects borrowers seeking loans with investors looking to earn returns on their investments. It features a modern, professional UI with Standard Bank's blue color scheme, intuitive dashboards, and a complete loan lifecycle management system.

## Features

### For Borrowers

- **Loan Creation**: Create loan requests with customizable amounts, terms, and purposes
- **Dashboard**: Track active loans, upcoming payments, and loan status
- **Verification System**: Upload identity and income documents for verification
- **Repayment Management**: Make payments and view repayment schedules
- **Credit Scoring**: System tracks payment history and calculates credit scores

### For Investors

- **Investment Dashboard**: View investment opportunities and portfolio performance
- **Diversification Tools**: Analyze investment distribution across risk levels and loan purposes
- **Returns Tracking**: Monitor expected returns and received payments
- **Investment Management**: Invest in loans and track performance

### General Features

- **Wallet System**: Deposit and withdraw funds
- **Transaction History**: Track all financial transactions
- **Loan Calculator**: Calculate monthly payments, total interest, and other loan metrics
- **Responsive Design**: Professional UI with gradients, modern cards, and responsive layouts

## Technical Architecture

### Models

#### Accounts App

- **UserProfile**: Extends Django's User model with additional fields
- **InvestorProfile**: Specific profile for investors
- **BorrowerProfile**: Specific profile for borrowers
- **Wallet**: Manages user funds
- **Transaction**: Records all financial transactions

#### Lending App

- **Loan**: Core model for loan requests and management
- **Investment**: Records investments made by investors
- **LoanPayment**: Tracks individual loan payments and schedules

#### Dashboard App

- Provides views for investor and borrower dashboards

### Key Functions

#### Loan Management

- `calculate_monthly_payment()`: Calculates monthly payment using amortization formula
- `generate_repayment_schedule()`: Creates a payment schedule for loans
- `funding_percentage`: Calculates the percentage of a loan that has been funded
- `remaining_balance`: Calculates the remaining balance on a loan

#### Wallet Operations

- `deposit_funds()`: Adds funds to a user's wallet
- `withdraw_funds()`: Withdraws funds from a user's wallet

#### Dashboard Analytics

- `investor_dashboard()`: Generates statistics and data for investor dashboards
- `borrower_dashboard()`: Generates statistics and data for borrower dashboards

## Installation and Setup

### Prerequisites

- Python 3.11+
- Django 4.2
- python-crontab 3.2.0

### Installation Steps

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Apply migrations:
   ```
   python manage.py migrate
   ```
5. Create a superuser:
   ```
   python manage.py createsuperuser
   ```
6. Run the development server:
   ```
   python manage.py runserver
   ```

### Scheduled Tasks

The platform includes scheduled tasks for processing payments and updating loan statuses:

- `process_payments.py`: Processes due payments and updates loan statuses
- `update_loan_payment_schema.py`: Updates payment schedules as needed

These can be set up as cron jobs or scheduled tasks on your server.

## UI Customization

The platform features a professional UI with Standard Bank's blue color scheme. Key styling elements include:

- **Color Scheme**: Primary blue (#0033A0) with complementary colors
- **Card Design**: Modern cards with gradients, shadows, and hover effects
- **Dashboard Layout**: Clean, organized dashboards with statistics and visualizations
- **Loan Calculator**: Interactive calculator with clear display of financial metrics

## Security Considerations

- User authentication and authorization
- Secure handling of financial transactions
- Document verification for KYC compliance
- Proper validation of all user inputs

## Future Enhancements

- Integration with payment gateways
- Mobile application
- Advanced risk assessment algorithms
- Secondary market for loan trading
- Automated investment strategies

## License

This project is proprietary and confidential. All rights reserved.

---

© 2025 P2P Lending Platform. Designed with Standard Bank's color scheme.
import os
import django
import random
import decimal
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'p2p_platform.settings')
django.setup()

# Import models
from django.contrib.auth.models import User
from accounts.models import Profile, Wallet, Transaction
from lending.models import Loan, Investment, LoanPayment

# Create sample users
def create_sample_users():
    print("Creating sample users...")
    
    # Create investors
    investors = []
    for i in range(1, 6):
        username = f"investor{i}"
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                email=f"investor{i}@example.com",
                password="password123",
                first_name=f"Investor{i}",
                last_name="Test"
            )
            profile = Profile.objects.create(
                user=user,
                user_type='investor',
                phone_number=f"555-000-{1000+i}",
                address=f"{i} Investment St, Moneyville",
                date_of_birth=datetime.now() - timedelta(days=365*30 + i*100)
            )
            wallet = Wallet.objects.create(user=user)
            investors.append(user)
            print(f"Created investor: {username}")
        else:
            investors.append(User.objects.get(username=username))
            print(f"Investor {username} already exists")
    
    # Create borrowers
    borrowers = []
    for i in range(1, 6):
        username = f"borrower{i}"
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                email=f"borrower{i}@example.com",
                password="password123",
                first_name=f"Borrower{i}",
                last_name="Test"
            )
            profile = Profile.objects.create(
                user=user,
                user_type='borrower',
                phone_number=f"555-111-{1000+i}",
                address=f"{i} Borrowing Ave, Loantown",
                date_of_birth=datetime.now() - timedelta(days=365*25 + i*100)
            )
            wallet = Wallet.objects.create(user=user)
            borrowers.append(user)
            print(f"Created borrower: {username}")
        else:
            borrowers.append(User.objects.get(username=username))
            print(f"Borrower {username} already exists")
    
    return {'investors': investors, 'borrowers': borrowers}

# Add funds to investor wallets
def fund_investor_wallets(investors):
    print("Funding investor wallets...")
    
    for investor in investors:
        wallet = investor.wallet
        initial_balance = decimal.Decimal(random.randint(5000, 20000))
        
        if wallet.balance < 1000:  # Only add funds if balance is low
            transaction = Transaction.objects.create(
                wallet=wallet,
                transaction_type='deposit',
                amount=initial_balance,
                status='completed',
                description="Initial funds deposit"
            )
            wallet.balance += initial_balance
            wallet.save()
            print(f"Funded {investor.username}'s wallet with ${initial_balance}")
        else:
            print(f"{investor.username}'s wallet already has ${wallet.balance}")

# Add starter funds to borrower wallets
def fund_borrower_wallets(borrowers):
    print("Adding starter funds to borrower wallets...")
    
    for borrower in borrowers:
        wallet = borrower.wallet
        initial_balance = decimal.Decimal(random.randint(500, 2000))
        
        if wallet.balance < 500:  # Only add funds if balance is low
            transaction = Transaction.objects.create(
                wallet=wallet,
                transaction_type='deposit',
                amount=initial_balance,
                status='completed',
                description="Initial funds deposit"
            )
            wallet.balance += initial_balance
            wallet.save()
            print(f"Funded {borrower.username}'s wallet with ${initial_balance}")
        else:
            print(f"{borrower.username}'s wallet already has ${wallet.balance}")

# Create sample loan listings
def create_sample_loans(borrowers):
    print("Creating sample loan listings...")
    
    loan_purposes = ['personal', 'business', 'education', 'debt_consolidation', 'home_improvement', 'medical', 'other']
    loan_titles = [
        "Home renovation project",
        "Starting a small business",
        "College tuition payment",
        "Debt consolidation loan",
        "Medical expenses coverage",
        "Wedding expenses",
        "Car purchase financing",
        "Travel funding",
        "Emergency funds",
        "Moving expenses"
    ]
    
    descriptions = [
        "I need a loan to renovate my kitchen and bathroom.",
        "Looking to start a small online business selling handmade crafts.",
        "Need to pay for my final year of college tuition.",
        "Consolidating several high-interest credit cards into one payment.",
        "Unexpected medical expenses that my insurance doesn't cover.",
        "Funding for my upcoming wedding in six months.",
        "Need to purchase a reliable used car for commuting to work.",
        "Planning a trip abroad and need some extra funds.",
        "Emergency fund for unexpected home repairs needed.",
        "Moving to a new city for a job and need help with expenses."
    ]
    
    loans = []
    if Loan.objects.count() < 10:  # Only create loans if we have fewer than 10
        for i in range(10):
            borrower = random.choice(borrowers)
            amount = decimal.Decimal(random.randint(1000, 10000))
            term = random.randint(6, 36)
            interest_rate = decimal.Decimal(random.uniform(5.0, 15.0)).quantize(decimal.Decimal('0.1'))
            purpose = random.choice(loan_purposes)
            
            loan = Loan.objects.create(
                borrower=borrower,
                title=loan_titles[i],
                description=descriptions[i],
                amount=amount,
                term_months=term,
                interest_rate=interest_rate,
                purpose=purpose,
                risk_score=random.randint(1, 10),
                status='pending' if i < 8 else 'funded'  # Make most loans pending, a few funded
            )
            loans.append(loan)
            print(f"Created loan: {loan.title} - ${loan.amount} for {loan.term_months} months at {loan.interest_rate}%")
    else:
        print("Sufficient loans already exist in the database")
        loans = list(Loan.objects.all()[:10])
    
    return loans

# Create sample investments
def create_sample_investments(investors, loans):
    print("Creating sample investments...")
    
    # Only invest in loans with 'pending' status
    pending_loans = [loan for loan in loans if loan.status == 'pending']
    
    if pending_loans:
        for i in range(min(15, len(pending_loans) * len(investors))):
            investor = random.choice(investors)
            loan = random.choice(pending_loans)
            
            # Make sure investor has enough funds
            wallet = investor.wallet
            available_amount = min(
                decimal.Decimal(random.randint(100, int(loan.amount / 2))),
                wallet.balance,
                loan.amount - loan.current_funded_amount
            )
            
            # Only create investment if it's meaningful
            if available_amount >= 100 and loan.current_funded_amount < loan.amount:
                # Check if this investor already invested in this loan
                existing = Investment.objects.filter(investor=investor, loan=loan).exists()
                if not existing:
                    investment = Investment.objects.create(
                        investor=investor,
                        loan=loan,
                        amount=available_amount
                    )
                    
                    # Update wallet
                    wallet.balance -= available_amount
                    wallet.save()
                    
                    # Create transaction record
                    Transaction.objects.create(
                        wallet=wallet,
                        transaction_type='investment',
                        amount=available_amount,
                        status='completed',
                        description=f"Investment in loan: {loan.title}"
                    )
                    
                    print(f"{investor.username} invested ${available_amount} in '{loan.title}'")
                    
                    # Check if loan is fully funded
                    if loan.current_funded_amount >= loan.amount:
                        loan.status = 'funded'
                        loan.save()
                        print(f"Loan '{loan.title}' is now fully funded!")
    else:
        print("No pending loans available for investment")

# Create loan payments for funded loans
def create_loan_payments(loans):
    print("Creating payment schedules for funded loans...")
    
    funded_loans = [loan for loan in loans if loan.status in ['funded', 'active']]
    
    for loan in funded_loans:
        # Check if payments already exist
        if LoanPayment.objects.filter(loan=loan).exists():
            print(f"Payment schedule already exists for loan: {loan.title}")
            continue
        
        # Create payment schedule
        monthly_payment = loan.calculate_monthly_payment()
        
        for month in range(1, loan.term_months + 1):
            due_date = datetime.now() + timedelta(days=30 * month)
            
            payment = LoanPayment.objects.create(
                loan=loan,
                payment_number=month,
                amount_due=monthly_payment,
                due_date=due_date,
                status='pending'
            )
        
        print(f"Created payment schedule for loan: {loan.title} - ${monthly_payment}/month for {loan.term_months} months")

# Main function to run all initialization
def initialize_sample_data():
    print("Starting sample data initialization...")
    
    users = create_sample_users()
    fund_investor_wallets(users['investors'])
    fund_borrower_wallets(users['borrowers'])
    loans = create_sample_loans(users['borrowers'])
    create_sample_investments(users['investors'], loans)
    create_loan_payments(loans)
    
    print("Sample data initialization complete!")

if __name__ == "__main__":
    initialize_sample_data()
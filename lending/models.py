from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import math
from dateutil.relativedelta import relativedelta

class Loan(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('funded', 'Funded'),
        ('active', 'Active'),
        ('repaid', 'Repaid'),
        ('defaulted', 'Defaulted'),
        ('cancelled', 'Cancelled'),
    )
    
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    title = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_months = models.IntegerField()
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2)
    total_repayment = models.DecimalField(max_digits=12, decimal_places=2)
    risk_score = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    purpose = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    @property
    def current_funded_amount(self):
        """Calculate total amount invested in this loan"""
        return Investment.objects.filter(loan=self).aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')
    
    @property
    def funding_percentage(self):
        """Calculate percentage of loan that has been funded"""
        if self.amount <= 0:
            return 0
        return (self.current_funded_amount / self.amount) * 100
    
    @property
    def total_interest(self):
        """Calculate total interest to be paid"""
        return self.total_repayment - self.amount
    
    @property
    def remaining_balance(self):
        """Calculate remaining balance on loan"""
        if self.status not in ['active', 'funded']:
            return self.amount
        
        paid_principal = LoanPayment.objects.filter(
            loan=self, status='paid').aggregate(
            total=models.Sum('principal'))['total'] or Decimal('0.00')
        
        return self.amount - paid_principal
    
    def calculate_monthly_payment(self):
        """Calculate monthly payment amount using amortization formula"""
        r = self.interest_rate / Decimal('100') / 12  # Monthly interest rate
        n = self.term_months  # Number of payments
        
        # Amortization formula: P = A * (r(1+r)^n) / ((1+r)^n - 1)
        if r == 0:
            return self.amount / n
        
        numerator = r * (1 + r) ** n
        denominator = (1 + r) ** n - 1
        
        return self.amount * (numerator / denominator)
    
    def generate_repayment_schedule(self):
        """Generate or retrieve the repayment schedule for this loan"""
        # If we've already generated the schedule, return it
        if LoanPayment.objects.filter(loan=self).exists():
            return LoanPayment.objects.filter(loan=self).order_by('payment_number')
        
        # If loan is not funded yet, return empty list
        if self.status not in ['funded', 'active', 'repaid'] or not self.start_date:
            return []
        
        # Calculate payment details
        balance = self.amount
        payment_date = self.start_date
        
        schedule = []
        
        for payment_number in range(1, self.term_months + 1):
            # Calculate interest and principal
            monthly_interest = balance * (self.interest_rate / Decimal('100') / 12)
            
            if payment_number == self.term_months:
                # Last payment - make sure we pay off exactly the balance
                principal = balance
                interest = self.monthly_payment - principal
            else:
                interest = monthly_interest
                principal = self.monthly_payment - interest
            
            # Create payment record
            payment = LoanPayment(
                loan=self,
                payment_number=payment_number,
                due_date=payment_date,
                amount_due=self.monthly_payment,
                principal=principal,
                interest=interest,
                status='pending'
            )
            
            if hasattr(payment, 'id'):  # If it's a saved instance
                schedule.append(payment)
            else:
                schedule.append(payment)  # Unsaved but will be returned for display
            
            # Update balance and next payment date
            balance -= principal
            payment_date = payment_date + relativedelta(months=1)
        
        return schedule
    
    def __str__(self):
        return f"{self.title} - ${self.amount} ({self.get_status_display()})"

class Investment(models.Model):
    investor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='investments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date_invested = models.DateTimeField(auto_now_add=True)
    
    @property
    def investment_percentage(self):
        """Calculate what percentage of the loan this investment represents"""
        if self.loan.amount <= 0:
            return 0
        return (self.amount / self.loan.amount) * 100
    
    def __str__(self):
        return f"{self.investor.username} invested ${self.amount} in {self.loan.title}"

class LoanPayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('late', 'Late'),
        ('defaulted', 'Defaulted'),
    )
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    payment_number = models.IntegerField()
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    class Meta:
        unique_together = ('loan', 'payment_number')
    
    def __str__(self):
        return f"Payment #{self.payment_number} for {self.loan.title} - ${self.amount_due}"

# Function to create a loan request
def create_loan_request(borrower, title, description, amount, term_months, purpose=''):
    """Create a new loan request with risk assessment and interest rate calculation"""
    # Get borrower's credit score
    try:
        borrower_profile = borrower.profile.borrower_profile
        credit_score = borrower_profile.credit_score
        
        # Update total loans count
        borrower_profile.total_loans += 1
        borrower_profile.save()
    except:
        # Default credit score if we couldn't get the borrower profile
        credit_score = 650
    
    # Calculate interest rate based on credit score and loan term
    # Higher credit score = lower interest rate
    # Longer term = higher interest rate
    base_rate = Decimal('10.00')  # Base rate of 10%
    
    # Adjust for credit score: 0.02% reduction for each point above 650, up to 3%
    credit_adjustment = min((credit_score - 650) * Decimal('0.02'), Decimal('3.00'))
    
    # Adjust for term: 0.1% increase for each month above 12, up to 2%
    term_adjustment = min((term_months - 12) * Decimal('0.1'), Decimal('2.00'))
    
    interest_rate = base_rate - credit_adjustment + term_adjustment
    interest_rate = max(interest_rate, Decimal('5.00'))  # Minimum 5% interest rate
    
    # Calculate the risk score (1-10 scale, 10 being highest risk)
    risk_score = 10 - int(min(credit_score / 80, 10))
    
    # Calculate monthly payment and total repayment
    loan = Loan(
        borrower=borrower,
        title=title,
        description=description,
        amount=amount,
        interest_rate=interest_rate,
        term_months=term_months,
        risk_score=risk_score,
        purpose=purpose
    )
    
    # Calculate monthly payment
    monthly_payment = loan.calculate_monthly_payment()
    loan.monthly_payment = monthly_payment
    
    # Calculate total repayment
    loan.total_repayment = monthly_payment * Decimal(term_months)
    
    # Save the loan
    loan.save()
    
    return loan

# Function to process an investment in a loan
def invest_in_loan(investor, loan, amount):
    """Process an investment in a loan"""
    with transaction.atomic():
        # Verify the loan is still available for investment
        if loan.status != 'pending':
            return {'success': False, 'message': 'This loan is no longer available for investment.'}
        
        # Verify investor has sufficient funds
        wallet = investor.wallet
        if wallet.balance < amount:
            return {'success': False, 'message': 'Insufficient funds in your wallet.'}
        
        # Verify the investment amount doesn't exceed what's still needed
        remaining_needed = loan.amount - loan.current_funded_amount
        if amount > remaining_needed:
            return {'success': False, 'message': f'The maximum you can invest is ${remaining_needed}.'}
        
        # Process the investment
        # 1. Deduct funds from investor's wallet
        wallet.withdraw_funds(amount)
        
        # 2. Create investment record
        investment = Investment.objects.create(
            investor=investor,
            loan=loan,
            amount=amount
        )
        
        # 3. Update investor's total invested amount
        investor_profile = investor.profile.investor_profile
        investor_profile.total_invested += amount
        investor_profile.save()
        
        # 4. Check if loan is now fully funded
        if loan.current_funded_amount >= loan.amount:
            # Update loan status to funded
            loan.status = 'funded'
            loan.start_date = timezone.now().date()
            loan.end_date = loan.start_date + relativedelta(months=loan.term_months)
            loan.save()
            
            # Create payment schedule
            loan.generate_repayment_schedule()
        
        return {'success': True, 'message': f'Successfully invested ${amount} in {loan.title}.'}

# Function to process a loan repayment
def process_loan_repayment(loan, amount):
    """Process a loan repayment"""
    with transaction.atomic():
        # Verify the loan is in a repayable state
        if loan.status not in ['funded', 'active']:
            return {'success': False, 'message': 'This loan is not in a repayable state.'}
        
        # Get borrower's wallet
        try:
            wallet = loan.borrower.wallet
            if wallet.balance < amount:
                return {'success': False, 'message': 'Insufficient funds in your wallet.'}
        except:
            return {'success': False, 'message': 'Unable to access borrower wallet.'}
        
        # Get the next pending payment
        next_payment = LoanPayment.objects.filter(
            loan=loan, status__in=['pending', 'late']).order_by('payment_number').first()
        
        if not next_payment:
            return {'success': False, 'message': 'No pending payments found for this loan.'}
        
        # Process the payment
        # 1. Deduct funds from borrower's wallet
        wallet.withdraw_funds(amount)
        
        # 2. Update payment record
        next_payment.amount_paid = amount
        next_payment.payment_date = timezone.now().date()
        next_payment.status = 'paid'
        next_payment.save()
        
        # 3. Distribute payment to investors
        platform_fee_percentage = Decimal('0.02')  # 2% platform fee
        platform_fee = next_payment.interest * platform_fee_percentage
        
        distributable_amount = amount - platform_fee
        
        # Get the platform account
        try:
            platform_user = User.objects.get(username='platform')
            platform_wallet = platform_user.wallet
            platform_wallet.deposit_funds(platform_fee)
        except:
            # If platform user doesn't exist, just continue
            pass
        
        # Distribute to investors proportionally
        for investment in loan.investments.all():
            investor = investment.investor
            investor_percentage = investment.investment_percentage / 100
            investor_share = distributable_amount * investor_percentage
            
            # Add to investor's wallet
            investor_wallet = investor.wallet
            investor_wallet.deposit_funds(investor_share)
            
            # Update investor's earnings
            investor_profile = investor.profile.investor_profile
            interest_share = next_payment.interest * investor_percentage
            investor_profile.total_earnings += interest_share
            investor_profile.save()
        
        # 4. Update loan status if this was the last payment
        if not LoanPayment.objects.filter(loan=loan, status__in=['pending', 'late']).exists():
            loan.status = 'repaid'
            loan.save()
        elif loan.status == 'funded':
            # Change status to active after first payment
            loan.status = 'active'
            loan.save()
        
        return {'success': True, 'message': f'Payment of ${amount} processed successfully.'}

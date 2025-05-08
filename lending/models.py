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
    
    LOAN_PURPOSE_CHOICES = (
        ('personal', 'Personal'),
        ('business', 'Business'),
        ('education', 'Education'),
        ('debt_consolidation', 'Debt Consolidation'),
        ('home_improvement', 'Home Improvement'),
        ('medical', 'Medical'),
        ('car', 'Car Purchase'),
        ('vacation', 'Vacation'),
        ('wedding', 'Wedding'),
        ('other', 'Other'),
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
    
    # Enhanced loan details
    purpose = models.CharField(max_length=20, choices=LOAN_PURPOSE_CHOICES, default='other')
    purpose_description = models.TextField(blank=True)
    debt_to_income_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Verification and risk factors
    borrower_verified = models.BooleanField(default=False)
    employment_verified = models.BooleanField(default=False)
    income_verified = models.BooleanField(default=False)
    previous_loans_count = models.IntegerField(default=0)
    previous_loans_repaid = models.IntegerField(default=0)
    
    # Collateral information (for secured loans)
    is_secured = models.BooleanField(default=False)
    collateral_description = models.TextField(blank=True)
    collateral_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    loan_to_value_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Loan performance metrics
    days_late_count = models.IntegerField(default=0)
    times_late_count = models.IntegerField(default=0)
    
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
    def remaining_amount(self):
        """Calculate remaining amount needed to fully fund the loan"""
        return self.amount - self.current_funded_amount
        
    @property
    def total_interest(self):
        """Calculate total interest to be paid"""
        return self.total_repayment - self.amount
        
    @property
    def remaining_balance(self):
        """Calculate remaining balance on loan"""
        # If loan is not active or funded, return full amount
        if self.status not in ['active', 'funded', 'repaid']:
            return self.amount
            
        # Calculate based on payments made
        paid_amount = LoanPayment.objects.filter(
            loan=self, status='paid'
        ).aggregate(total_principal=models.Sum('principal'))['total_principal'] or Decimal('0.00')
        
        return self.amount - paid_amount
        
    @property
    def repayment_progress(self):
        """Calculate repayment progress as a percentage"""
        if self.amount <= 0:
            return 0
        return 100 - ((self.remaining_balance / self.amount) * 100)
        
    @property
    def is_late(self):
        """Check if loan has any late payments"""
        return LoanPayment.objects.filter(loan=self, status='late').exists()
        
    @property
    def on_time_payment_percentage(self):
        """Calculate percentage of payments made on time"""
        total_payments = LoanPayment.objects.filter(
            loan=self, status__in=['paid', 'late']
        ).count()
        
        if total_payments == 0:
            return 100
            
        on_time_payments = LoanPayment.objects.filter(
            loan=self, status='paid'
        ).exclude(payment_date__gt=F('due_date')).count()
        
        return (on_time_payments / total_payments) * 100
    
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
    
    # Automated repayment fields
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_date = models.DateTimeField(null=True, blank=True)
    late_notice_sent = models.BooleanField(default=False)
    late_notice_sent_date = models.DateTimeField(null=True, blank=True)
    late_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    auto_payment_enabled = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('loan', 'payment_number')
    
    def __str__(self):
        return f"Payment #{self.payment_number} for {self.loan.title} - ${self.amount_due}"
    
    def is_due_soon(self):
        """Check if payment is due within 3 days"""
        if self.status != 'pending':
            return False
        return 0 <= (self.due_date - timezone.now().date()).days <= 3
    
    def is_overdue(self):
        """Check if payment is overdue"""
        if self.status != 'pending':
            return False
        return self.due_date < timezone.now().date()
    
    def days_overdue(self):
        """Calculate days overdue"""
        if not self.is_overdue():
            return 0
        return (timezone.now().date() - self.due_date).days
    
    def mark_as_late(self):
        """Mark payment as late and apply late fee"""
        if self.status == 'pending' and self.is_overdue():
            self.status = 'late'
            
            # Apply late fee (5% of payment amount)
            late_fee_rate = Decimal('0.05')
            self.late_fee_amount = self.amount_due * late_fee_rate
            
            # Update amount due with late fee
            self.amount_due += self.late_fee_amount
            
            # Update loan's late payment metrics
            self.loan.times_late_count += 1
            self.loan.days_late_count += self.days_overdue()
            self.loan.save()
            
            self.save()
            return True
        return False

class PortfolioAnalysis(models.Model):
    """Model for storing investor portfolio analysis metrics"""
    investor = models.OneToOneField(User, on_delete=models.CASCADE, related_name='portfolio_analysis')
    last_updated = models.DateTimeField(auto_now=True)
    
    # Performance metrics
    total_invested = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    expected_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    annual_return_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Risk metrics
    avg_loan_risk_score = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))
    risk_adjusted_return = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Diversification metrics
    loan_count = models.IntegerField(default=0)
    loans_at_risk_count = models.IntegerField(default=0)
    avg_investment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    largest_investment_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Purpose diversification (stored as JSON)
    purpose_distribution = models.JSONField(default=dict)
    risk_distribution = models.JSONField(default=dict)
    term_distribution = models.JSONField(default=dict)
    
    def __str__(self):
        return f"{self.investor.username}'s Portfolio Analysis"
    
    def calculate_metrics(self):
        """Calculate all portfolio metrics"""
        from django.db.models import Avg, Count, Max, Sum, F, ExpressionWrapper, DecimalField, Value, Q
        from django.db.models.functions import Cast
        from django.utils import timezone
        
        # Get all active investments
        investments = Investment.objects.filter(
            investor=self.investor,
            loan__status__in=['pending', 'funded', 'active']
        )
        
        # Performance metrics
        self.total_invested = investments.aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
        
        # Calculate earnings (both realized and expected)
        paid_payments = LoanPayment.objects.filter(
            loan__investments__investor=self.investor,
            status='paid'
        )
        
        pending_payments = LoanPayment.objects.filter(
            loan__investments__investor=self.investor,
            status__in=['pending', 'late']
        )
        
        self.total_earnings = paid_payments.aggregate(sum=Sum('interest'))['sum'] or Decimal('0.00')
        self.expected_earnings = pending_payments.aggregate(sum=Sum('interest'))['sum'] or Decimal('0.00')
        
        # Calculate annual return rate
        if self.total_invested > 0:
            # Simple annualized return calculation
            first_investment_date = Investment.objects.filter(
                investor=self.investor
            ).order_by('date_invested').first()
            
            if first_investment_date:
                days_invested = (timezone.now() - first_investment_date.date_invested).days
                if days_invested > 0:
                    # Convert numeric literals to Decimal to avoid TypeError
                    days_invested_decimal = Decimal(str(days_invested))
                    annualized_return = (self.total_earnings / self.total_invested) * (Decimal('365') / days_invested_decimal) * Decimal('100')
                    self.annual_return_rate = min(annualized_return, Decimal('100.00'))  # Cap at 100% for display purposes
        
        # Risk metrics
        self.avg_loan_risk_score = investments.aggregate(
            avg=Avg('loan__risk_score'))['avg'] or Decimal('0.00')
        
        # Risk-adjusted return (simple Sharpe-like ratio)
        if self.avg_loan_risk_score > 0:
            # Convert avg_loan_risk_score to Decimal to avoid TypeError in division
            self.risk_adjusted_return = self.annual_return_rate / Decimal(str(self.avg_loan_risk_score))
        
        # Diversification metrics
        self.loan_count = investments.count()
        self.loans_at_risk_count = investments.filter(loan__risk_score__gt=7).count()
        
        if self.loan_count > 0:
            self.avg_investment_amount = self.total_invested / self.loan_count
            
            # Find largest investment percentage
            largest_investment = investments.order_by('-amount').first()
            if largest_investment:
                self.largest_investment_percentage = (largest_investment.amount / self.total_invested) * 100
        
        # Calculate purpose distribution
        purpose_dist = {}
        for purpose, name in Loan.LOAN_PURPOSE_CHOICES:
            amount = investments.filter(loan__purpose=purpose).aggregate(
                sum=Sum('amount'))['sum'] or Decimal('0.00')
            if amount > 0:
                purpose_dist[name] = float(amount)
        self.purpose_distribution = purpose_dist
        
        # Calculate risk distribution
        risk_dist = {
            'Low Risk (1-3)': float(investments.filter(loan__risk_score__lte=3).aggregate(sum=Sum('amount'))['sum'] or 0),
            'Medium Risk (4-7)': float(investments.filter(loan__risk_score__gt=3, loan__risk_score__lte=7).aggregate(sum=Sum('amount'))['sum'] or 0),
            'High Risk (8-10)': float(investments.filter(loan__risk_score__gt=7).aggregate(sum=Sum('amount'))['sum'] or 0)
        }
        self.risk_distribution = risk_dist
        
        # Calculate term distribution
        term_dist = {
            'Short Term (≤12 mo)': float(investments.filter(loan__term_months__lte=12).aggregate(sum=Sum('amount'))['sum'] or 0),
            'Medium Term (13-36 mo)': float(investments.filter(loan__term_months__gt=12, loan__term_months__lte=36).aggregate(sum=Sum('amount'))['sum'] or 0),
            'Long Term (>36 mo)': float(investments.filter(loan__term_months__gt=36).aggregate(sum=Sum('amount'))['sum'] or 0)
        }
        self.term_distribution = term_dist
        
        self.save()
        return self

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

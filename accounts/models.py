from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('investor', 'Investor'),
        ('borrower', 'Borrower'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    kyc_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    @property
    def available_balance(self):
        """Get the user's wallet balance"""
        try:
            return self.user.wallet.balance
        except:
            return 0

class InvestorProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='investor_profile')
    investment_strategy = models.CharField(max_length=100, blank=True)
    risk_tolerance = models.CharField(max_length=20, blank=True)
    total_invested = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    def __str__(self):
        return f"{self.user_profile.user.username}'s investor profile"

class BorrowerProfile(models.Model):
    EMPLOYMENT_STATUS_CHOICES = (
        ('employed', 'Employed'),
        ('self_employed', 'Self-Employed'),
        ('unemployed', 'Unemployed'),
        ('retired', 'Retired'),
    )
    
    VERIFICATION_STATUS_CHOICES = (
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='borrower_profile')
    credit_score = models.IntegerField(default=650)
    employment_status = models.CharField(max_length=15, choices=EMPLOYMENT_STATUS_CHOICES, default='employed')
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_loans = models.IntegerField(default=0)
    
    # Identity verification fields
    identity_verified = models.BooleanField(default=False)
    income_verified = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=15, choices=VERIFICATION_STATUS_CHOICES, default='not_submitted')
    
    # Document storage
    id_document = models.FileField(upload_to='verification/id/', null=True, blank=True)
    income_proof = models.FileField(upload_to='verification/income/', null=True, blank=True)
    
    # Verification timestamps
    verification_submitted_at = models.DateTimeField(null=True, blank=True)
    verification_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional verification data
    employer_name = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    employment_duration_years = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user_profile.user.username}'s borrower profile"
    
    def verification_progress(self):
        """Return verification progress as a percentage"""
        total_steps = 2  # ID and income verification
        completed_steps = 0
        
        if self.identity_verified:
            completed_steps += 1
        if self.income_verified:
            completed_steps += 1
            
        return (completed_steps / total_steps) * 100

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    def deposit_funds(self, amount, description=None, related_entity_type=None, related_entity_id=None):
        """Add funds to wallet and record transaction"""
        self.balance += amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            wallet=self,
            transaction_type='deposit',
            amount=amount,
            description=description or 'Deposit funds',
            balance_after=self.balance,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
        
        return True
    
    def withdraw_funds(self, amount, description=None, related_entity_type=None, related_entity_id=None):
        """Withdraw funds from wallet and record transaction"""
        if self.balance < amount:
            return False
        
        self.balance -= amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            wallet=self,
            transaction_type='withdrawal',
            amount=amount,
            description=description or 'Withdraw funds',
            balance_after=self.balance,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
        
        return True
    
    def __str__(self):
        return f"{self.user.username}'s wallet"

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('investment', 'Investment'),
        ('return', 'Investment Return'),
        ('fee', 'Platform Fee'),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    related_entity_type = models.CharField(max_length=20, blank=True, null=True)
    related_entity_id = models.PositiveIntegerField(blank=True, null=True)
    
    @property
    def related_entity(self):
        """Get the related entity (investment, loan payment, etc.) if applicable"""
        if not self.related_entity_type or not self.related_entity_id:
            return None
            
        if self.related_entity_type == 'investment':
            from lending.models import Investment
            return Investment.objects.filter(id=self.related_entity_id).first()
        elif self.related_entity_type == 'loan_payment':
            from lending.models import LoanPayment
            return LoanPayment.objects.filter(id=self.related_entity_id).first()
        return None
    
    def __str__(self):
        return f"{self.wallet.user.username} - {self.get_transaction_type_display()} - R{self.amount}"

# Signal to create profiles and wallet automatically
@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    """Create profiles and wallet when a new user is created"""
    if created:
        # Create wallet for all users
        Wallet.objects.create(user=instance)

@receiver(post_save, sender=UserProfile)
def create_type_specific_profile(sender, instance, created, **kwargs):
    """Create type-specific profile based on user_type"""
    if created:
        if instance.user_type == 'investor':
            InvestorProfile.objects.create(user_profile=instance)
        elif instance.user_type == 'borrower':
            BorrowerProfile.objects.create(user_profile=instance)

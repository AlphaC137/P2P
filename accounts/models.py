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
    
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='borrower_profile')
    credit_score = models.IntegerField(default=650)
    employment_status = models.CharField(max_length=15, choices=EMPLOYMENT_STATUS_CHOICES, default='employed')
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_loans = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user_profile.user.username}'s borrower profile"

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    def deposit_funds(self, amount):
        """Add funds to wallet and record transaction"""
        self.balance += amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            wallet=self,
            transaction_type='deposit',
            amount=amount,
            description='Deposit funds'
        )
        
        return True
    
    def withdraw_funds(self, amount):
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
            description='Withdraw funds'
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
    
    def __str__(self):
        return f"{self.wallet.user.username} - {self.get_transaction_type_display()} - ${self.amount}"

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

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import datetime

from .models import UserProfile, BorrowerProfile, InvestorProfile

class UserLoginForm(forms.Form):
    """Form for user login"""
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput())

class UserRegistrationForm(UserCreationForm):
    """Base form for user registration"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=datetime.date.today() - datetime.timedelta(days=365*25)  # Default to 25 years ago
    )
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email is already in use')
        return email
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        today = datetime.date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        if age < 18:
            raise forms.ValidationError('You must be at least 18 years old to register')
        return dob

class InvestorRegistrationForm(UserRegistrationForm):
    """Form for investor registration"""
    investment_strategy = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    risk_tolerance = forms.ChoiceField(choices=[
        ('conservative', 'Conservative'),
        ('moderate', 'Moderate'),
        ('aggressive', 'Aggressive')
    ], required=False)
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                user_type='investor',
                phone_number=self.cleaned_data.get('phone_number', ''),
                date_of_birth=self.cleaned_data.get('date_of_birth'),
                address=self.cleaned_data.get('address', '')
            )
            
            # Update investor profile
            investor_profile = profile.investor_profile
            investor_profile.investment_strategy = self.cleaned_data.get('investment_strategy', '')
            investor_profile.risk_tolerance = self.cleaned_data.get('risk_tolerance', 'moderate')
            investor_profile.save()
        
        return user

class BorrowerRegistrationForm(UserRegistrationForm):
    """Form for borrower registration"""
    employment_status = forms.ChoiceField(choices=BorrowerProfile.EMPLOYMENT_STATUS_CHOICES, required=True)
    annual_income = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=True,
        validators=[MinValueValidator(Decimal('1000.00'))]
    )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                user_type='borrower',
                phone_number=self.cleaned_data.get('phone_number', ''),
                date_of_birth=self.cleaned_data.get('date_of_birth'),
                address=self.cleaned_data.get('address', '')
            )
            
            # Update borrower profile
            borrower_profile = profile.borrower_profile
            borrower_profile.annual_income = self.cleaned_data.get('annual_income')
            borrower_profile.employment_status = self.cleaned_data.get('employment_status', 'employed')
            borrower_profile.save()
        
        return user

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address']
    
    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Update user fields
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
            
            profile.save()
        return profile

class InvestorProfileUpdateForm(forms.Form):
    """Form for updating investor profile"""
    investment_strategy = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    risk_tolerance = forms.ChoiceField(choices=[
        ('conservative', 'Conservative'),
        ('moderate', 'Moderate'),
        ('aggressive', 'Aggressive')
    ], required=False)

class BorrowerProfileUpdateForm(forms.Form):
    """Form for updating borrower profile"""
    employment_status = forms.ChoiceField(choices=BorrowerProfile.EMPLOYMENT_STATUS_CHOICES, required=True)
    annual_income = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=True,
        validators=[MinValueValidator(Decimal('1000.00'))]
    )

class DepositForm(forms.Form):
    """Form for depositing funds"""
    amount = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=True,
        validators=[MinValueValidator(Decimal('10.00'))],
        widget=forms.NumberInput(attrs={'min': '10.00', 'step': '0.01'})
    )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount < Decimal('10.00'):
            raise forms.ValidationError('Minimum deposit amount is $10.00')
        return amount

class WithdrawalForm(forms.Form):
    """Form for withdrawing funds"""
    amount = forms.DecimalField(
        max_digits=12, 
        decimal_places=2,
        min_value=Decimal('10.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount'})
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(WithdrawalForm, self).__init__(*args, **kwargs)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount < Decimal('10.00'):
            raise forms.ValidationError("Minimum withdrawal amount is $10.00")
        
        if self.user and amount > self.user.wallet.balance:
            raise forms.ValidationError(f"You can't withdraw more than your current balance (${self.user.wallet.balance})")
        
        return amount

class InvestorProfileForm(forms.Form):
    """Form for investor profile information"""
    phone_number = forms.CharField(max_length=15, required=True)
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=datetime.date.today() - datetime.timedelta(days=365*25)  # Default to 25 years ago
    )
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    investment_strategy = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    risk_tolerance = forms.ChoiceField(choices=[
        ('conservative', 'Conservative'),
        ('moderate', 'Moderate'),
        ('aggressive', 'Aggressive')
    ], required=False)

class BorrowerProfileForm(forms.Form):
    """Form for borrower profile information"""
    phone_number = forms.CharField(max_length=15, required=True)
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=datetime.date.today() - datetime.timedelta(days=365*25)  # Default to 25 years ago
    )
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    employment_status = forms.ChoiceField(choices=BorrowerProfile.EMPLOYMENT_STATUS_CHOICES, required=True)
    annual_income = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=True,
        validators=[MinValueValidator(Decimal('1000.00'))]
    )
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        today = datetime.date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        if age < 18:
            raise forms.ValidationError('You must be at least 18 years old to register')
        return dob
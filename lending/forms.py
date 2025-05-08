from django import forms
from .models import Loan
from decimal import Decimal

class LoanRequestForm(forms.Form):
    """Form for creating a loan request"""
    title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Loan Title'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Detailed description of your loan request'
        })
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('100.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Amount needed',
            'min': '100.00',
            'step': '50.00'
        })
    )
    term_months = forms.IntegerField(
        min_value=1,
        max_value=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Loan term in months',
            'min': '1',
            'max': '60'
        })
    )
    
    # Use the choices from the Loan model
    purpose = forms.ChoiceField(
        choices=Loan.LOAN_PURPOSE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    purpose_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional details about how you plan to use the loan'
        })
    )
    
    # Secured loan options
    is_secured = forms.BooleanField(
        required=False,
        label='This is a secured loan (collateral provided)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    collateral_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe the collateral you are offering (e.g., vehicle, property)'
        })
    )
    
    collateral_value = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Estimated value of collateral',
            'min': '0',
            'step': '100.00'
        })
    )
    
    # Financial information
    monthly_income = forms.DecimalField(
        required=True,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your monthly income',
            'min': '0',
            'step': '100.00'
        })
    )
    
    monthly_debt_payments = forms.DecimalField(
        required=True,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your monthly debt payments',
            'min': '0',
            'step': '10.00'
        })
    )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount < Decimal('100.00'):
            raise forms.ValidationError('Minimum loan amount is $100.00')
        if amount > Decimal('50000.00'):
            raise forms.ValidationError('Maximum loan amount is $50,000.00')
        return amount
    
    def clean_term_months(self):
        term_months = self.cleaned_data.get('term_months')
        if term_months < 1:
            raise forms.ValidationError('Minimum loan term is 1 month')
        if term_months > 60:
            raise forms.ValidationError('Maximum loan term is 60 months (5 years)')
        return term_months
    
    def clean_collateral_value(self):
        is_secured = self.cleaned_data.get('is_secured')
        collateral_value = self.cleaned_data.get('collateral_value')
        
        if is_secured and (collateral_value is None or collateral_value <= 0):
            raise forms.ValidationError('Collateral value is required for secured loans')
        return collateral_value
    
    def clean_collateral_description(self):
        is_secured = self.cleaned_data.get('is_secured')
        collateral_description = self.cleaned_data.get('collateral_description')
        
        if is_secured and not collateral_description:
            raise forms.ValidationError('Collateral description is required for secured loans')
        return collateral_description
    
    def clean(self):
        cleaned_data = super().clean()
        monthly_income = cleaned_data.get('monthly_income') or Decimal('0')
        monthly_debt_payments = cleaned_data.get('monthly_debt_payments') or Decimal('0')
        
        if monthly_income and monthly_debt_payments:
            if monthly_income <= 0:
                self.add_error('monthly_income', 'Monthly income must be greater than zero')
            elif monthly_debt_payments / monthly_income > Decimal('0.5'):
                self.add_error('monthly_debt_payments', 
                              'Your debt-to-income ratio is too high. Monthly debt payments should be less than 50% of your income.')
        
        return cleaned_data

class InvestmentForm(forms.Form):
    """Form for investing in a loan"""
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('10.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Investment amount',
            'min': '10.00',
            'step': '5.00'
        })
    )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount < Decimal('10.00'):
            raise forms.ValidationError('Minimum investment amount is $10.00')
        return amount

class LoanRepaymentForm(forms.Form):
    """Form for making a loan repayment"""
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Payment amount',
            'min': '1.00',
            'step': '0.01'
        })
    )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= Decimal('0'):
            raise forms.ValidationError('Payment amount must be greater than zero')
        return amount
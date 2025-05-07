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
    PURPOSE_CHOICES = [
        ('personal', 'Personal'),
        ('business', 'Business'),
        ('education', 'Education'),
        ('debt_consolidation', 'Debt Consolidation'),
        ('home_improvement', 'Home Improvement'),
        ('medical', 'Medical'),
        ('other', 'Other')
    ]
    purpose = forms.ChoiceField(
        choices=PURPOSE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
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
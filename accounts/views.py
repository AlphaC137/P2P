from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .models import UserProfile, Wallet, Transaction
from .forms import UserRegistrationForm, InvestorProfileForm, BorrowerProfileForm, DepositForm, WithdrawalForm
from decimal import Decimal

def register_investor(request):
    """Register a new investor user"""
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = InvestorProfileForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            # Create user account
            user = user_form.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                user_type='investor',
                phone_number=profile_form.cleaned_data.get('phone_number'),
                date_of_birth=profile_form.cleaned_data.get('date_of_birth'),
                address=profile_form.cleaned_data.get('address')
            )
            
            # Update investor profile
            investor_profile = profile.investor_profile
            investor_profile.investment_strategy = profile_form.cleaned_data.get('investment_strategy')
            investor_profile.risk_tolerance = profile_form.cleaned_data.get('risk_tolerance')
            investor_profile.save()
            
            # Log the user in
            username = user_form.cleaned_data.get('username')
            password = user_form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            
            messages.success(request, f'Account created successfully! Welcome, {username}!')
            return redirect('dashboard:investor')
    else:
        user_form = UserRegistrationForm()
        profile_form = InvestorProfileForm()
    
    return render(request, 'accounts/register.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_type': 'Investor'
    })

def register_borrower(request):
    """Register a new borrower user"""
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = BorrowerProfileForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            # Create user account
            user = user_form.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                user_type='borrower',
                phone_number=profile_form.cleaned_data.get('phone_number'),
                date_of_birth=profile_form.cleaned_data.get('date_of_birth'),
                address=profile_form.cleaned_data.get('address')
            )
            
            # Update borrower profile
            borrower_profile = profile.borrower_profile
            borrower_profile.employment_status = profile_form.cleaned_data.get('employment_status')
            borrower_profile.annual_income = profile_form.cleaned_data.get('annual_income')
            borrower_profile.save()
            
            # Log the user in
            username = user_form.cleaned_data.get('username')
            password = user_form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            
            messages.success(request, f'Account created successfully! Welcome, {username}!')
            return redirect('dashboard:borrower')
    else:
        user_form = UserRegistrationForm()
        profile_form = BorrowerProfileForm()
    
    return render(request, 'accounts/register.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_type': 'Borrower'
    })

def user_login(request):
    """Login view"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Redirect based on user type
                try:
                    if user.profile.user_type == 'investor':
                        return redirect('dashboard:investor')
                    else:
                        return redirect('dashboard:borrower')
                except:
                    # If profile doesn't exist, redirect to home
                    return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def profile(request):
    """Display user profile"""
    user_profile = request.user.profile
    
    context = {
        'user_profile': user_profile
    }
    
    if user_profile.user_type == 'investor':
        context['investor_profile'] = user_profile.investor_profile
    else:
        context['borrower_profile'] = user_profile.borrower_profile
    
    return render(request, 'accounts/profile.html', context)

@login_required
def wallet_view(request):
    """Display user wallet and transaction history"""
    wallet = request.user.wallet
    transactions = Transaction.objects.filter(wallet=wallet).order_by('-timestamp')
    
    context = {
        'wallet': wallet,
        'transactions': transactions
    }
    
    return render(request, 'accounts/wallet.html', context)

@login_required
def deposit_funds(request):
    """Handle deposit of funds to wallet"""
    wallet = request.user.wallet
    
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            
            if amount <= Decimal('0'):
                messages.error(request, 'Amount must be greater than zero.')
                return redirect('accounts:deposit_funds')
            
            # Process deposit
            wallet.deposit_funds(amount)
            
            messages.success(request, f'Successfully deposited ${amount} to your wallet.')
            return redirect('accounts:wallet')
    else:
        form = DepositForm()
    
    return render(request, 'accounts/deposit.html', {
        'form': form,
        'user': request.user
    })

@login_required
def withdraw_funds(request):
    """Handle withdrawal of funds from wallet"""
    wallet = request.user.wallet
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            
            if amount <= Decimal('0'):
                messages.error(request, 'Amount must be greater than zero.')
                return redirect('accounts:withdraw_funds')
            
            if wallet.balance < amount:
                messages.error(request, 'Insufficient funds in your wallet.')
                return redirect('accounts:withdraw_funds')
            
            # Process withdrawal
            wallet.withdraw_funds(amount)
            
            messages.success(request, f'Successfully withdrew ${amount} from your wallet.')
            return redirect('accounts:wallet')
    else:
        form = WithdrawalForm()
    
    return render(request, 'accounts/withdraw.html', {
        'form': form,
        'wallet': wallet
    })

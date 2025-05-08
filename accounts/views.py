from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .models import UserProfile, Wallet, Transaction
from .forms import (
    UserRegistrationForm, InvestorProfileForm, BorrowerProfileForm, 
    DepositForm, WithdrawalForm, BorrowerVerificationForm
)
import datetime
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

@login_required
def borrower_verification(request):
    """Handle borrower verification document upload"""
    # Check if user is a borrower
    try:
        if request.user.profile.user_type != 'borrower':
            messages.warning(request, 'Only borrowers need to complete verification.')
            return redirect('home')
    except:
        messages.error(request, 'User profile not found.')
        return redirect('home')
    
    # Get borrower profile
    borrower_profile = request.user.profile.borrower_profile
    
    # Check if already verified or pending verification
    if borrower_profile.identity_verified and borrower_profile.income_verified:
        messages.info(request, 'Your account is already verified.')
        return redirect('dashboard:borrower')
    
    if borrower_profile.verification_status == 'pending':
        messages.info(request, 'Your verification is pending review. We will notify you once completed.')
        return redirect('dashboard:borrower')
    
    if request.method == 'POST':
        form = BorrowerVerificationForm(request.POST, request.FILES, instance=borrower_profile)
        if form.is_valid():
            profile = form.save(commit=False)
            # Update additional fields
            profile.verification_status = 'pending'
            profile.verification_submitted_at = datetime.datetime.now()
            profile.save()
            
            messages.success(request, 'Your verification documents have been submitted successfully. We will review them shortly.')
            return redirect('dashboard:borrower')
    else:
        form = BorrowerVerificationForm(instance=borrower_profile)
    
    return render(request, 'accounts/verification.html', {
        'form': form,
        'borrower_profile': borrower_profile
    })

@login_required
def transaction_detail(request, transaction_id):
    """View details of a specific transaction"""
    transaction = get_object_or_404(Transaction, id=transaction_id, wallet__user=request.user)
    
    return render(request, 'accounts/transaction_detail.html', {
        'transaction': transaction
    })

@login_required
def wallet_statistics(request):
    """Display detailed statistics for user's wallet"""
    wallet = request.user.wallet
    transactions = Transaction.objects.filter(wallet=wallet)
    
    # Calculate basic statistics
    deposit_sum = transactions.filter(transaction_type='deposit').aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
    withdrawal_sum = transactions.filter(transaction_type='withdrawal').aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
    transaction_count = transactions.count()
    
    # Get recent transactions
    recent_transactions = transactions.order_by('-timestamp')[:5]
    
    # Calculate ROI for investors
    roi = 0
    if hasattr(request.user, 'profile') and request.user.profile.user_type == 'investor':
        investor_profile = request.user.profile.investor_profile
        if investor_profile.total_invested > 0:
            roi = (investor_profile.total_earnings / investor_profile.total_invested) * 100
            roi = round(roi, 2)
    
    # Prepare data for charts
    # Monthly cash flow
    months_data = {}
    for i in range(0, 6):  # Last 6 months
        target_month = datetime.datetime.now() - datetime.timedelta(days=30 * i)
        month_key = target_month.strftime('%b %Y')
        
        # Money in for the month
        money_in = transactions.filter(
            transaction_type__in=['deposit', 'return'],
            timestamp__year=target_month.year,
            timestamp__month=target_month.month
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0
        
        # Money out for the month
        money_out = transactions.filter(
            transaction_type__in=['withdrawal', 'investment', 'fee'],
            timestamp__year=target_month.year,
            timestamp__month=target_month.month
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0
        
        months_data[month_key] = {
            'in': float(money_in),
            'out': float(money_out)
        }
    
    # Sort months chronologically
    months = list(months_data.keys())
    months.reverse()  # Most recent last
    
    money_in = [months_data[m]['in'] for m in months]
    money_out = [months_data[m]['out'] for m in months]
    
    # Transaction types distribution
    transaction_types = []
    transaction_amounts = []
    
    for t_type, t_name in Transaction.TRANSACTION_TYPE_CHOICES:
        amount = transactions.filter(
            transaction_type=t_type
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0
        
        if amount > 0:
            transaction_types.append(t_name)
            transaction_amounts.append(float(amount))
    
    context = {
        'wallet': wallet,
        'deposit_sum': deposit_sum,
        'withdrawal_sum': withdrawal_sum,
        'transaction_count': transaction_count,
        'recent_transactions': recent_transactions,
        'roi': roi,
        'months': months,
        'money_in': money_in,
        'money_out': money_out,
        'transaction_types': transaction_types,
        'transaction_amounts': transaction_amounts
    }
    
    return render(request, 'accounts/wallet_statistics.html', context)

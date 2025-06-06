from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Value, DecimalField
from django.contrib import messages
from accounts.models import Transaction
from lending.models import Loan, Investment, LoanPayment

@login_required
def investor_dashboard(request):
    """Dashboard view for investors"""
    # Check if user is an investor
    try:
        if request.user.profile.user_type != 'investor':
            messages.warning(request, 'You do not have access to this dashboard.')
            return redirect('home')
    except:
        messages.error(request, 'User profile not found.')
        return redirect('home')
    
    # Get user's wallet
    wallet = request.user.wallet
    
    # Get user's investments
    investments = Investment.objects.filter(investor=request.user).order_by('-date_invested')
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(wallet=wallet).order_by('-timestamp')[:10]
    
    # Get active investments (the actual queryset, not just the count)
    active_investments = investments.filter(loan__status__in=['active', 'funded'])
    
    # Summary statistics
    total_invested = investments.aggregate(total=Sum('amount'))['total'] or 0
    active_investments_count = active_investments.count()
    
    # Calculate total returns (received repayments)
    total_returns = LoanPayment.objects.filter(
        loan__investments__investor=request.user,
        status='paid'
    ).aggregate(
        total=Sum('amount_due')
    )['total'] or 0
    
    # Calculate average interest rate (weighted by investment amount)
    if total_invested > 0:
        avg_interest_rate = investments.annotate(
            weighted_rate=F('amount') * F('loan__interest_rate') / total_invested
        ).aggregate(avg_rate=Sum('weighted_rate'))['avg_rate'] or 0
    else:
        avg_interest_rate = 0
    
    # Calculate expected returns (upcoming repayments)
    expected_returns = LoanPayment.objects.filter(
        loan__investments__investor=request.user,
        status__in=['pending', 'late']
    ).aggregate(
        total=Sum('amount_due')
    )['total'] or 0
    
    # Diversification metrics
    loan_purposes = investments.values('loan__purpose').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    risk_diversification = investments.values('loan__risk_score').annotate(
        total=Sum('amount')
    ).order_by('loan__risk_score')
    
    context = {
        'wallet': wallet,
        'investments': investments,
        'recent_transactions': recent_transactions,
        'total_invested': total_invested,
        'active_investments': active_investments,
        'active_investments_count': active_investments_count,
        'total_returns': total_returns,
        'avg_interest_rate': avg_interest_rate,
        'expected_returns': expected_returns,
        'loan_purposes': loan_purposes,
        'risk_diversification': risk_diversification,
    }
    
    return render(request, 'dashboard/investor.html', context)

@login_required
def borrower_dashboard(request):
    """Dashboard view for borrowers"""
    # Check if user is a borrower
    try:
        if request.user.profile.user_type != 'borrower':
            messages.warning(request, 'You do not have access to this dashboard.')
            return redirect('home')
    except:
        messages.error(request, 'User profile not found.')
        return redirect('home')
    
    # Get user's wallet
    wallet = request.user.wallet
    
    # Get user's loans
    loans = Loan.objects.filter(borrower=request.user).order_by('-created_at')
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(wallet=wallet).order_by('-timestamp')[:10]
    
    # Upcoming payments - find the next pending payment for each active loan
    upcoming_payments = []
    try:
        for loan in loans.filter(status__in=['active', 'funded']):
            next_payment = LoanPayment.objects.filter(
                loan=loan,
                status__in=['pending', 'late']
            ).order_by('due_date').first()
            
            if next_payment:
                upcoming_payments.append({'loan': loan, 'payment': next_payment})
    except Exception as e:
        # Log the error but continue
        print(f"Error processing upcoming payments: {e}")
        messages.warning(request, "There was an issue loading some payment information.")
    
    # Late payments
    late_payments = LoanPayment.objects.filter(
        loan__borrower=request.user,
        status='late'
    ).order_by('due_date')
    
    # Summary statistics
    total_borrowed = loans.aggregate(total=Sum('amount'))['total'] or 0
    active_loans_count = loans.filter(status__in=['active', 'funded']).count()
    active_loans = loans.filter(status__in=['active', 'funded'])
    pending_loans = loans.filter(status='pending').count()
    
    # Calculate total repaid
    total_repaid = LoanPayment.objects.filter(
        loan__borrower=request.user,
        status='paid'
    ).aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    
    # Calculate remaining debt
    remaining_debt = LoanPayment.objects.filter(
        loan__borrower=request.user,
        status__in=['pending', 'late']
    ).aggregate(
        total=Sum('amount_due')
    )['total'] or 0
    
    # Get user's credit score
    credit_score = 650  # Default value
    try:
        borrower_profile = request.user.profile.borrower_profile
        credit_score = borrower_profile.credit_score
    except:
        pass
        
    context = {
        'wallet': wallet,
        'loans': loans,
        'recent_transactions': recent_transactions,
        'upcoming_payments': upcoming_payments,
        'late_payments': late_payments,
        'total_borrowed': total_borrowed,
        'active_loans': active_loans,
        'active_loans_count': active_loans_count,
        'pending_loans': pending_loans,
        'total_repaid': total_repaid,
        'remaining_debt': remaining_debt,
        'credit_score': credit_score,
    }
    
    return render(request, 'dashboard/borrower.html', context)

@login_required
def home_dashboard(request):
    """Main dashboard router - redirects to the appropriate dashboard based on user type"""
    if not hasattr(request.user, 'profile'):
        messages.error(request, 'Please complete your profile setup first')
        return redirect('accounts:profile_setup')
        
    if request.user.profile.user_type == 'investor':
        return redirect('dashboard:investor')
    elif request.user.profile.user_type == 'borrower':
        return redirect('dashboard:borrower')
    else:
        messages.error(request, 'Unknown user type. Please contact support.')
        return redirect('home')

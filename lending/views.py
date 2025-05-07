from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Loan, Investment, LoanPayment, create_loan_request, invest_in_loan, process_loan_repayment
from .forms import LoanRequestForm, InvestmentForm, LoanRepaymentForm
from decimal import Decimal

def marketplace(request):
    """Display all pending loans for investment"""
    # Get all pending loans
    pending_loans = Loan.objects.filter(status='pending')
    
    # Filter loans by search query if provided
    query = request.GET.get('q')
    if query:
        pending_loans = pending_loans.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(purpose__icontains=query)
        )
    
    # Filter by amount range if provided
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    
    if min_amount:
        pending_loans = pending_loans.filter(amount__gte=Decimal(min_amount))
    
    if max_amount:
        pending_loans = pending_loans.filter(amount__lte=Decimal(max_amount))
    
    # Filter by interest rate if provided
    min_rate = request.GET.get('min_rate')
    max_rate = request.GET.get('max_rate')
    
    if min_rate:
        pending_loans = pending_loans.filter(interest_rate__gte=Decimal(min_rate))
    
    if max_rate:
        pending_loans = pending_loans.filter(interest_rate__lte=Decimal(max_rate))
    
    # Filter by term if provided
    term = request.GET.get('term')
    if term:
        if term == 'short':
            pending_loans = pending_loans.filter(term_months__lte=12)
        elif term == 'medium':
            pending_loans = pending_loans.filter(term_months__gt=12, term_months__lte=36)
        elif term == 'long':
            pending_loans = pending_loans.filter(term_months__gt=36)
    
    # Filter by risk score if provided
    risk = request.GET.get('risk')
    if risk:
        if risk == 'low':
            pending_loans = pending_loans.filter(risk_score__lte=3)
        elif risk == 'medium':
            pending_loans = pending_loans.filter(risk_score__gt=3, risk_score__lte=7)
        elif risk == 'high':
            pending_loans = pending_loans.filter(risk_score__gt=7)
    
    context = {
        'loans': pending_loans,
        'query': query,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'min_rate': min_rate,
        'max_rate': max_rate,
        'term': term,
        'risk': risk,
    }
    
    return render(request, 'lending/marketplace.html', context)

def loan_detail(request, loan_id):
    """Display detailed information about a loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Get investments for this loan
    investments = Investment.objects.filter(loan=loan)
    
    # Get payment schedule if loan is funded or active
    payment_schedule = None
    if loan.status in ['funded', 'active', 'repaid']:
        payment_schedule = loan.generate_repayment_schedule()
    
    # Check if current user has already invested in this loan
    user_investment = None
    if request.user.is_authenticated:
        user_investment = Investment.objects.filter(loan=loan, investor=request.user).first()
    
    # Prepare investment form for authenticated investors
    investment_form = None
    can_invest = False
    if request.user.is_authenticated:
        try:
            if request.user.profile.user_type == 'investor' and loan.status == 'pending':
                investment_form = InvestmentForm()
                can_invest = True
        except:
            pass
    
    context = {
        'loan': loan,
        'investments': investments,
        'payment_schedule': payment_schedule,
        'user_investment': user_investment,
        'investment_form': investment_form,
        'can_invest': can_invest,
    }
    
    return render(request, 'lending/loan_detail.html', context)

@login_required
def create_loan(request):
    """Create a new loan request"""
    # Check if user is a borrower
    try:
        if request.user.profile.user_type != 'borrower':
            messages.error(request, 'Only borrowers can create loan requests.')
            return redirect('home')
    except:
        messages.error(request, 'User profile not found.')
        return redirect('home')
    
    if request.method == 'POST':
        form = LoanRequestForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            description = form.cleaned_data.get('description')
            amount = form.cleaned_data.get('amount')
            term_months = form.cleaned_data.get('term_months')
            purpose = form.cleaned_data.get('purpose')
            
            # Create loan request
            loan = create_loan_request(
                borrower=request.user,
                title=title,
                description=description,
                amount=amount,
                term_months=term_months,
                purpose=purpose
            )
            
            messages.success(request, f'Loan request "{title}" created successfully! It is now available for investors to fund.')
            return redirect('lending:loan_detail', loan_id=loan.id)
    else:
        form = LoanRequestForm()
    
    return render(request, 'lending/create_loan.html', {
        'form': form
    })

@login_required
def invest(request, loan_id):
    """Process an investment in a loan"""
    # Check if user is an investor
    try:
        if request.user.profile.user_type != 'investor':
            messages.error(request, 'Only investors can invest in loans.')
            return redirect('lending:loan_detail', loan_id=loan_id)
    except:
        messages.error(request, 'User profile not found.')
        return redirect('lending:loan_detail', loan_id=loan_id)
    
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Check if loan is still available for investment
    if loan.status != 'pending':
        messages.error(request, 'This loan is no longer available for investment.')
        return redirect('lending:loan_detail', loan_id=loan_id)
    
    if request.method == 'POST':
        form = InvestmentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            
            # Check if amount is greater than zero
            if amount <= Decimal('0'):
                messages.error(request, 'Investment amount must be greater than zero.')
                return redirect('lending:invest', loan_id=loan_id)
            
            # Check if user has sufficient funds
            wallet = request.user.wallet
            if wallet.balance < amount:
                messages.error(request, 'Insufficient funds in your wallet.')
                return redirect('lending:invest', loan_id=loan_id)
            
            # Check if amount doesn't exceed remaining needed
            remaining_needed = loan.amount - loan.current_funded_amount
            if amount > remaining_needed:
                messages.error(request, f'The maximum you can invest is ${remaining_needed}.')
                return redirect('lending:invest', loan_id=loan_id)
            
            # Process the investment
            result = invest_in_loan(request.user, loan, amount)
            
            if result['success']:
                messages.success(request, result['message'])
                return redirect('lending:loan_detail', loan_id=loan_id)
            else:
                messages.error(request, result['message'])
                return redirect('lending:invest', loan_id=loan_id)
    else:
        form = InvestmentForm()
    
    return render(request, 'lending/invest.html', {
        'form': form,
        'loan': loan
    })

@login_required
def repay_loan(request, loan_id):
    """Process a loan repayment"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Check if user is the borrower of this loan
    if request.user != loan.borrower:
        messages.error(request, 'You can only repay your own loans.')
        return redirect('dashboard:borrower')
    
    # Check if loan is in a repayable state
    if loan.status not in ['funded', 'active']:
        messages.error(request, 'This loan is not in a repayable state.')
        return redirect('dashboard:borrower')
    
    # Get the next pending payment
    next_payment = LoanPayment.objects.filter(
        loan=loan, status__in=['pending', 'late']).order_by('payment_number').first()
    
    if not next_payment:
        messages.error(request, 'No pending payments found for this loan.')
        return redirect('dashboard:borrower')
    
    if request.method == 'POST':
        form = LoanRepaymentForm(request.POST)
        if form.is_valid():
            payment_amount = form.cleaned_data.get('amount')
            
            # Process the payment
            result = process_loan_repayment(loan, payment_amount)
            
            if result['success']:
                messages.success(request, result['message'])
                return redirect('dashboard:borrower')
            else:
                messages.error(request, result['message'])
                return redirect('lending:repay_loan', loan_id=loan_id)
    else:
        # Pre-fill form with the next payment amount
        form = LoanRepaymentForm(initial={'amount': next_payment.amount_due})
    
    return render(request, 'lending/repay.html', {
        'form': form,
        'loan': loan,
        'next_payment': next_payment
    })

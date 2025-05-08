from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, F
from .models import Loan, Investment, LoanPayment, PortfolioAnalysis, create_loan_request, invest_in_loan, process_loan_repayment
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
    
    # Get the borrower profile
    try:
        borrower_profile = request.user.profile.borrower_profile
        
        # Check if the borrower is verified
        borrower_verified = borrower_profile.verification_status == 'verified'
    except:
        borrower_verified = False
    
    if request.method == 'POST':
        form = LoanRequestForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            description = form.cleaned_data.get('description')
            amount = form.cleaned_data.get('amount')
            term_months = form.cleaned_data.get('term_months')
            purpose = form.cleaned_data.get('purpose')
            purpose_description = form.cleaned_data.get('purpose_description')
            
            # Get secured loan details
            is_secured = form.cleaned_data.get('is_secured')
            collateral_description = form.cleaned_data.get('collateral_description')
            collateral_value = form.cleaned_data.get('collateral_value')
            
            # Get financial details for risk assessment
            monthly_income = form.cleaned_data.get('monthly_income')
            monthly_debt_payments = form.cleaned_data.get('monthly_debt_payments')
            
            # Calculate debt-to-income ratio
            if monthly_income > 0:
                debt_to_income_ratio = monthly_debt_payments / monthly_income
            else:
                debt_to_income_ratio = 0
            
            # Get previous loan history
            previous_loans_count = Loan.objects.filter(borrower=request.user).count()
            previous_loans_repaid = Loan.objects.filter(borrower=request.user, status='repaid').count()
            
            # Create loan request
            loan = create_loan_request(
                borrower=request.user,
                title=title,
                description=description,
                amount=amount,
                term_months=term_months,
                purpose=purpose
            )
            
            # Update additional loan details
            loan.purpose_description = purpose_description
            loan.debt_to_income_ratio = debt_to_income_ratio
            
            # Set verification status
            loan.borrower_verified = borrower_verified
            
            if hasattr(borrower_profile, 'identity_verified'):
                loan.identity_verified = borrower_profile.identity_verified
            
            if hasattr(borrower_profile, 'income_verified'):
                loan.income_verified = borrower_profile.income_verified
            
            # Update loan history
            loan.previous_loans_count = previous_loans_count
            loan.previous_loans_repaid = previous_loans_repaid
            
            # Update secured loan details if applicable
            if is_secured:
                loan.is_secured = True
                loan.collateral_description = collateral_description
                loan.collateral_value = collateral_value
                
                # Calculate loan-to-value ratio
                if collateral_value > 0:
                    loan.loan_to_value_ratio = amount / collateral_value
            
            # Adjust interest rate if borrower is verified
            if borrower_verified:
                loan.interest_rate = max(loan.interest_rate - Decimal('1.5'), Decimal('5.0'))
                
            # Adjust interest rate for secured loans
            if is_secured and loan.loan_to_value_ratio < Decimal('0.8'):
                loan.interest_rate = max(loan.interest_rate - Decimal('1.0'), Decimal('5.0'))
            
            # Save updated loan
            loan.save()
            
            messages.success(request, f'Loan request "{title}" created successfully! It is now available for investors to fund.')
            return redirect('lending:loan_detail', loan_id=loan.id)
    else:
        form = LoanRequestForm()
    
    return render(request, 'lending/create_loan.html', {
        'form': form,
        'is_verified': borrower_verified
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

@login_required
def my_investments(request):
    """Display user's investments"""
    # Check if user is an investor
    try:
        if request.user.profile.user_type != 'investor':
            messages.warning(request, 'Only investors can view investments.')
            return redirect('home')
    except:
        messages.error(request, 'User profile not found.')
        return redirect('home')
    
    # Get all investments for this user
    investments = Investment.objects.filter(investor=request.user).order_by('-date_invested')
    
    # Group by status
    active_investments = investments.filter(loan__status__in=['active', 'funded'])
    completed_investments = investments.filter(loan__status__in=['repaid', 'defaulted'])
    
    # Calculate totals
    total_invested = investments.aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate returns
    total_returns = LoanPayment.objects.filter(
        loan__investments__investor=request.user,
        status='paid'
    ).aggregate(
        total=Sum('amount_due')
    )['total'] or 0
    
    context = {
        'investments': investments,
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'total_invested': total_invested,
        'total_returns': total_returns
    }
    
    return render(request, 'lending/my_investments.html', context)

@login_required
def my_loans(request):
    """Display user's loans"""
    # Check if user is a borrower
    try:
        if request.user.profile.user_type != 'borrower':
            messages.warning(request, 'Only borrowers can view their loans.')
            return redirect('home')
    except:
        messages.error(request, 'User profile not found.')
        return redirect('home')
    
    # Get all loans for this user
    loans = Loan.objects.filter(borrower=request.user).order_by('-created_at')
    
    # Group by status
    pending_loans = loans.filter(status='pending')
    active_loans = loans.filter(status__in(['active', 'funded']))
    completed_loans = loans.filter(status__in(['repaid', 'defaulted', 'cancelled']))
    
    # Calculate totals
    total_borrowed = loans.filter(status__in(['active', 'funded', 'repaid'])).aggregate(
        total=Sum('amount'))['total'] or 0
    
    # Calculate payments
    total_repaid = LoanPayment.objects.filter(
        loan__borrower=request.user,
        status='paid'
    ).aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    
    context = {
        'loans': loans,
        'pending_loans': pending_loans,
        'active_loans': active_loans,
        'completed_loans': completed_loans,
        'total_borrowed': total_borrowed,
        'total_repaid': total_repaid
    }
    
    return render(request, 'lending/my_loans.html', context)

@login_required
def portfolio_analysis(request):
    """Display detailed portfolio analysis for investors"""
    # Check if user is an investor
    try:
        if request.user.profile.user_type != 'investor':
            messages.warning(request, 'Only investors can view portfolio analysis.')
            return redirect('home')
    except:
        messages.error(request, 'User profile not found.')
        return redirect('home')
    
    # Get or create portfolio analysis for this investor
    try:
        portfolio = PortfolioAnalysis.objects.get(investor=request.user)
        # Recalculate metrics if requested or if last updated > 24 hours ago
        if request.GET.get('refresh') or (timezone.now() - portfolio.last_updated).days >= 1:
            portfolio.calculate_metrics()
    except PortfolioAnalysis.DoesNotExist:
        portfolio = PortfolioAnalysis(investor=request.user)
        portfolio.calculate_metrics()
    
    # Get all active investments
    investments = Investment.objects.filter(
        investor=request.user,
        loan__status__in=['pending', 'funded', 'active']
    ).order_by('-date_invested')
    
    # Get recent loan payments (returns)
    recent_payments = LoanPayment.objects.filter(
        loan__investments__investor=request.user,
        status='paid'
    ).order_by('-payment_date')[:10]
    
    # Calculate monthly returns for chart data
    monthly_returns = LoanPayment.objects.filter(
        loan__investments__investor=request.user,
        status='paid'
    ).values('payment_date__year', 'payment_date__month').annotate(
        month=F('payment_date__month'),
        year=F('payment_date__year'),
        returns=Sum('interest')
    ).order_by('payment_date__year', 'payment_date__month')[:12]
    
    # Format data for charts
    monthly_returns_labels = []
    monthly_returns_data = []
    
    for entry in monthly_returns:
        month_name = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }.get(entry['month'], '')
        
        monthly_returns_labels.append(f"{month_name} {entry['year']}")
        monthly_returns_data.append(float(entry['returns']))
    
    # Prepare diversification data for charts
    purpose_labels = list(portfolio.purpose_distribution.keys())
    purpose_data = list(portfolio.purpose_distribution.values())
    
    risk_labels = list(portfolio.risk_distribution.keys())
    risk_data = list(portfolio.risk_distribution.values())
    
    term_labels = list(portfolio.term_distribution.keys())
    term_data = list(portfolio.term_distribution.values())
    
    # Get loan recommendations based on investor's current portfolio
    # Logic: recommend loans in categories where the investor has less exposure
    recommendations = []
    
    # Find purposes with lower representation
    if portfolio.purpose_distribution:
        # Get the least represented purpose categories
        min_purposes = sorted(portfolio.purpose_distribution.items(), key=lambda x: x[1])[:2]
        min_purpose_names = [p[0] for p in min_purposes]
        
        # Find available loans with these purposes
        for purpose_name in min_purpose_names:
            purpose_code = next((code for code, name in Loan.LOAN_PURPOSE_CHOICES if name == purpose_name), None)
            if purpose_code:
                recommended_loans = Loan.objects.filter(
                    status='pending',
                    purpose=purpose_code
                ).exclude(
                    investments__investor=request.user
                )[:2]
                
                recommendations.extend(recommended_loans)
    
    # If we still need more recommendations, add some based on risk profile
    if len(recommendations) < 3:
        # Calculate investor's average risk preference
        invested_in_high_risk = portfolio.risk_distribution.get('High Risk (8-10)', 0) > 0
        
        # Recommend loans based on risk preference
        if invested_in_high_risk:
            # This investor accepts high risk, recommend some high return options
            high_return_loans = Loan.objects.filter(
                status='pending',
                interest_rate__gte=12
            ).exclude(
                investments__investor=request.user
            ).order_by('-interest_rate')[:2]
            
            recommendations.extend(high_return_loans)
        else:
            # This investor prefers lower risk, recommend safer options
            low_risk_loans = Loan.objects.filter(
                status='pending',
                risk_score__lte=5
            ).exclude(
                investments__investor=request.user
            ).order_by('risk_score')[:2]
            
            recommendations.extend(low_risk_loans)
    
    # Remove duplicates and limit to 5
    recommendations = list(dict.fromkeys(recommendations))[:5]
    
    context = {
        'portfolio': portfolio,
        'investments': investments,
        'recent_payments': recent_payments,
        'monthly_returns_labels': monthly_returns_labels,
        'monthly_returns_data': monthly_returns_data,
        'purpose_labels': purpose_labels,
        'purpose_data': purpose_data,
        'risk_labels': risk_labels,
        'risk_data': risk_data,
        'term_labels': term_labels,
        'term_data': term_data,
        'recommendations': recommendations,
    }
    
    return render(request, 'lending/portfolio_analysis.html', context)

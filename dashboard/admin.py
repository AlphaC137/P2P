from django.contrib import admin
from django.db.models import Sum, Count, Avg
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from accounts.models import UserProfile, Transaction, Wallet
from lending.models import Loan, Investment, LoanPayment
from .models import PlatformMetrics

# Admin site customization
admin.site.site_header = "P2P Lending Administration"
admin.site.site_title = "P2P Lending Admin Portal"
admin.site.index_title = "Platform Management"

@admin.register(PlatformMetrics)
class PlatformMetricsAdmin(admin.ModelAdmin):
    """Admin interface for platform metrics dashboard"""
    actions = None  # Explicitly set actions to None
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('metrics/', self.admin_site.admin_view(self.platform_metrics_view), name='platform-metrics'),
            path('reports/', self.admin_site.admin_view(self.platform_reports_view), name='platform-reports'),
        ]
        return custom_urls + urls
    
    def platform_metrics_view(self, request):
        """Admin view for platform-wide metrics"""
        
        # Calculate user metrics
        total_users = UserProfile.objects.count()
        investor_count = UserProfile.objects.filter(user_type='investor').count()
        borrower_count = UserProfile.objects.filter(user_type='borrower').count()
        verified_borrowers = UserProfile.objects.filter(
            user_type='borrower', 
            borrower_profile__verification_status='verified'
        ).count()
        
        # Calculate loan metrics
        total_loans = Loan.objects.count()
        active_loans = Loan.objects.filter(status__in=['active', 'funded']).count()
        pending_loans = Loan.objects.filter(status='pending').count()
        completed_loans = Loan.objects.filter(status='repaid').count()
        cancelled_loans = Loan.objects.filter(status__in=['cancelled', 'defaulted']).count()
        
        # Calculate financial metrics
        total_loan_volume = Loan.objects.filter(status__in=['active', 'funded', 'repaid']).aggregate(
            total=Sum('amount'))['total'] or 0
        total_investment_volume = Investment.objects.aggregate(total=Sum('amount'))['total'] or 0
        avg_loan_amount = Loan.objects.filter(status__in=['active', 'funded', 'repaid']).aggregate(
            avg=Avg('amount'))['avg'] or 0
        avg_interest_rate = Loan.objects.filter(status__in=['active', 'funded', 'repaid']).aggregate(
            avg=Avg('interest_rate'))['avg'] or 0
        
        # Calculate system balance
        total_system_balance = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0
        
        # Calculate payment metrics
        late_payments = LoanPayment.objects.filter(status='late').count()
        pending_payments = LoanPayment.objects.filter(status='pending').count()
        
        # Recent activity
        recent_loans = Loan.objects.all().order_by('-created_at')[:5]
        recent_investments = Investment.objects.all().order_by('-date_invested')[:5]
        recent_transactions = Transaction.objects.all().order_by('-timestamp')[:5]
        
        # Verification queue
        pending_verifications = UserProfile.objects.filter(
            user_type='borrower', 
            borrower_profile__verification_status='pending'
        ).count()
        
        context = {
            'title': 'Platform Metrics',
            # User metrics
            'total_users': total_users,
            'investor_count': investor_count,
            'borrower_count': borrower_count,
            'verified_borrowers': verified_borrowers,
            'verification_rate': round((verified_borrowers / borrower_count) * 100 if borrower_count > 0 else 0, 1),
            
            # Loan metrics
            'total_loans': total_loans,
            'active_loans': active_loans,
            'pending_loans': pending_loans,
            'completed_loans': completed_loans,
            'cancelled_loans': cancelled_loans,
            
            # Financial metrics
            'total_loan_volume': total_loan_volume,
            'total_investment_volume': total_investment_volume,
            'avg_loan_amount': avg_loan_amount,
            'avg_interest_rate': avg_interest_rate,
            'total_system_balance': total_system_balance,
            
            # Payment metrics
            'late_payments': late_payments,
            'pending_payments': pending_payments,
            
            # Recent activity
            'recent_loans': recent_loans,
            'recent_investments': recent_investments,
            'recent_transactions': recent_transactions,
            
            # Verification queue
            'pending_verifications': pending_verifications,
        }
        
        return render(request, 'admin/dashboard/metrics_dashboard.html', context)
    
    def platform_reports_view(self, request):
        """Admin view for generating platform reports"""
        import datetime
        
        # Get date filter parameters
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        # Default to last 6 months if no dates provided
        if not date_from:
            date_from = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Monthly loan volume
        monthly_loan_volume = Loan.objects.filter(status__in=['active', 'funded', 'repaid']).extra({
            'month': "strftime('%m', created_at)",
            'year': "strftime('%Y', created_at)"
        }).values('month', 'year').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('year', 'month')
        
        # Monthly investment volume
        monthly_investment_volume = Investment.objects.extra({
            'month': "strftime('%m', date_invested)",
            'year': "strftime('%Y', date_invested)"
        }).values('month', 'year').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('year', 'month')
        
        # User growth
        monthly_user_growth = UserProfile.objects.extra({
            'month': "strftime('%m', user__date_joined)",
            'year': "strftime('%Y', user__date_joined)"
        }).values('month', 'year', 'user_type').annotate(
            count=Count('id')
        ).order_by('year', 'month')
        
        # Payment performance
        payment_performance = LoanPayment.objects.extra({
            'month': "strftime('%m', due_date)",
            'year': "strftime('%Y', due_date)"
        }).values('month', 'year', 'status').annotate(
            count=Count('id'),
            total=Sum('amount_due')
        ).order_by('year', 'month')
        
        context = {
            'title': 'Platform Reports',
            'monthly_loan_volume': monthly_loan_volume,
            'monthly_investment_volume': monthly_investment_volume,
            'monthly_user_growth': monthly_user_growth,
            'payment_performance': payment_performance,
            'date_from': date_from,
            'date_to': date_to,
        }
        
        # Handle export formats
        export_format = request.GET.get('format')
        if export_format:
            if export_format == 'csv':
                # Implementation for CSV export would go here
                pass
            elif export_format == 'json':
                # Implementation for JSON export would go here
                pass
            elif export_format == 'pdf':
                # Implementation for PDF export would go here
                pass
        
        return render(request, 'admin/dashboard/reports_dashboard.html', context)
    
    def changelist_view(self, request, extra_context=None):
        """Redirect the changelist view to our metrics dashboard"""
        return self.platform_metrics_view(request)

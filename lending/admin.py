from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Loan, Investment, LoanPayment, PortfolioAnalysis

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'borrower_name', 'amount', 'interest_rate', 
                   'term_months', 'status', 'created_at', 'funding_progress', 'action_buttons')
    list_filter = ('status', 'purpose', 'risk_score', 'created_at', 'borrower_verified')
    search_fields = ('title', 'description', 'borrower__username', 'borrower__email')
    readonly_fields = ('borrower', 'created_at', 'current_funded_amount', 'risk_score')
    
    # Define actions as a list or None
    actions = None
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('borrower', 'title', 'description', 'amount', 'term_months', 'interest_rate', 'status', 'created_at')
        }),
        ('Purpose & Risk', {
            'fields': ('purpose', 'purpose_description', 'risk_score')
        }),
        ('Funding', {
            'fields': ('current_funded_amount', 'funding_deadline')
        }),
        ('Verification', {
            'fields': ('borrower_verified', 'identity_verified', 'income_verified')
        }),
        ('Secured Loan Info', {
            'fields': ('is_secured', 'collateral_description', 'collateral_value', 'loan_to_value_ratio'),
            'classes': ('collapse',)
        }),
        ('Historical Data', {
            'fields': ('previous_loans_count', 'previous_loans_repaid', 'debt_to_income_ratio'),
            'classes': ('collapse',)
        }),
    )
    
    def borrower_name(self, obj):
        return obj.borrower.username
    
    def funding_progress(self, obj):
        if obj.amount == 0:
            percentage = 0
        else:
            percentage = int((obj.current_funded_amount / obj.amount) * 100)
        
        return format_html(
            '<div style="width:100px; background-color:#f8f9fa; height:20px; border-radius:3px;">'
            '<div style="width:{}px; background-color:{}; height:20px; border-radius:3px;"></div>'
            '<span style="position:relative; top:-20px; text-align:center; display:block;">'
            '{}%</span></div>',
            percentage, '#28a745' if percentage == 100 else '#007bff', percentage
        )
    
    funding_progress.short_description = 'Funding'
    
    def action_buttons(self, obj):
        buttons = []
        
        # View button for all loans
        view_url = reverse('admin:lending_loan_change', args=[obj.id])
        buttons.append(f'<a class="button" href="{view_url}">View</a>')
        
        # Approve button for pending loans
        if obj.status == 'pending':
            approve_url = reverse('admin:approve_loan', args=[obj.id])
            buttons.append(f'<a class="button" href="{approve_url}">Approve</a>')
            
            # Reject button
            reject_url = reverse('admin:reject_loan', args=[obj.id])
            buttons.append(f'<a class="button" style="background-color: #ba2121;" href="{reject_url}">Reject</a>')
        
        return format_html('&nbsp;'.join(buttons))
    
    action_buttons.short_description = 'Actions'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/approve/', self.admin_site.admin_view(self.approve_loan), name='approve_loan'),
            path('<path:object_id>/reject/', self.admin_site.admin_view(self.reject_loan), name='reject_loan'),
        ]
        return custom_urls + urls
    
    def approve_loan(self, request, object_id, *args, **kwargs):
        loan = self.get_object(request, object_id)
        if loan.status == 'pending':
            # Only change status if not all funding is received yet
            if loan.current_funded_amount < loan.amount:
                loan.status = 'active'
                loan.save()
                self.message_user(request, f"Loan '{loan.title}' has been approved and is now active.", messages.SUCCESS)
            else:
                loan.status = 'funded'
                loan.save()
                self.message_user(request, f"Loan '{loan.title}' has been approved and is fully funded.", messages.SUCCESS)
        return HttpResponseRedirect("../")
    
    def reject_loan(self, request, object_id, *args, **kwargs):
        loan = self.get_object(request, object_id)
        if loan.status == 'pending':
            loan.status = 'cancelled'
            loan.save()
            self.message_user(request, f"Loan '{loan.title}' has been rejected.", messages.WARNING)
        return HttpResponseRedirect("../")

class LoanPaymentInline(admin.TabularInline):
    model = LoanPayment
    extra = 0
    fields = ('payment_number', 'due_date', 'amount_due', 'principal', 'interest', 'status', 'payment_date', 'amount_paid')
    readonly_fields = ('payment_number', 'due_date', 'amount_due', 'principal', 'interest')
    
    def has_delete_permission(self, request, obj=None):
        return False

class InvestmentInline(admin.TabularInline):
    model = Investment
    extra = 0
    fields = ('investor', 'amount', 'investment_percentage', 'date_invested')
    readonly_fields = ('investor', 'amount', 'investment_percentage', 'date_invested')
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'investor_name', 'loan_title', 'amount', 'investment_percentage', 'date_invested')
    list_filter = ('date_invested', 'loan__status')
    search_fields = ('investor__username', 'investor__email', 'loan__title')
    readonly_fields = ('investor', 'loan', 'amount', 'investment_percentage', 'date_invested')
    actions = None
    
    def investor_name(self, obj):
        return obj.investor.username
    
    def loan_title(self, obj):
        return obj.loan.title
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete investments for audit purposes
        return request.user.is_superuser

@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan_title', 'payment_number', 'due_date', 'amount_due', 
                   'status', 'payment_date', 'amount_paid', 'days_overdue_or_remaining')
    list_filter = ('status', 'due_date', 'payment_date')
    search_fields = ('loan__title', 'loan__borrower__username')
    readonly_fields = ('loan', 'payment_number', 'due_date', 'amount_due', 'principal', 'interest')
    
    # Fix the actions - Define it as a list of action methods
    actions = ['mark_as_paid', 'mark_as_late']
    
    def loan_title(self, obj):
        return obj.loan.title
    
    def days_overdue_or_remaining(self, obj):
        if obj.status == 'paid':
            return 'Paid'
        elif obj.status == 'late':
            days = obj.days_overdue()
            return format_html('<span style="color: red;">{} days overdue</span>', days)
        else:  # pending
            import datetime
            today = datetime.date.today()
            days = (obj.due_date - today).days
            if days < 0:
                return format_html('<span style="color: red;">{} days overdue</span>', abs(days))
            elif days <= 3:
                return format_html('<span style="color: orange;">{} days remaining</span>', days)
            else:
                return f'{days} days remaining'
    
    days_overdue_or_remaining.short_description = 'Status'
    
    def mark_as_paid(self, request, queryset):
        import datetime
        for payment in queryset.filter(status__in=['pending', 'late']):
            payment.status = 'paid'
            payment.payment_date = datetime.date.today()  # or use timezone.now().date()
            payment.amount_paid = payment.amount_due
            payment.save()
        
        self.message_user(request, f"{queryset.count()} payment(s) marked as paid.")
    
    mark_as_paid.short_description = "Mark selected payments as paid"
    
    def mark_as_late(self, request, queryset):
        for payment in queryset.filter(status='pending'):
            payment.status = 'late'
            payment.save()
        
        self.message_user(request, f"{queryset.count()} payment(s) marked as late.")
    
    mark_as_late.short_description = "Mark selected payments as late"
    
    def has_add_permission(self, request):
        return False

@admin.register(PortfolioAnalysis)
class PortfolioAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'investor_name', 'annual_return_rate', 'total_invested', 
                   'total_earnings', 'risk_adjusted_return', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('investor__username', 'investor__email')
    readonly_fields = ('investor', 'total_invested', 'total_earnings', 'expected_earnings', 
                      'annual_return_rate', 'avg_loan_risk_score', 'risk_adjusted_return',
                      'loan_count', 'loans_at_risk_count', 'avg_investment_amount',
                      'largest_investment_percentage', 'purpose_distribution', 
                      'risk_distribution', 'term_distribution', 'last_updated')
    
    # Define actions as a list of action methods
    actions = ['recalculate_metrics']
    
    def investor_name(self, obj):
        return obj.investor.username
    
    def recalculate_metrics(self, request, queryset):
        for portfolio in queryset:
            portfolio.calculate_metrics()
        
        self.message_user(request, f"Metrics recalculated for {queryset.count()} portfolio(s).")
    
    recalculate_metrics.short_description = "Recalculate portfolio metrics"

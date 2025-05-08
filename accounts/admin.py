from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.contrib import messages
from .models import UserProfile, InvestorProfile, BorrowerProfile, Wallet, Transaction

class InvestorProfileInline(admin.StackedInline):
    model = InvestorProfile
    can_delete = False
    verbose_name_plural = 'Investor Profile'
    
class BorrowerProfileInline(admin.StackedInline):
    model = BorrowerProfile
    can_delete = False
    verbose_name_plural = 'Borrower Profile'
    
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'user_type', 'phone_number', 'kyc_verified', 'date_of_birth', 'view_user')
    list_filter = ('user_type', 'kyc_verified')
    search_fields = ('user__username', 'user__email', 'phone_number')
    readonly_fields = ('user',)
    actions = None  # Explicitly set actions to None
    
    def get_inlines(self, request, obj=None):
        if obj:
            if obj.user_type == 'investor':
                return [InvestorProfileInline]
            elif obj.user_type == 'borrower':
                return [BorrowerProfileInline]
        return []
    
    def username(self, obj):
        return obj.user.username
    
    def view_user(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">View User</a>', url)
    
    view_user.short_description = 'User Account'

@admin.register(BorrowerProfile)
class BorrowerProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'verification_status', 'credit_score', 'annual_income', 'employment_status', 'verify_documents')
    list_filter = ('verification_status', 'employment_status', 'identity_verified', 'income_verified')
    search_fields = ('user_profile__user__username', 'user_profile__user__email')
    readonly_fields = ('user_profile', 'verification_submitted_at', 'verification_completed_at')
    actions = None  # Explicitly set actions to None
    
    fieldsets = (
        ('User Information', {
            'fields': ('user_profile',)
        }),
        ('Verification Status', {
            'fields': ('verification_status', 'identity_verified', 'income_verified', 
                      'verification_submitted_at', 'verification_completed_at')
        }),
        ('Financial Information', {
            'fields': ('credit_score', 'annual_income', 'employment_status', 'employer_name', 
                      'job_title', 'employment_duration_years', 'total_loans')
        }),
        ('Documents', {
            'fields': ('id_document', 'income_proof',)
        }),
    )
    
    def username(self, obj):
        return obj.user_profile.user.username
    
    def verify_documents(self, obj):
        if obj.verification_status == 'pending':
            approve_url = reverse('admin:approve_verification', args=[obj.id])
            reject_url = reverse('admin:reject_verification', args=[obj.id])
            return format_html(
                '<a class="button" href="{}">Approve</a>&nbsp;'
                '<a class="button" style="background-color: #ba2121;" href="{}">Reject</a>',
                approve_url, reject_url
            )
        return "-"
    
    verify_documents.short_description = 'Actions'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/approve/', self.admin_site.admin_view(self.approve_verification), name='approve_verification'),
            path('<path:object_id>/reject/', self.admin_site.admin_view(self.reject_verification), name='reject_verification'),
        ]
        return custom_urls + urls
    
    def approve_verification(self, request, object_id, *args, **kwargs):
        profile = self.get_object(request, object_id)
        profile.verification_status = 'verified'
        profile.identity_verified = True
        profile.income_verified = True
        profile.verification_completed_at = timezone.now()
        profile.save()
        
        # Update credit score based on verification documents
        profile.credit_score = min(profile.credit_score + 50, 850)  # Max credit score is 850
        profile.save()
        
        self.message_user(request, f"Verification for {profile.user_profile.user.username} has been approved.", messages.SUCCESS)
        return HttpResponseRedirect("../")
    
    def reject_verification(self, request, object_id, *args, **kwargs):
        profile = self.get_object(request, object_id)
        profile.verification_status = 'rejected'
        profile.verification_completed_at = timezone.now()
        profile.save()
        
        self.message_user(request, f"Verification for {profile.user_profile.user.username} has been rejected.", messages.ERROR)
        return HttpResponseRedirect("../")

@admin.register(InvestorProfile)
class InvestorProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'risk_tolerance', 'total_invested', 'total_earnings')
    list_filter = ('risk_tolerance',)
    search_fields = ('user_profile__user__username', 'user_profile__user__email')
    readonly_fields = ('user_profile', 'total_invested', 'total_earnings')
    actions = None  # Explicitly set actions to None
    
    def username(self, obj):
        return obj.user_profile.user.username

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('transaction_type', 'amount', 'timestamp', 'description', 'balance_after')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('username', 'balance', 'transaction_count')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'balance')
    inlines = [TransactionInline]
    actions = None  # Explicitly set actions to None
    
    def username(self, obj):
        return obj.user.username
    
    def transaction_count(self, obj):
        return obj.transactions.count()
    
    transaction_count.short_description = 'Transactions'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'transaction_type', 'amount', 'timestamp', 'balance_after')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('wallet__user__username', 'wallet__user__email', 'description')
    readonly_fields = ('wallet', 'transaction_type', 'amount', 'timestamp', 'description', 'balance_after', 
                       'related_entity_type', 'related_entity_id')
    actions = None  # Explicitly set actions to None
    
    def username(self, obj):
        return obj.wallet.user.username
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete transactions for audit purposes
        return request.user.is_superuser

from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    
    # Registration
    path('register/investor/', views.register_investor, name='register_investor'),
    path('register/borrower/', views.register_borrower, name='register_borrower'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    
    # Wallet
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/deposit/', views.deposit_funds, name='deposit_funds'),
    path('wallet/withdraw/', views.withdraw_funds, name='withdraw_funds'),
    path('wallet/statistics/', views.wallet_statistics, name='wallet_statistics'),
    path('wallet/transaction/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    
    # Verification
    path('verification/', views.borrower_verification, name='verification'),
]
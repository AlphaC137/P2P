from django.urls import path
from . import views

app_name = 'lending'

urlpatterns = [
    # Marketplace
    path('marketplace/', views.marketplace, name='marketplace'),
    path('loan/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    
    # Create Loan
    path('create-loan/', views.create_loan, name='create_loan'),
    
    # Investments
    path('loan/<int:loan_id>/invest/', views.invest, name='invest'),
    
    # Repayments
    path('loan/<int:loan_id>/repay/', views.repay_loan, name='repay_loan'),
]
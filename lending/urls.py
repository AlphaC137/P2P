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
    path('my-investments/', views.my_investments, name='my_investments'),
    path('my-loans/', views.my_loans, name='my_loans'),
    path('portfolio-analysis/', views.portfolio_analysis, name='portfolio_analysis'),
    
    # Repayments
    path('loan/<int:loan_id>/repay/', views.repay_loan, name='repay_loan'),
]
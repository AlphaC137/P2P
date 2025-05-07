from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home_dashboard, name='home'),
    path('investor/', views.investor_dashboard, name='investor'),
    path('borrower/', views.borrower_dashboard, name='borrower'),
]
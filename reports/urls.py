from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('profit-loss/', views.profit_loss_report, name='profit_loss'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
]
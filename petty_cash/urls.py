from django.urls import path
from . import views

app_name = 'petty_cash'

urlpatterns = [
    path('', views.petty_cash_list, name='list'),
    path('create/', views.petty_cash_create, name='create'),
    path('finance/review/', views.finance_review_petty_cash, name='finance_review'),
    path('finance/approve/<int:pk>/', views.finance_approve_petty_cash, name='finance_approve'),
]
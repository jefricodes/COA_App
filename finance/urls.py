from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('review/reimbursement/', views.review_reimbursements, name='review_reimbursements'),
    path('review/reimbursement/<int:pk>/approve/', views.approve_reimbursement, name='approve_reimbursement'),
    path('review/reimbursement/<int:pk>/reject/', views.reject_reimbursement, name='reject_reimbursement'),
    path('monthly-close/', views.monthly_close, name='monthly_close'),
    path('general-transaction/', views.general_transaction_list, name='general_transaction_list'),
    path('general-transaction/create/', views.general_transaction_create, name='general_transaction_create'),
]

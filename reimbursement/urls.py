from django.urls import path
from . import views

app_name = 'reimbursement'

urlpatterns = [
    path('', views.reimbursement_list, name='list'),
    path('create/', views.reimbursement_create, name='create'),
    path('<int:pk>/', views.reimbursement_detail, name='detail'),
    path('<int:pk>/edit/', views.reimbursement_edit, name='edit'),
]
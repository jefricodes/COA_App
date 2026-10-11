from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('pending-users/', views.pending_users_list,name='pending_users_list'),
    path('approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
]
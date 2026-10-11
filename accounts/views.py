from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.messages import get_messages
from .forms import UserRegistrationForm, CustomAuthenticationForm
from .models import CustomUser


def login_view(request):
    storage = get_messages(request)
    for _ in storage:
        pass

    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            if not user.is_active:
                messages.error(request, 'Akun Anda belum diaktifkan. Silakan hubungi Administrator.')
                return render(request, 'accounts/login.html', {'form': form})

            login(request, user)
            messages.success(request, f'Selamat datang, {user.first_name or user.username}!')
            
            next_url = request.GET.get('next', 'dashboard:index')
            return redirect(next_url)
        else:
            messages.error(request, 'Username atau password salah, atau akun belum diaktifkan.')
    else:
        form = CustomAuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Anda telah logout.')
    return redirect('accounts:login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            messages.success(
                request,
                'Registrasi berhasil! Akun Anda sedang menunggu persetujuan dari Administrator. '
            )
            return redirect('accounts:login')
        else:
            error_messages = []
            for field, errors in form.errors.items():
                if field == '__all__':
                    error_messages.extend(errors)
                else:
                    field_labels = {
                        'username': 'Username',
                        'email': 'Email',
                        'password1': 'Password',
                        'password2': 'Konfirmasi Password',
                        'employee_id': 'NIP/Employee ID',
                        'full_name': 'Nama Lengkap',
                        'position': 'Jabatan',
                        'department': 'Departemen',
                        'first_name': 'Nama Depan',
                        'last_name': 'Nama Belakang',
                    }
                    label = field_labels.get(field, field)
                    for error in errors:
                        error_messages.append(f"{label}: {error}")
            
            messages.error(request, 'Data yang Anda masukkan tidak valid. Silakan periksa kembali form pendaftaran.')
            
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def is_superuser_check(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(is_superuser_check)
def pending_users_list(request):
    pending_users = CustomUser.objects.filter(is_active=False).order_by('-date_joined')
    
    context = {
        'pending_users': pending_users
    }
    return render(request, 'accounts/pending_users.html', context)


@login_required
@user_passes_test(is_superuser_check)
def approve_user(request, user_id):
    user_to_approve = get_object_or_404(CustomUser, id=user_id, is_active=False)
    
    if request.method == 'POST':
        user_to_approve.is_active = True
        user_to_approve.save()
        messages.success(request, f'Akun untuk {user_to_approve.username} ({user_to_approve.get_full_name()}) berhasil diaktifkan!')
    else:
        messages.error(request, 'Metode tidak diizinkan.')
        
    return redirect('accounts:pending_users_list')



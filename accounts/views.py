from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.messages import get_messages
from .forms import SimpleRegistrationForm, CustomAuthenticationForm, EmployeeProfileForm
from .models import CustomUser


def login_view(request):
    from django.contrib.messages import get_messages
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
            messages.error(request, 'Email/Username atau password yang Anda masukkan salah.')
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
        form = SimpleRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                'Registrasi berhasil! Silakan login. Anda akan diminta melengkapi data profil setelah masuk.'
            )
            return redirect('accounts:login')
    else:
        form = SimpleRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def complete_profile_view(request):
    if hasattr(request.user, 'employee_profile'):
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = EmployeeProfileForm(request.POST)
        if form.is_valid():

            employee = form.save(commit=False)
            employee.user = request.user
            employee.is_active = True
            employee.save()
            
            emp_id_value = form.cleaned_data.get('employee_id')
            if emp_id_value:
                request.user.employee_id = emp_id_value
                request.user.save(update_fields=['employee_id'])

            messages.success(request, 'Data profil berhasil disimpan! Anda sekarang dapat membuat request.')
            return redirect('dashboard:index')
    else:
        initial_data = {'employee_id': request.user.employee_id}
        form = EmployeeProfileForm(initial=initial_data)

    return render(request, 'accounts/complete_profile.html', {'form': form})


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



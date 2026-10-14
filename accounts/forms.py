from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import password_validation
from django.utils import timezone
from .models import CustomUser, Department, Employee
from django.contrib.auth import authenticate


class SimpleRegistrationForm(forms.Form):
    email = forms.EmailField(
        label='Email Perusahaan',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'nama@perusahaan.com',
            'autocomplete': 'email'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimal 8 karakter',
        }),
        help_text=password_validation.password_validators_help_text_html()
    )
    password2 = forms.CharField(
        label='Konfirmasi Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ulangi password',
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Email ini sudah terdaftar. Silakan gunakan email lain atau login.")
        return email

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Password tidak cocok!')
        password_validation.validate_password(p1)
        return p2

    def save(self):
        email = self.cleaned_data['email']
        username = f"user_{int(timezone.now().timestamp())}" 
        
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=self.cleaned_data['password1'],
            role='staff',          
            is_active=True         
        )
        return user

class EmployeeProfileForm(forms.ModelForm):

    employee_id = forms.CharField(
        label='NIP / NIK / ID Karyawan',
        max_length=20,
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Contoh: 199001012023...'
        })
    )

    class Meta:
        model = Employee
        fields = ['full_name', 'department', 'position'] 
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama Lengkap sesuai KTP'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Jabatan / Posisi'}),
        }


# ==========================================
# 3. FORM LOGIN
# ==========================================
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django import forms
from .models import CustomUser

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email atau Username",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email atau Username',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        })
    )

    def clean(self):
        username_input = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username_input and password:
            auth_username = username_input
            
            if '@' in username_input:
                user = CustomUser.objects.filter(email__iexact=username_input).first()
                if user:
                    auth_username = user.username
            
            self.user_cache = authenticate(self.request, username=auth_username, password=password)
            
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data
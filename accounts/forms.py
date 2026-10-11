from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import password_validation 
from .models import CustomUser, Department

class UserRegistrationForm(forms.ModelForm):

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimal 8 karakter, kombinasi huruf & angka',
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

    full_name = forms.CharField(
        label='Nama Lengkap',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama lengkap'})
    )
    
    position = forms.CharField(
        label='Jabatan',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Jabatan/Posisi'})
    )



    class Meta:
        model = CustomUser 
        fields = ['username', 'email', 'employee_id', 'department', 'role', 'position']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username untuk login'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@perusahaan.com'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: EMP001'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Jabatan'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [('staff', 'Staff')] 
        self.fields['role'].initial = 'staff'

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Password tidak cocok!')
        
        password_validation.validate_password(p1, self.instance)
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_active = False 
        
        full_name = self.cleaned_data.get('full_name', '').split(' ', 1)
        user.first_name = full_name[0] if len(full_name) > 0 else ''
        user.last_name = full_name[1] if len(full_name) > 1 else ''

        if commit:
            user.save()
            
            from .models import Employee
            from django.utils import timezone
            
            Employee.objects.create(
                user=user,
                department=user.department,
                full_name=self.cleaned_data.get('full_name', user.username),
                position=self.cleaned_data.get('position', ''),
                join_date=timezone.now().date(),
                is_active=True,
            )
        
        return user

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )
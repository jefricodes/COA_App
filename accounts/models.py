from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):

    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('accountant', 'Akuntan'),
        ('manager', 'Manager Keuangan'),
        ('auditor', 'Auditor'),
        ('admin', 'Administrator'),
    ]
    
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="NIK / ID Karyawan")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff', verbose_name="Peran")
    department = models.ForeignKey('Department', on_delete=models.PROTECT, null=True, blank=True, related_name='users')
    
    is_2fa_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Pengguna'
        verbose_name_plural = 'Pengguna'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_accountant(self):
        return self.is_superuser or self.role in ['accountant', 'manager', 'admin']

    @property
    def is_approver(self):
        return self.is_superuser or self.role in ['manager', 'admin']

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Departemen'
        verbose_name_plural = 'Departemen'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Employee(models.Model):

    user = models.OneToOneField(CustomUser, on_delete=models.PROTECT, related_name='employee_profile')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    
    full_name = models.CharField(max_length=200)
    position = models.CharField(max_length=100, blank=True)
    join_date = models.DateField(null=True, blank=True) 
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} - {self.department.name}"
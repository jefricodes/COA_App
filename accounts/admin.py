from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Department, Employee, CustomUser

# 1. Konfigurasi Admin untuk CustomUser (Pengganti User bawaan Django)
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Menambahkan field kustom ke list tampilan
    list_display = ['username', 'email', 'employee_id', 'role', 'department', 'is_staff', 'is_active']
    list_filter = ['role', 'department', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'employee_id', 'first_name', 'last_name']
    ordering = ['username']

    # Menambahkan field kustom ke form tambah/edit user
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Karyawan & Peran', {
            'fields': ('employee_id', 'role', 'department', 'is_2fa_enabled'),
        }),
    )
    
    # Field yang muncul saat membuat user baru (Add form)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informasi Karyawan & Peran', {
            'fields': ('employee_id', 'role', 'department'),
        }),
    )


# 2. Konfigurasi Admin untuk Department
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    list_editable = ['is_active']


# 3. Konfigurasi Admin untuk Employee (DIPERBAIKI)
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Hapus 'employee_id' langsung, ganti dengan fungsi custom
    list_display = ['full_name', 'get_employee_id', 'department', 'position', 'is_active']
    list_filter = ['department', 'is_active']
    
    # Cari berdasarkan user yang berelasi
    search_fields = ['full_name', 'user__employee_id', 'user__username']
    list_per_page = 25

    # Hapus 'employee_id' dari fieldsets karena itu milik User, bukan Employee
    fieldsets = (
        ('Informasi Akun', {
            'fields': ('user',), # Hanya user, employee_id diurus di menu Users
            'description': 'Hubungkan ke user account. NIK/ID Karyawan diatur di menu Users.'
        }),
        ('Informasi Pribadi', {
            'fields': ('full_name', 'position', 'department'),
        }),
        ('Status', {
            'fields': ('is_active',),
            'classes': ('collapse',),
        }),
    )

    # Fungsi custom untuk mengambil employee_id dari model User yang berelasi
    def get_employee_id(self, obj):
        if obj.user:
            return obj.user.employee_id
        return "-"
    
    get_employee_id.short_description = 'ID Karyawan (NIK)'
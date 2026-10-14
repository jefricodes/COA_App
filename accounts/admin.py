from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Department, Employee, CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'employee_id', 'role', 'department', 'is_staff', 'is_active']
    list_filter = ['role', 'department', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'employee_id', 'first_name', 'last_name']
    ordering = ['username']

    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Karyawan & Peran', {
            'fields': ('employee_id', 'role', 'department', 'is_2fa_enabled'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informasi Karyawan & Peran', {
            'fields': ('employee_id', 'role', 'department'),
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    list_editable = ['is_active']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'get_employee_id', 'department', 'position', 'is_active']
    list_filter = ['department', 'is_active']
    search_fields = ['full_name', 'user__employee_id', 'user__username']
    list_per_page = 25

    fieldsets = (
        ('Informasi Akun', {
            'fields': ('user',),
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

    def get_employee_id(self, obj):
        if obj.user:
            return obj.user.employee_id
        return "-"
    
    get_employee_id.short_description = 'ID Karyawan (NIK)'
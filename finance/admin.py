from django.contrib import admin
from .models import MonthlyClose, GeneralTransaction


@admin.register(MonthlyClose)
class MonthlyCloseAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'status', 'total_revenue', 'total_expense', 'net_profit', 'closed_by', 'closed_at']
    list_filter = ['status', 'period_year', 'period_month']
    search_fields = ['period_year', 'period_month']
    readonly_fields = ['closed_at', 'total_revenue', 'total_expense', 'net_profit']
    
    fieldsets = (
        ('Periode', {
            'fields': ('period_month', 'period_year', 'status')
        }),
        ('Hasil Perhitungan', {
            'fields': ('total_revenue', 'total_expense', 'net_profit')
        }),
        ('Informasi Penutup', {
            'fields': ('closed_by', 'closed_at', 'notes')
        }),
    )


@admin.register(GeneralTransaction)
class GeneralTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'transaction_date', 'description', 'amount', 'transaction_type', 'department']
    list_filter = ['transaction_type', 'department', 'transaction_date']
    search_fields = ['transaction_number', 'description']

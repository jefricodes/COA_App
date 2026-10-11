from django.contrib import admin
from .models import PettyCashEntry

@admin.register(PettyCashEntry)
class PettyCashEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'entry_date', 'entry_type', 'department', 'amount', 'status', 'account']
    list_filter = ['status', 'entry_type', 'department', 'entry_date']
    search_fields = ['entry_number', 'description']
    readonly_fields = ['entry_number', 'created_by', 'created_at']
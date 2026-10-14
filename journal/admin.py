from django.contrib import admin
from .models import ChartOfAccount, JournalEntry, JournalEntryLine


@admin.register(ChartOfAccount)
class ChartOfAccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'is_active']
    list_filter = ['account_type', 'is_active']
    search_fields = ['code', 'name']


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 2


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['journal_number', 'entry_date', 'department', 'status', 'total_debit', 'total_credit', 'is_posted']
    list_filter = ['status', 'department', 'entry_date', 'is_posted']
    search_fields = ['journal_number', 'description']
    readonly_fields = ['journal_number', 'created_by', 'created_at']
    inlines = [JournalEntryLineInline]

    def total_debit(self, obj):
        return obj.total_debit
    total_debit.short_description = 'Total Debit'

    def total_credit(self, obj):
        return obj.total_credit
    total_credit.short_description = 'Total Kredit'
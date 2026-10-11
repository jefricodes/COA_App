from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from accounts.models import Department
from decimal import Decimal

class GeneralTransaction(models.Model):
    transaction_number = models.CharField(max_length=30, unique=True)
    transaction_date = models.DateField()
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField()
    transaction_type = models.CharField(max_length=20, choices=[
        ('income', 'Pemasukan'),
        ('expense', 'Pengeluaran'),
        ('transfer', 'Transfer Antar Akun'),
    ])
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    account = models.ForeignKey('journal.ChartOfAccount', on_delete=models.PROTECT)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='general_transactions')
    journal_entry = models.ForeignKey('journal.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.transaction_number} - {self.description[:50]}"


class MonthlyClose(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'Sedang Diproses'),
        ('completed', 'Selesai'),
    ]

    period_month = models.PositiveIntegerField()
    period_year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='monthly_closes')
    closed_at = models.DateTimeField(auto_now_add=True)

    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['period_month', 'period_year']
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        months = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                  'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        return f"Tutup Buku {months[self.period_month]} {self.period_year}"

    def calculate_totals(self):
        from journal.models import JournalEntryLine
        from django.db.models import Sum

        journal_lines = JournalEntryLine.objects.filter(
            journal__status='approved',
            journal__period_month=self.period_month,
            journal__period_year=self.period_year,
            journal__is_posted=True
        )

        revenue_lines = journal_lines.filter(account__account_type='revenue')
        self.total_revenue = revenue_lines.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')

        expense_lines = journal_lines.filter(account__account_type='expense')
        self.total_expense = expense_lines.aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')

        self.net_profit = self.total_revenue - self.total_expense

    def close_period(self):
        from journal.models import JournalEntry

        with transaction.atomic():
            self.calculate_totals()

            JournalEntry.objects.filter(
                period_month=self.period_month,
                period_year=self.period_year,
                status='approved'
            ).update(is_posted=True)

            self.status = 'completed'
            self.save()
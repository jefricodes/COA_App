from django.db import models, transaction
from django.conf import settings # GANTI User dengan ini
from accounts.models import Department
from journal.models import ChartOfAccount
import datetime

class PettyCashEntry(models.Model):
    ENTRY_TYPES = [
        ('in', 'Uang Masuk'),
        ('out', 'Uang Keluar'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Menunggu Review'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ]

    entry_number = models.CharField(max_length=30, unique=True)
    entry_date = models.DateField()
    entry_type = models.CharField(max_length=5, choices=ENTRY_TYPES)
    
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    
    # DIPERBAIKI: Menggunakan settings.AUTH_USER_MODEL
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='petty_cash_entries')
    
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_petty_cash')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    receipt_file = models.FileField(upload_to='petty_cash/%Y/%m/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-id']

    def __str__(self):
        direction = "Masuk" if self.entry_type == 'in' else "Keluar"
        return f"{self.entry_number} - {direction} Rp {self.amount}"

    def save(self, *args, **kwargs):
        if not self.entry_number:
            year = self.entry_date.year if self.entry_date else datetime.date.today().year
            dept_code = self.department.code
            prefix = "PCIN" if self.entry_type == 'in' else "PCOUT"
            
            # PERBAIKAN RACE CONDITION: Bungkus dalam transaction.atomic
            with transaction.atomic():
                count = PettyCashEntry.objects.filter(
                    department=self.department,
                    entry_date__year=year,
                    entry_type=self.entry_type
                ).count() + 1
                
                self.entry_number = f"{prefix}-{dept_code}-{year}-{count:04d}"
            
        super().save(*args, **kwargs)
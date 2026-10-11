from django.db import models, transaction
from django.conf import settings # GANTI User dengan ini
from accounts.models import Department, Employee
import datetime

class ReimbursementRequest(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Menunggu Review'), 
        ('approved', 'Disetujui'), 
        ('rejected', 'Ditolak'), 
        ('paid', 'Sudah Dibayar')
    ]

    request_number = models.CharField(max_length=30, unique=True)
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='reimbursements')
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    request_date = models.DateField(auto_now_add=True)
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    receipt_file = models.FileField(upload_to='receipts/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    # DIPERBAIKI: Menggunakan settings.AUTH_USER_MODEL
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reimbursements')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-request_date', '-id']

    def __str__(self):
        return f"{self.request_number} - {self.employee.full_name}"

    def save(self, *args, **kwargs):
        if not self.request_number:
            year = self.request_date.year if self.request_date else datetime.date.today().year
            
            # PERBAIKAN RACE CONDITION: Bungkus dalam transaction.atomic
            with transaction.atomic():
                count = ReimbursementRequest.objects.filter(
                    department=self.department, 
                    request_date__year=year
                ).count() + 1
                self.request_number = f"RMB-{self.department.code}-{year}-{count:04d}"
                
        super().save(*args, **kwargs)
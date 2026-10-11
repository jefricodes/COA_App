from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class ChartOfAccount(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'Aset'),
        ('liability', 'Liabilitas'),
        ('equity', 'Ekuitas'),
        ('revenue', 'Pendapatan'),
        ('expense', 'Beban'),
    ]
    code = models.CharField(max_length=20, unique=True, verbose_name="Kode Akun")
    name = models.CharField(max_length=200, verbose_name="Nama Akun")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, verbose_name="Tipe Akun")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        ordering = ['code']
        verbose_name = "Chart of Account"
        verbose_name_plural = "Chart of Accounts"

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def normal_balance(self):
        return 'debit' if self.account_type in ['asset', 'expense'] else 'credit'


class JournalEntry(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    journal_number = models.CharField(max_length=30, unique=True, verbose_name="No. Jurnal")
    entry_date = models.DateField(verbose_name="Tanggal Jurnal")
    description = models.TextField(verbose_name="Deskripsi", blank=True)
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.PROTECT,
        verbose_name="Departemen"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='journal_entries',
        verbose_name="Dibuat Oleh"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Status"
    )
    is_posted = models.BooleanField(default=False, verbose_name="Sudah Diposting")
    period_month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Bulan Periode"
    )
    period_year = models.PositiveIntegerField(verbose_name="Tahun Periode")

    total_debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total Debit"
    )
    total_credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total Kredit"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-journal_number']
        verbose_name = "Jurnal"
        verbose_name_plural = "Jurnal"

    def __str__(self):
        return f"{self.journal_number} - {self.description[:30]}"

    def _calculate_totals(self):
        from django.db.models import Sum
        totals = self.lines.aggregate(
            d=Sum('debit_amount'),
            c=Sum('credit_amount')
        )
        self.total_debit = totals['d'] or Decimal('0.00')
        self.total_credit = totals['c'] or Decimal('0.00')

    def clean(self):
        super().clean()

        if self.is_posted and self.total_debit != self.total_credit:
            raise ValidationError('Jurnal yang diposting harus seimbang (Debit = Kredit)!')

        if self.pk:
            try:
                old_instance = JournalEntry.objects.get(pk=self.pk)
                if old_instance.is_posted:
                    raise ValidationError(
                        'Jurnal yang sudah diposting TIDAK BOLEH diubah. '
                        'Buat jurnal pembalik jika ada kesalahan.'
                    )
            except JournalEntry.DoesNotExist:
                pass

    def save(self, *args, **kwargs):

        if self.pk:
            try:
                self._calculate_totals()
            except Exception:
                pass
        super().save(*args, **kwargs)


class JournalEntryLine(models.Model):
    journal = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Jurnal"
    )
    account = models.ForeignKey(
        ChartOfAccount,
        on_delete=models.PROTECT,
        verbose_name="Akun"
    )
    description = models.CharField(max_length=200, verbose_name="Deskripsi Baris")
    debit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Debit"
    )
    credit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Kredit"
    )

    class Meta:
        verbose_name = "Baris Jurnal"
        verbose_name_plural = "Baris Jurnal"

    def clean(self):
        super().clean()
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValidationError('Satu baris tidak boleh memiliki debit DAN kredit sekaligus!')
        if self.debit_amount == 0 and self.credit_amount == 0:
            raise ValidationError('Salah satu nominal (debit atau kredit) harus diisi!')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.journal_id:
            self.journal._calculate_totals()
            self.journal.save(update_fields=['total_debit', 'total_credit', 'updated_at'])
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime

from reimbursement.models import ReimbursementRequest
from journal.models import ChartOfAccount, JournalEntry, JournalEntryLine
from accounts.models import Department
from .models import MonthlyClose, GeneralTransaction
from .forms import GeneralTransactionForm


def is_finance_approver(user):
    return user.is_authenticated and getattr(user, 'is_approver', False)

finance_approver_required = user_passes_test(
    is_finance_approver,
    login_url='/accounts/login/'
)


@finance_approver_required
def review_reimbursements(request):
    reimbursements = ReimbursementRequest.objects.filter(status='submitted')
    
    dept_filter = request.GET.get('department')
    if dept_filter:
        reimbursements = reimbursements.filter(department_id=dept_filter)
    
    departments = Department.objects.filter(is_active=True)
    
    context = {
        'reimbursements': reimbursements,
        'departments': departments,
        'dept_filter': dept_filter,
    }
    return render(request, 'finance/review_reimbursements.html', context)


@finance_approver_required
@transaction.atomic 
def approve_reimbursement(request, pk):
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)
    
    if reimbursement.status != 'submitted':
        messages.error(request, 'Request ini sudah diproses.')
        return redirect('finance:review_reimbursements')
    
    if request.method == 'POST':
        try:
            reimbursement.status = 'approved'
            reimbursement.reviewed_by = request.user
            reimbursement.reviewed_at = timezone.now()
            reimbursement.save()

            _create_journal_for_reimbursement(reimbursement, request.user)
            
            messages.success(request, f'Reimbursement {reimbursement.request_number} disetujui dan Jurnal terbuat!')
            
        except ValidationError as e:
            messages.error(request, f'Gagal menyetujui: {e.message}')
            return redirect('finance:review_reimbursements')
        except Exception as e:
            messages.error(request, 'Terjadi kesalahan sistem saat membuat jurnal.')
            return redirect('finance:review_reimbursements')
    
    return redirect('finance:review_reimbursements')


@finance_approver_required
def reject_reimbursement(request, pk):
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)
    
    if reimbursement.status != 'submitted':
        messages.error(request, 'Request ini sudah diproses.')
        return redirect('finance:review_reimbursements')
    
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '')
        
        if not reason:
            messages.error(request, 'Alasan penolakan wajib diisi!')
            return redirect('finance:review_reimbursements')
        
        reimbursement.status = 'rejected'
        reimbursement.reviewed_by = request.user
        reimbursement.reviewed_at = timezone.now()
        reimbursement.rejection_reason = reason
        reimbursement.save()
        
        messages.warning(request, f'Reimbursement {reimbursement.request_number} ditolak.')
    
    return redirect('finance:review_reimbursements')


def _create_journal_for_reimbursement(reimbursement, user):
    expense_account = ChartOfAccount.objects.filter(
        code__startswith='5-', 
        name__icontains='reimbursement'
    ).first()
    
    cash_account = ChartOfAccount.objects.filter(
        code__startswith='1-', 
        name__icontains='kas'
    ).first()
    
    if not expense_account or not cash_account:
        raise ValidationError("COA untuk Beban Reimbursement atau Kas belum disetup.")
    
    today = timezone.now().date()
    
    # Buat Journal Entry
    journal = JournalEntry.objects.create(
        journal_number=f"JRN-AUTO-{today.strftime('%Y%m%d')}-{reimbursement.id}",
        entry_date=today,
        description=f"Reimbursement {reimbursement.request_number} - {reimbursement.description[:100]}",
        department=reimbursement.department,
        created_by=user,
        status='approved',
        is_posted=True,
        period_month=today.month,
        period_year=today.year,
    )
    
    JournalEntryLine.objects.create(
        journal=journal,
        account=expense_account,
        description=f"Reimbursement {reimbursement.request_number}",
        debit_amount=reimbursement.amount,
        credit_amount=Decimal('0.00'),
    )
    
    JournalEntryLine.objects.create(
        journal=journal,
        account=cash_account,
        description=f"Reimbursement {reimbursement.request_number}",
        debit_amount=Decimal('0.00'),
        credit_amount=reimbursement.amount,
    )
    
    journal._calculate_totals()
    journal.save(update_fields=['total_debit', 'total_credit'])


@finance_approver_required
@transaction.atomic 
def monthly_close(request):
    if request.method == 'POST':
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))

        existing = MonthlyClose.objects.filter(period_month=month, period_year=year).first()
        if existing and existing.status == 'completed':
            messages.error(request, f'Periode {month}/{year} sudah ditutup sebelumnya!')
            return redirect('finance:monthly_close')

        pending_journals = JournalEntry.objects.filter(
            period_month=month, period_year=year, status='submitted'
        )
        if pending_journals.exists():
            messages.error(request, f'Gagal! Masih ada {pending_journals.count()} jurnal yang belum di-review.')
            return redirect('finance:monthly_close')

        try:
            mc, created = MonthlyClose.objects.get_or_create(
                period_month=month, period_year=year,
                defaults={'closed_by': request.user}
            )
            
            mc.closed_by = request.user
            mc.close_period()

            messages.success(request, f'✅ Tutup buku {month}/{year} berhasil! Laba/Rugi: Rp {mc.net_profit}')
        except Exception as e:
            messages.error(request, f'Gagal melakukan tutup buku: {str(e)}')
            
        return redirect('finance:monthly_close')

    today = timezone.now()
    closed_periods = MonthlyClose.objects.all().order_by('-period_year', '-period_month')

    context = {
        'closed_periods': closed_periods,
        'current_month': today.month,
        'current_year': today.year,
        'month_names': {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
            7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
    }
    return render(request, 'finance/monthly_close.html', context)


# ==========================================
# GENERAL TRANSACTION VIEWS
# ==========================================

@finance_approver_required
def general_transaction_list(request):
    """Menampilkan daftar General Transaction."""
    transactions = GeneralTransaction.objects.all().order_by('-transaction_date')
    
    # Filter opsional berdasarkan tipe transaksi
    type_filter = request.GET.get('type')
    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)

    context = {
        'transactions': transactions,
        'type_filter': type_filter,
    }
    return render(request, 'finance/general_transaction_list.html', context)


@finance_approver_required
@transaction.atomic
def general_transaction_create(request):
    """Membuat General Transaction dan otomatis membuat Jurnal Entry."""
    if request.method == 'POST':
        form = GeneralTransactionForm(request.POST)
        if form.is_valid():
            try:
                # 1. Simpan General Transaction dulu (tanpa nomor & jurnal)
                gt = form.save(commit=False)
                gt.created_by = request.user
                gt.transaction_number = "TEMP"
                gt.save()

                # Update nomor transaksi setelah ID didapat
                gt.transaction_number = f"GT-{gt.transaction_date.strftime('%Y%m%d')}-{gt.id:04d}"
                gt.save(update_fields=['transaction_number'])

                # 2. Cari Akun Kas (Counterpart)
                cash_account = ChartOfAccount.objects.filter(
                    code__startswith='1-', 
                    name__icontains='kas',
                    is_active=True
                ).first()

                if not cash_account:
                    # Hapus GT yang baru dibuat agar tidak ada data sampah
                    gt.delete()
                    messages.error(request, 
                        "Akun Kas (dengan kode 1-xxx dan nama mengandung 'Kas') tidak ditemukan di Chart of Account. "
                        "Silakan buat akun Kas terlebih dahulu di Django Admin.")
                    return redirect('finance:general_transaction_create')

                # 3. Validasi akun yang dipilih user
                if not gt.account:
                    gt.delete()
                    messages.error(request, "Akun transaksi harus dipilih!")
                    return redirect('finance:general_transaction_create')

                # 4. Buat Journal Entry Otomatis
                journal = JournalEntry.objects.create(
                    journal_number=f"JRN-GT-{gt.transaction_date.strftime('%Y%m%d')}-{gt.id:04d}",
                    entry_date=gt.transaction_date,
                    description=f"General Transaction: {gt.description[:100]}",
                    department=gt.department,
                    created_by=request.user,
                    status='approved',
                    is_posted=True,
                    period_month=gt.transaction_date.month,
                    period_year=gt.transaction_date.year,
                )

                # 5. Buat Baris Jurnal berdasarkan Tipe Transaksi
                if gt.transaction_type == 'income':
                    # Pemasukan: Debit Kas, Kredit Akun Tujuan
                    JournalEntryLine.objects.create(
                        journal=journal, 
                        account=cash_account, 
                        description=f"Kas - {gt.description[:50]}",
                        debit_amount=gt.amount, 
                        credit_amount=Decimal('0.00')
                    )
                    JournalEntryLine.objects.create(
                        journal=journal, 
                        account=gt.account, 
                        description=f"Pendapatan - {gt.description[:50]}",
                        debit_amount=Decimal('0.00'), 
                        credit_amount=gt.amount
                    )
                
                elif gt.transaction_type == 'expense':
                    # Pengeluaran: Debit Akun Tujuan, Kredit Kas
                    JournalEntryLine.objects.create(
                        journal=journal, 
                        account=gt.account, 
                        description=f"Beban - {gt.description[:50]}",
                        debit_amount=gt.amount, 
                        credit_amount=Decimal('0.00')
                    )
                    JournalEntryLine.objects.create(
                        journal=journal, 
                        account=cash_account, 
                        description=f"Kas - {gt.description[:50]}",
                        debit_amount=Decimal('0.00'), 
                        credit_amount=gt.amount
                    )
                
                elif gt.transaction_type == 'transfer':
                    # Transfer: Debit Akun Tujuan, Kredit Kas
                    JournalEntryLine.objects.create(
                        journal=journal, 
                        account=gt.account, 
                        description=f"Transfer - {gt.description[:50]}",
                        debit_amount=gt.amount, 
                        credit_amount=Decimal('0.00')
                    )
                    JournalEntryLine.objects.create(
                        journal=journal, 
                        account=cash_account, 
                        description=f"Kas - {gt.description[:50]}",
                        debit_amount=Decimal('0.00'), 
                        credit_amount=gt.amount
                    )

                # 6. Hitung Total & Simpan Relasi
                journal._calculate_totals()
                journal.save(update_fields=['total_debit', 'total_credit'])

                gt.journal_entry = journal
                gt.save(update_fields=['journal_entry'])

                messages.success(request, 
                    f'General Transaction {gt.transaction_number} berhasil dibuat dan Jurnal otomatis tercatat!')
                return redirect('finance:general_transaction_list')

            except ValidationError as e:
                # PERBAIKAN: Gunakan str(e) untuk mendapatkan pesan error
                error_msg = str(e)
                messages.error(request, f'Gagal membuat transaksi: {error_msg}')
            except Exception as e:
                messages.error(request, f'Terjadi kesalahan sistem: {str(e)}')
    else:
        form = GeneralTransactionForm()

    context = {
        'form': form,
    }
    return render(request, 'finance/general_transaction_create.html', context)
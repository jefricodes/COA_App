from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import PettyCashEntry
from .forms import PettyCashEntryForm
from journal.models import ChartOfAccount, JournalEntry, JournalEntryLine


def is_finance_approver(user):
    return user.is_authenticated and getattr(user, 'is_approver', False)

finance_approver_required = user_passes_test(is_finance_approver, login_url='/accounts/login/')


@login_required
def petty_cash_list(request):
    # CARA AMAN: getattr tidak akan memicu error RelatedObjectDoesNotExist
    employee_profile = getattr(request.user, 'employee_profile', None)
    
    if not employee_profile:
        messages.warning(request, 'Silakan lengkapi data profil Anda terlebih dahulu.')
        return redirect('accounts:complete_profile')
    
    if not request.user.is_superuser:
        entries = PettyCashEntry.objects.filter(department=employee_profile.department).select_related('created_by', 'department')
    else:
        entries = PettyCashEntry.objects.all().select_related('created_by', 'department')
    
    return render(request, 'petty_cash/list.html', {'entries': entries})


@login_required
def petty_cash_create(request):
    employee_profile = getattr(request.user, 'employee_profile', None)
    
    if not employee_profile:
        messages.warning(request, 'Silakan lengkapi data profil Anda terlebih dahulu sebelum membuat request Petty Cash.')
        return redirect('accounts:complete_profile')

    if request.method == 'POST':
        form = PettyCashEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.department = employee_profile.department
            entry.created_by = request.user
            entry.status = 'submitted'
            entry.save()
            
            messages.success(request, f'Pencatatan {entry.entry_number} berhasil disimpan dan menunggu review!')
            return redirect('petty_cash:list')
    else:
        form = PettyCashEntryForm(initial={'entry_date': timezone.now().date()})
    
    return render(request, 'petty_cash/create.html', {'form': form})


@finance_approver_required
def finance_review_petty_cash(request):
    entries = PettyCashEntry.objects.filter(status='submitted').select_related('department', 'created_by')
    coa_list = ChartOfAccount.objects.filter(is_active=True).order_by('code')
    
    context = {
        'entries': entries,
        'coa_list': coa_list,
    }
    
    return render(request, 'petty_cash/finance_review.html', context)


@finance_approver_required
@transaction.atomic
def finance_approve_petty_cash(request, pk):
    entry = get_object_or_404(PettyCashEntry, pk=pk)
    
    if entry.status != 'submitted':
        messages.error(request, f'{entry.entry_number} sudah diproses sebelumnya.')
        return redirect('petty_cash:finance_review')
    
    if request.method == 'POST':
        account_id = request.POST.get('account')
        if not account_id:
            messages.error(request, 'Anda wajib memilih Akun (COA)!')
            return redirect('petty_cash:finance_review')
        
        selected_account = ChartOfAccount.objects.get(id=account_id)
        
        if selected_account.code.startswith('1-1001'):
            messages.error(request, 'Tidak boleh memilih akun Kas! Pilih akun sumber/tujuan.')
            return redirect('petty_cash:finance_review')
        
        try:
            entry.account_id = account_id
            entry.status = 'approved'
            entry.approved_by = request.user
            entry.approved_at = timezone.now()
            entry.save()
            
            print(f"=== DEBUG: Memulai pembuatan jurnal untuk {entry.entry_number} ===")
            print(f"Entry Type: {entry.entry_type}")
            print(f"Amount: {entry.amount}")
            print(f"Account: {entry.account}")
            
            # Buat Journal Entry otomatis
            _create_journal_for_petty_cash(entry, request.user)
            
            print(f"=== DEBUG: Jurnal berhasil dibuat ===")
            messages.success(request, f'{entry.entry_number} berhasil disetujui!')
            
        except ValidationError as e:
            print(f"=== DEBUG ERROR: {str(e)} ===")
            messages.error(request, f'Gagal memproses: {str(e)}')
            return redirect('petty_cash:finance_review')
        except Exception as e:
            print(f"=== DEBUG ERROR TAK TERDUGA: {str(e)} ===")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Terjadi kesalahan sistem: {str(e)}')
            return redirect('petty_cash:finance_review')
    
    return redirect('petty_cash:finance_review')


@transaction.atomic
def _create_journal_for_petty_cash(entry, user):
    if not entry.account:
        raise ValidationError("Akun COA untuk transaksi ini belum ditentukan.")
        
    today = timezone.now().date()
    s
    cash_account = ChartOfAccount.objects.filter(code='1-1001', is_active=True).first()
    
    if not cash_account:
        raise ValidationError("Akun Kas (1-1001) tidak ditemukan di sistem.")

    print(f"DEBUG: Cash account found: {cash_account}")

    journal = JournalEntry.objects.create(
        journal_number=f"JRN-PC-{today.strftime('%Y%m%d')}-{entry.id:04d}",
        entry_date=today,
        description=f"Petty Cash: {entry.entry_number} - {entry.description[:50]}",
        department=entry.department,
        created_by=user,
        status='approved',
        is_posted=True,
        period_month=today.month,
        period_year=today.year,
    )
    
    print(f"DEBUG: Journal created: {journal.journal_number}")
    
    if entry.entry_type == 'out':
        JournalEntryLine.objects.create(
            journal=journal, account=entry.account,
            description=entry.description,
            debit_amount=entry.amount, credit_amount=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            journal=journal, account=cash_account,
            description="Kas Keluar",
            debit_amount=Decimal('0.00'), credit_amount=entry.amount
        )
    else:
        JournalEntryLine.objects.create(
            journal=journal, account=cash_account,
            description="Kas Masuk",
            debit_amount=entry.amount, credit_amount=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            journal=journal, account=entry.account,
            description=entry.description,
            debit_amount=Decimal('0.00'), credit_amount=entry.amount
        )
    
    print(f"DEBUG: Journal lines created")

    if hasattr(journal, '_calculate_totals'):
        journal._calculate_totals()
        journal.save(update_fields=['total_debit', 'total_credit'])
        print(f"DEBUG: Totals calculated - Debit: {journal.total_debit}, Credit: {journal.total_credit}")
    else:
        print(f"WARNING: Method _calculate_totals() tidak ada di model JournalEntry!")
        from django.db.models import Sum
        totals = journal.lines.aggregate(
            d=Sum('debit_amount'),
            c=Sum('credit_amount')
        )
        journal.total_debit = totals['d'] or Decimal('0.00')
        journal.total_credit = totals['c'] or Decimal('0.00')
        journal.save(update_fields=['total_debit', 'total_credit'])
        print(f"DEBUG: Totals calculated manually - Debit: {journal.total_debit}, Credit: {journal.total_credit}")

@finance_approver_required
@transaction.atomic
def finance_reject_petty_cash(request, pk):

    entry = get_object_or_404(PettyCashEntry, pk=pk)
    
    if entry.status != 'submitted':
        messages.error(request, f'{entry.entry_number} sudah diproses sebelumnya.')
        return redirect('petty_cash:finance_review')
    
    if request.method == 'POST':

        rejection_reason = request.POST.get('rejection_reason', '')
        
        entry.status = 'rejected'
        entry.approved_by = request.user  # Kita pakai field ini untuk mencatat siapa yang reject
        entry.approved_at = timezone.now()
        entry.rejection_reason = rejection_reason
        entry.save()
        
        messages.success(request, f'{entry.entry_number} berhasil DITOLAK.')
        return redirect('petty_cash:finance_review')
    
    return redirect('petty_cash:finance_review')
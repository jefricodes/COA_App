from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from decimal import Decimal

from .models import JournalEntry, JournalEntryLine, ChartOfAccount
from .forms import JournalEntryForm, JournalEntryLineFormSet


def is_accounting_staff(user):
    return user.is_authenticated and getattr(user, 'is_accountant', False)

accounting_staff_required = user_passes_test(is_accounting_staff, login_url='/accounts/login/')


@login_required
@accounting_staff_required
def journal_list(request):

    user = request.user
    
    if user.is_superuser:
        entries = JournalEntry.objects.select_related('created_by', 'department').all()
    else:
        employee_profile = getattr(user, 'employee_profile', None)
        if employee_profile and employee_profile.department:
            entries = JournalEntry.objects.filter(
                department=employee_profile.department
            ).select_related('created_by', 'department')
        else:
            entries = JournalEntry.objects.none()
    
    status_filter = request.GET.get('status')
    if status_filter:
        entries = entries.filter(status=status_filter)
    
    context = {
        'entries': entries,
        'status_filter': status_filter,
    }
    
    return render(request, 'journal/list.html', context)


@login_required
@accounting_staff_required
def journal_detail(request, pk):
    journal = get_object_or_404(
        JournalEntry.objects.select_related('created_by', 'department'),
        pk=pk
    )
    
    user = request.user
    if not user.is_superuser:
        employee_profile = getattr(user, 'employee_profile', None)
        if not employee_profile or journal.department != employee_profile.department:
            raise PermissionDenied("Anda tidak memiliki akses ke jurnal ini.")
    
    lines = journal.lines.select_related('account').all()
    
    context = {
        'journal': journal,
        'lines': lines,
    }
    
    return render(request, 'journal/detail.html', context)


@login_required
@accounting_staff_required
def journal_create(request):

    user = request.user
    employee_profile = getattr(user, 'employee_profile', None)
    default_department = employee_profile.department if employee_profile else None

    if request.method == 'POST':
        
        form = JournalEntryForm(request.POST)
        formset = JournalEntryLineFormSet(request.POST, prefix='lines')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    journal = form.save(commit=False)
                    journal.created_by = user
                    
                    if not employee_profile:
                        journal.department = form.cleaned_data['department']
                    else:
                        journal.department = employee_profile.department
                    
                    today = timezone.now().date()
                    prefix = f"JRN-{today.strftime('%Y%m%d')}"
                    last_journal = JournalEntry.objects.filter(
                        journal_number__startswith=prefix
                    ).order_by('-journal_number').first()
                    
                    if last_journal:
                        last_num = int(last_journal.journal_number.split('-')[-1])
                        new_num = f"{prefix}-{last_num + 1:04d}"
                    else:
                        new_num = f"{prefix}-0001"
                    
                    journal.journal_number = new_num
                    journal.status = 'approved' 
                    journal.is_posted = True 
                    journal.save()

                    lines = formset.save(commit=False)
                    for line in lines:
                        line.journal = journal
                        line.save()
                    
                    for line in formset.deleted_objects:
                        line.delete()
                    

                    journal._calculate_totals()
                    journal.save(update_fields=['total_debit', 'total_credit'])
                    

                    if journal.total_debit != journal.total_credit:
                        raise ValidationError("Total Debit dan Kredit harus seimbang!")
                    
                messages.success(request, f'Jurnal {journal.journal_number} berhasil dibuat!')
                return redirect('journal:list')
                
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Terjadi kesalahan: {str(e)}')
                import traceback
                traceback.print_exc()
        else:

            error_msg = "Ada kesalahan pada form. "
            if not form.is_valid():
                error_msg += "Form utama: " + str(form.errors) + ". "
            if not formset.is_valid():
                error_msg += "Baris jurnal: " + str(formset.non_form_errors())
            messages.error(request, error_msg)
    else:
        initial_data = {
            'entry_date': timezone.now().date(),
            'period_month': timezone.now().month,
            'period_year': timezone.now().year,
        }
        if default_department:
            initial_data['department'] = default_department
            
        form = JournalEntryForm(initial=initial_data)
        formset = JournalEntryLineFormSet(prefix='lines')

    context = {
        'form': form,
        'formset': formset,
    }
    
    return render(request, 'journal/create.html', context)

@login_required
@accounting_staff_required
def journal_update(request, pk):
    journal = get_object_or_404(JournalEntry, pk=pk)
    
    user = request.user
    if not user.is_superuser:
        employee_profile = getattr(user, 'employee_profile', None)
        if not employee_profile or journal.department != employee_profile.department:
            raise PermissionDenied("Anda tidak memiliki izin untuk mengedit jurnal ini.")

    if journal.is_posted:
        messages.error(request, 'Jurnal yang sudah diposting TIDAK BOLEH diubah.')
        return redirect('journal:detail', pk=journal.pk)

    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=journal)
        formset = JournalEntryLineFormSet(request.POST, instance=journal, prefix='lines')
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Update jurnal utama
                    updated_journal = form.save()
                    
                    # Formset.save() otomatis handle:
                    # - Update lines yang ada
                    # - Hapus lines yang di-mark DELETE
                    # - Tambah lines baru
                    lines = formset.save(commit=False)
                    for line in lines:
                        line.journal = updated_journal
                        if not line.account:
                            continue
                        line.save()
                    
                    # Hapus lines yang di-mark delete
                    for line in formset.deleted_objects:
                        line.delete()
                    
                    # Hitung ulang total
                    updated_journal._calculate_totals()
                    updated_journal.save(update_fields=['total_debit', 'total_credit'])
                    
                    # Validasi
                    if updated_journal.total_debit != updated_journal.total_credit:
                        raise ValidationError("Total Debit dan Kredit harus seimbang!")
                    
                    if updated_journal.lines.count() < 2:
                        raise ValidationError("Jurnal harus memiliki minimal 2 baris!")
                    
                messages.success(request, f'Jurnal {updated_journal.journal_number} berhasil diperbarui!')
                return redirect('journal:list')
                
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Terjadi kesalahan: {str(e)}')
        else:
            error_parts = []
            if not form.is_valid():
                for field, errors in form.errors.items():
                    error_parts.append(f"{field}: {', '.join(errors)}")
            if not formset.is_valid():
                for i, f in enumerate(formset.forms):
                    if f.errors:
                        for field, errors in f.errors.items():
                            error_parts.append(f"Baris {i+1} - {field}: {', '.join(errors)}")
                if formset.non_form_errors():
                    error_parts.extend([str(e) for e in formset.non_form_errors()])
            
            messages.error(request, 'Ada kesalahan: ' + ' | '.join(error_parts))
    else:
        form = JournalEntryForm(instance=journal)
        formset = JournalEntryLineFormSet(instance=journal, prefix='lines')

    return render(request, 'journal/update.html', {
        'form': form,
        'formset': formset,
        'journal': journal,
    })

@login_required
@accounting_staff_required
def journal_delete(request, pk):
    journal = get_object_or_404(JournalEntry, pk=pk)
    
    user = request.user
    if not user.is_superuser:
        employee_profile = getattr(user, 'employee_profile', None)
        if not employee_profile or journal.department != employee_profile.department:
            raise PermissionDenied("Anda tidak memiliki izin untuk menghapus jurnal ini.")

    if journal.is_posted:
        messages.error(request, 'Jurnal yang sudah diposting TIDAK BOLEH dihapus.')
        return redirect('journal:detail', pk=journal.pk)

    if request.method == 'POST':
        journal_number = journal.journal_number
        journal.delete()
        messages.success(request, f'Jurnal {journal_number} berhasil dihapus.')
        return redirect('journal:list')

    context = {'journal': journal}
    return render(request, 'journal/confirm_delete.html', context)
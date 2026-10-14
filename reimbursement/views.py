from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied

from .models import ReimbursementRequest
from .forms import ReimbursementForm

@login_required
def reimbursement_list(request):
    employee_profile = getattr(request.user, 'employee_profile', None)
    
    if not employee_profile:
        messages.warning(request, 'Silakan lengkapi data profil Anda terlebih dahulu.')
        return redirect('accounts:complete_profile')

    reimbursements = ReimbursementRequest.objects.filter(employee=employee_profile)
    
    context = {
        'reimbursements': reimbursements,
        'employee': employee_profile,
    }
    return render(request, 'reimbursement/list.html', context)


@login_required
def reimbursement_create(request):
    employee_profile = getattr(request.user, 'employee_profile', None)
    
    if not employee_profile:
        messages.warning(request, 'Silakan lengkapi data profil Anda terlebih dahulu sebelum membuat request Reimbursement.')
        return redirect('accounts:complete_profile')

    if request.method == 'POST':
        form = ReimbursementForm(request.POST, request.FILES)
        if form.is_valid():
            reimbursement = form.save(commit=False)
            reimbursement.employee = employee_profile
            reimbursement.department = employee_profile.department
            reimbursement.status = 'submitted'
            reimbursement.save()
            messages.success(request, f'Request {reimbursement.request_number} berhasil dibuat!')
            return redirect('reimbursement:list')
        else:
            messages.error(request, 'Ada error di form. Silakan periksa kembali.')
    else:
        form = ReimbursementForm()

    context = {'form': form, 'employee': employee_profile}
    return render(request, 'reimbursement/create.html', context)


@login_required
def reimbursement_detail(request, pk):
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)
    employee_profile = getattr(request.user, 'employee_profile', None)

    if reimbursement.employee != employee_profile and not request.user.is_approver:
        raise PermissionDenied('Anda tidak punya akses ke request ini.')

    context = {'reimbursement': reimbursement}
    return render(request, 'reimbursement/detail.html', context)


@login_required
def reimbursement_edit(request, pk):
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)
    employee_profile = getattr(request.user, 'employee_profile', None)

    if reimbursement.employee != employee_profile:
        raise PermissionDenied('Anda tidak berhak mengedit request ini.')

    if reimbursement.status != 'submitted':
        messages.warning(request, 'Request ini sudah diproses dan tidak bisa diedit.')
        return redirect('reimbursement:detail', pk=reimbursement.pk)

    if request.method == 'POST':
        form = ReimbursementForm(request.POST, request.FILES, instance=reimbursement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Request berhasil diperbarui!')
            return redirect('reimbursement:detail', pk=reimbursement.pk)
    else:
        form = ReimbursementForm(instance=reimbursement)

    context = {'form': form, 'reimbursement': reimbursement}
    return render(request, 'reimbursement/edit.html', context)
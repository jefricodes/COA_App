from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal

from reimbursement.models import ReimbursementRequest
from petty_cash.models import PettyCashEntry
from journal.models import JournalEntryLine, ChartOfAccount

@login_required
def dashboard_index(request):
    today = timezone.now().date()
    user = request.user
    context = {}

    # ==========================================
    # 1. LOGIKA UNTUK MANAGER / APPROVER / FINANCE
    # ==========================================
    if getattr(user, 'is_approver', False) or getattr(user, 'is_accountant', False):
        # Antrian approval
        context['pending_reimbursements'] = ReimbursementRequest.objects.filter(status='submitted').count()
        context['pending_petty_cash'] = PettyCashEntry.objects.filter(status='submitted').count()
        
        # Filter Jurnal yang sudah posted
        posted_lines = JournalEntryLine.objects.filter(
            journal__status='approved',
            journal__is_posted=True,
            journal__period_month=today.month,
            journal__period_year=today.year
        )

        # Hitung Pendapatan & Beban
        revenue = posted_lines.filter(account__account_type='revenue').aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')
        expense = posted_lines.filter(account__account_type='expense').aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')
        
        context['total_revenue'] = revenue
        context['total_expense'] = expense
        context['net_profit'] = revenue - expense

        # Hitung Total Saldo Kas (Aset Lancar - Kode 1-xxxx)
        all_posted_lines = JournalEntryLine.objects.filter(
            journal__status='approved',
            journal__is_posted=True,
            account__account_type='asset'
        )

        total_asset_debit = all_posted_lines.aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')
        total_asset_credit = all_posted_lines.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')
        
        context['total_cash_balance'] = total_asset_debit - total_asset_credit

    # ==========================================
    # 2. LOGIKA UNTUK STAFF BIASA
    # ==========================================
    else:
        employee_profile = getattr(user, 'employee_profile', None)
        if employee_profile:
            context['my_pending_reimbursements'] = ReimbursementRequest.objects.filter(employee=employee_profile, status='submitted').count()
            context['my_approved_reimbursements'] = ReimbursementRequest.objects.filter(employee=employee_profile, status='approved').count()
        else:
            context['my_pending_reimbursements'] = 0
            context['my_approved_reimbursements'] = 0

    return render(request, 'dashboard/index.html', context)
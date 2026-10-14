from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from decimal import Decimal
import datetime, calendar
from openpyxl import Workbook
from openpyxl.styles import Font
from django.http import HttpResponse

from journal.models import JournalEntryLine, ChartOfAccount


def is_accounting_staff(user):
    return user.is_authenticated and getattr(user, 'is_accountant', False)

accounting_required = user_passes_test(is_accounting_staff, login_url='/accounts/login/')

MONTH_NAMES = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

@login_required
@accounting_required
def profit_loss_report(request):
    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    current_month_name = MONTH_NAMES.get(month, '')
    revenue_accounts = JournalEntryLine.objects.filter(
        journal__status='approved',
        journal__is_posted=True,
        journal__period_month=month,
        journal__period_year=year,
        account__account_type='revenue'
    ).values('account__code', 'account__name').annotate(
        total=Sum('credit_amount')
    ).order_by('account__code')
    
    total_revenue = sum(acc['total'] or Decimal('0') for acc in revenue_accounts)
    
    expense_accounts = JournalEntryLine.objects.filter(
        journal__status='approved',
        journal__is_posted=True,
        journal__period_month=month,
        journal__period_year=year,
        account__account_type='expense'
    ).values('account__code', 'account__name').annotate(
        total=Sum('debit_amount')
    ).order_by('account__code')
    
    total_expense = sum(acc['total'] or Decimal('0') for acc in expense_accounts)
    net_profit = total_revenue - total_expense
    
    context = {
        'month': month, 'year': year,
        'revenue_accounts': revenue_accounts,
        'expense_accounts': expense_accounts,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'month_names': MONTH_NAMES,
        'current_month_name': current_month_name,
    }
    
    return render(request, 'reports/profit_loss.html', context)


@login_required
@accounting_required
def trial_balance(request):
    """Laporan Neraca Saldo (Trial Balance) - Dioptimalkan."""
    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    current_month_name = MONTH_NAMES.get(month, '')
    
    journal_lines = JournalEntryLine.objects.filter(
        journal__status='approved',
        journal__is_posted=True,
        journal__period_month=month,
        journal__period_year=year,
    ).values(
        'account__code', 'account__name', 'account__account_type'
    ).annotate(
        raw_debit=Sum('debit_amount'),
        raw_credit=Sum('credit_amount')
    ).order_by('account__code')

    trial_data = []
    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')
    
    for line in journal_lines:
        total_debit += (line['raw_debit'] or Decimal('0.00'))
        total_credit += (line['raw_credit'] or Decimal('0.00'))
        
        if line['account__account_type'] in ['asset', 'expense']:
            balance = (line['raw_debit'] or Decimal('0.00')) - (line['raw_credit'] or Decimal('0.00'))
        else:
            balance = (line['raw_credit'] or Decimal('0.00')) - (line['raw_debit'] or Decimal('0.00'))
            
        trial_data.append({
            'code': line['account__code'],
            'name': line['account__name'],
            'type': line['account__account_type'],
            'debit': line['raw_debit'] or Decimal('0.00'),
            'credit': line['raw_credit'] or Decimal('0.00'),
            'balance': abs(balance),
        })
            
    is_balanced = total_debit == total_credit
    
    context = {
        'trial_data': trial_data,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'is_balanced': is_balanced,
        'month': month, 'year': year,
        'month_names': MONTH_NAMES,
        'current_month_name': current_month_name,
    }
    
    return render(request, 'reports/trial_balance.html', context)


@login_required
@accounting_required
def balance_sheet(request):
    """Report Neraca (Balance Sheet)"""
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    last_day = calendar.monthrange(year, month)[1]
    end_date = datetime.date(year, month, last_day)

    # Ambil semua jurnal yang sudah posted sampai tanggal tersebut
    journal_lines = JournalEntryLine.objects.filter(
        journal__status='approved',
        journal__is_posted=True,
        journal__entry_date__lte=end_date
    ).values(
        'account__code', 'account__name', 'account__account_type'
    ).annotate(
        raw_debit=Sum('debit_amount'),
        raw_credit=Sum('credit_amount')
    ).order_by('account__code')

    assets = []
    liabilities = []
    equities = []
    
    total_assets = Decimal('0.00')
    total_liabilities = Decimal('0.00')
    total_equity = Decimal('0.00')

    for line in journal_lines:
        acc_type = line['account__account_type']
        debit = line['raw_debit'] or Decimal('0.00')
        credit = line['raw_credit'] or Decimal('0.00')
        
        # Hitung Saldo Akhir
        if acc_type in ['asset', 'expense']:
            balance = debit - credit
        else:
            balance = credit - debit
            
        data_row = {
            'code': line['account__code'],
            'name': line['account__name'],
            'balance': balance
        }
        
        if acc_type == 'asset':
            assets.append(data_row)
            total_assets += balance
        elif acc_type == 'liability':
            liabilities.append(data_row)
            total_liabilities += balance
        elif acc_type == 'equity':
            equities.append(data_row)
            total_equity += balance

    revenue_ytd = JournalEntryLine.objects.filter(
        journal__status='approved', journal__is_posted=True, journal__entry_date__lte=end_date, account__account_type='revenue'
    ).aggregate(total=Sum('credit_amount'))['total'] or Decimal('0.00')
    
    expense_ytd = JournalEntryLine.objects.filter(
        journal__status='approved', journal__is_posted=True, journal__entry_date__lte=end_date, account__account_type='expense'
    ).aggregate(total=Sum('debit_amount'))['total'] or Decimal('0.00')
    
    net_profit_ytd = revenue_ytd - expense_ytd
    total_equity_with_profit = total_equity + net_profit_ytd

    is_balanced = total_assets == (total_liabilities + total_equity_with_profit)

    # ==========================================
    # EXPORT EXCEL
    # ==========================================
    if request.GET.get('export') == 'excel':
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from django.http import HttpResponse
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Neraca"
        
        header_font = Font(bold=True, size=14, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        subheader_font = Font(bold=True, size=11, color="FFFFFF")
        subheader_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
        total_font = Font(bold=True, size=11)
        total_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        ws.merge_cells('A1:B1')
        ws['A1'] = f"LAPORAN NERACA (BALANCE SHEET)"
        ws['A1'].font = header_font
        ws['A1'].fill = header_fill
        ws['A1'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells('A2:B2')
        ws['A2'] = f"Periode: {MONTH_NAMES.get(month, '')} {year}"
        ws['A2'].font = Font(italic=True, size=11)
        ws['A2'].alignment = Alignment(horizontal='center')
        
        ws['A4'] = "ASET"
        ws['A4'].font = subheader_font
        ws['A4'].fill = subheader_fill
        ws.merge_cells('A4:B4')
        
        row = 5
        for item in assets:
            ws.cell(row=row, column=1, value=f"{item['code']} - {item['name']}")
            ws.cell(row=row, column=2, value=float(item['balance']))
            ws.cell(row=row, column=2).number_format = '#,##0'
            row += 1
        
        # Total Aset
        ws.cell(row=row, column=1, value="TOTAL ASET")
        ws.cell(row=row, column=2, value=float(total_assets))
        ws.cell(row=row, column=1).font = total_font
        ws.cell(row=row, column=2).font = total_font
        ws.cell(row=row, column=2).number_format = '#,##0'
        ws.cell(row=row, column=1).fill = total_fill
        ws.cell(row=row, column=2).fill = total_fill
        
        ws['D4'] = "LIABILITAS"
        ws['D4'].font = subheader_font
        ws['D4'].fill = subheader_fill
        ws.merge_cells('D4:E4')
        
        row = 5
        for item in liabilities:
            ws.cell(row=row, column=4, value=f"{item['code']} - {item['name']}")
            ws.cell(row=row, column=5, value=float(item['balance']))
            ws.cell(row=row, column=5).number_format = '#,##0'
            row += 1
        
        ws.cell(row=row, column=4, value="Total Liabilitas")
        ws.cell(row=row, column=5, value=float(total_liabilities))
        ws.cell(row=row, column=4).font = total_font
        ws.cell(row=row, column=5).font = total_font
        ws.cell(row=row, column=5).number_format = '#,##0'
        ws.cell(row=row, column=4).fill = total_fill
        ws.cell(row=row, column=5).fill = total_fill
        
        # Ekuitas
        row += 2
        ws.cell(row=row, column=4, value="EKUITAS")
        ws.cell(row=row, column=4).font = subheader_font
        ws.cell(row=row, column=4).fill = subheader_fill
        ws.merge_cells(f'D{row}:E{row}')
        row += 1
        
        for item in equities:
            ws.cell(row=row, column=4, value=f"{item['code']} - {item['name']}")
            ws.cell(row=row, column=5, value=float(item['balance']))
            ws.cell(row=row, column=5).number_format = '#,##0'
            row += 1
        
        ws.cell(row=row, column=4, value="Laba/Rugi Berjalan (YTD)")
        ws.cell(row=row, column=5, value=float(net_profit_ytd))
        ws.cell(row=row, column=5).number_format = '#,##0'
        row += 1
        
        ws.cell(row=row, column=4, value="Total Ekuitas")
        ws.cell(row=row, column=5, value=float(total_equity_with_profit))
        ws.cell(row=row, column=4).font = total_font
        ws.cell(row=row, column=5).font = total_font
        ws.cell(row=row, column=5).number_format = '#,##0'
        ws.cell(row=row, column=4).fill = total_fill
        ws.cell(row=row, column=5).fill = total_fill
        
        # Total Liabilitas + Ekuitas
        row += 1
        ws.cell(row=row, column=4, value="TOTAL LIABILITAS & EKUITAS")
        ws.cell(row=row, column=5, value=float(total_liabilities + total_equity_with_profit))
        ws.cell(row=row, column=4).font = Font(bold=True, size=12)
        ws.cell(row=row, column=5).font = Font(bold=True, size=12)
        ws.cell(row=row, column=5).number_format = '#,##0'
        
        ws.column_dimensions['A'].width = 35
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['D'].width = 35
        ws.column_dimensions['E'].width = 20
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="Neraca_{month}_{year}.xlsx"'
        wb.save(response)
        return response

    # ==========================================
    # RENDER HTML if not Export
    # ==========================================
    context = {
        'assets': assets, 'total_assets': total_assets,
        'liabilities': liabilities, 'total_liabilities': total_liabilities,
        'equities': equities, 'total_equity': total_equity,
        'net_profit_ytd': net_profit_ytd,
        'total_equity_with_profit': total_equity_with_profit,
        'is_balanced': is_balanced,
        'month': month, 'year': year,
        'month_names': MONTH_NAMES,
    }
    return render(request, 'reports/balance_sheet.html', context)
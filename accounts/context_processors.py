from reimbursement.models import ReimbursementRequest
from petty_cash.models import PettyCashEntry

def notification_context(request):
    context = {}
    if request.user.is_authenticated and getattr(request.user, 'is_approver', False):
        context['pending_reimbursement_count'] = ReimbursementRequest.objects.filter(status='submitted').count()
        context['pending_petty_cash_count'] = PettyCashEntry.objects.filter(status='submitted').count()
    else:
        context['pending_reimbursement_count'] = 0
        context['pending_petty_cash_count'] = 0
    return context
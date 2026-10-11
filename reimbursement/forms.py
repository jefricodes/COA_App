from django import forms
from .models import ReimbursementRequest
from decimal import Decimal

class ReimbursementForm(forms.ModelForm):
    class Meta:
        model = ReimbursementRequest
        fields = ['description', 'amount', 'receipt_file']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '0.01'}),
            'receipt_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= Decimal('0'):
            raise forms.ValidationError('Jumlah harus lebih dari 0!')
        return amount
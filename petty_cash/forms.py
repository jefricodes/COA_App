from django import forms
from .models import PettyCashEntry
from decimal import Decimal

class PettyCashEntryForm(forms.ModelForm):
    class Meta:
        model = PettyCashEntry
        # Field department, account, dan status TIDAK ada di sini (diatur di views)
        fields = ['entry_type', 'entry_date', 'description', 'amount', 'receipt_file']
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'entry_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '0.01'}),
            'receipt_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= Decimal('0'):
            raise forms.ValidationError('Jumlah harus lebih dari 0!')
        return amount
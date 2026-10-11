from django import forms
from .models import GeneralTransaction

class GeneralTransactionForm(forms.ModelForm):
    class Meta:
        model = GeneralTransaction
        fields = ['transaction_date', 'department', 'description', 'transaction_type', 'amount', 'account']
        widgets = {
            'transaction_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Nominal harus lebih besar dari 0!")
        return amount
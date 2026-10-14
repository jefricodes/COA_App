from django import forms
from django.forms import inlineformset_factory
from .models import JournalEntry, JournalEntryLine


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['entry_date', 'description', 'department', 'period_month', 'period_year']
        widgets = {
            'entry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'period_month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'period_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2100}),
        }


class JournalEntryLineForm(forms.ModelForm):
    class Meta:
        model = JournalEntryLine
        fields = ['account', 'description', 'debit_amount', 'credit_amount']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'debit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'credit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].required = False
        self.fields['description'].required = False
        self.fields['debit_amount'].required = False
        self.fields['credit_amount'].required = False

    def clean(self):
        cleaned_data = super().clean()
        delete_key = f'{self.prefix}-DELETE' if self.prefix else 'DELETE'
        if self.data.get(delete_key) in ['on', 'True', 'true', '1']:
            return cleaned_data

        account = cleaned_data.get('account')
        description = cleaned_data.get('description')
        debit = cleaned_data.get('debit_amount')
        credit = cleaned_data.get('credit_amount')

        try:
            debit_val = float(debit) if debit else 0
        except (ValueError, TypeError):
            debit_val = 0

        try:
            credit_val = float(credit) if credit else 0
        except (ValueError, TypeError):
            credit_val = 0

        if not account and debit_val == 0 and credit_val == 0:
            return cleaned_data

        if not account:
            self.add_error('account', 'Akun wajib diisi.')
        if not description:
            self.add_error('description', 'Deskripsi wajib diisi.')
        if debit_val > 0 and credit_val > 0:
            raise forms.ValidationError("Tidak boleh mengisi Debit dan Kredit sekaligus!")
        if debit_val == 0 and credit_val == 0:
            raise forms.ValidationError("Salah satu nominal (Debit atau Kredit) harus diisi!")

        return cleaned_data


JournalEntryLineFormSet = inlineformset_factory(
    JournalEntry,
    JournalEntryLine,
    form=JournalEntryLineForm,
    extra=2,
    can_delete=True,
    min_num=2,
    validate_min=True,
)
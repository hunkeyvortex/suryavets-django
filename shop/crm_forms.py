from django import forms
from django.contrib.auth.forms import AuthenticationForm


class StaffLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff or not user.has_perm('shop.access_crm'):
            raise forms.ValidationError('This account does not have CRM access.', code='no_crm_access')


class StockAdjustmentForm(forms.Form):
    delta = forms.IntegerField(label='Quantity change', min_value=-1000000, max_value=1000000,
        help_text='Use a positive number for stock received, a negative number for stock removed.')
    reason = forms.CharField(min_length=3, max_length=500, widget=forms.Textarea(attrs={'rows': 3}))
    token = forms.CharField(widget=forms.HiddenInput)

    def clean_delta(self):
        value = self.cleaned_data['delta']
        if not value:
            raise forms.ValidationError('The quantity change cannot be zero.')
        return value


class StatusForm(forms.Form):
    expected = forms.CharField(widget=forms.HiddenInput)
    status = forms.ChoiceField(label='Next status', choices=[])
    reason = forms.CharField(min_length=3, max_length=500, widget=forms.Textarea(attrs={'rows': 2}))


class NoteForm(forms.Form):
    text = forms.CharField(label='Internal note', min_length=3, max_length=2000,
                          widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Staff-only note. Never enter card details, passwords, or payment secrets.'}))

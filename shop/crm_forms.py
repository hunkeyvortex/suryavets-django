from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Coupon


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


class CouponForm(forms.ModelForm):
    version = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Coupon
        fields = ['code', 'name', 'kind', 'value', 'minimum_subtotal', 'maximum_discount', 'starts_at', 'ends_at', 'max_uses', 'is_active']
        labels = {'value': 'Discount value (% or ₹)', 'minimum_subtotal': 'Minimum product subtotal (₹)',
                  'maximum_discount': 'Maximum discount (₹, optional)', 'max_uses': 'Total usage limit (optional)',
                  'is_active': 'Active at checkout'}
        widgets = {name: forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M') for name in ['starts_at', 'ends_at']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['code'].disabled = True
            self.fields['version'].initial = self.instance.updated_at.isoformat()
        self.fields['max_uses'].help_text = 'Blank means unlimited. Placed orders consume uses, including later cancellations.'
        self.fields['maximum_discount'].help_text = 'Optional cap on savings. Discounts apply to products, not shipping.'

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()

    def clean(self):
        data = super().clean()
        if self.instance.pk and data.get('version') != self.instance.updated_at.isoformat():
            raise forms.ValidationError('Another staff member edited this coupon. Reload before saving your changes.')
        return data

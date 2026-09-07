from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import CustomerPet, CustomerProfile, SupportRequest
from .forms import AddressForm


class SavedAddressForm(AddressForm):
    def clean_postal_code(self):
        value = self.cleaned_data['postal_code'].strip()
        if len(value) != 6 or not value.isdigit() or value.startswith('0'):
            raise forms.ValidationError('Enter a valid six-digit Indian PIN code.')
        return value

    def clean_country(self):
        if self.cleaned_data['country'].strip().lower() != 'india':
            raise forms.ValidationError('Delivery currently supports India only.')
        return 'India'


class PetForm(forms.ModelForm):
    class Meta:
        model = CustomerPet
        fields = ['name', 'pet_type', 'breed', 'date_of_birth', 'gender', 'weight']
        widgets = {'date_of_birth': forms.DateInput(attrs={'type': 'date'})}
        labels = {'weight': 'Weight (kg)', 'date_of_birth': 'Date of birth (optional)'}

    def clean_date_of_birth(self):
        value = self.cleaned_data['date_of_birth']
        if value and value > timezone.localdate():
            raise forms.ValidationError('Date of birth cannot be in the future.')
        return value


class ProfileForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(disabled=True, help_text='Contact support to request a verified email change.')

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = CustomerProfile.objects.filter(user=self.instance).first()
        self.fields['phone'].initial = profile.phone if profile else ''

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            CustomerProfile.objects.update_or_create(user=user, defaults={'phone': self.cleaned_data['phone']})
        return user


class SupportForm(forms.ModelForm):
    class Meta:
        model = SupportRequest
        fields = ['order', 'category', 'subject', 'message']
        widgets = {'message': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order'].queryset = user.orders.all()


class SupportReplyForm(forms.ModelForm):
    class Meta:
        model = SupportRequest
        fields = ['response', 'state']
        widgets = {'response': forms.Textarea(attrs={'rows': 4})}


class ReviewForm(forms.Form):
    kind = forms.ChoiceField(choices=[('return', 'Return review'), ('payment', 'Payment record')])
    expected = forms.CharField(required=False, widget=forms.HiddenInput)
    status = forms.CharField(max_length=24)
    note = forms.CharField(min_length=3, max_length=1000, widget=forms.Textarea)
    reference = forms.CharField(max_length=150, required=False)

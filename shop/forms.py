from django import forms
from hashlib import sha256
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import CustomerAddress


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label='Email address', max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'you@gmail.com', 'autocapitalize': 'none'}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(
        attrs={'autocomplete': 'current-password', 'placeholder': 'Your password'}))

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email, password = cleaned.get('email'), cleaned.get('password')
        if email and password:
            users = list(get_user_model().objects.filter(email__iexact=email)[:2])
            # Never pick an arbitrary account if historical emails are duplicated.
            if len(users) == 1:
                self.user_cache = authenticate(self.request, username=users[0].get_username(), password=password)
            else:
                # Match the password-hashing work for nonexistent/ambiguous accounts.
                get_user_model()().set_password(password)
            if self.user_cache is None:
                raise forms.ValidationError('The email address or password is incorrect.', code='invalid_login')
        return cleaned

    def get_user(self):
        return self.user_cache


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label='Email address', max_length=254)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'autocomplete': 'email', 'placeholder': 'you@gmail.com', 'autocapitalize': 'none'})
        self.fields['password1'].widget.attrs.update({'autocomplete': 'new-password', 'placeholder': 'Create a strong password'})
        self.fields['password2'].widget.attrs.update({'autocomplete': 'new-password', 'placeholder': 'Enter your password again'})

    class Meta:
        model = get_user_model()
        fields = ('email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already uses this email address.')
        # Django's existing User model still requires a unique username internally.
        # A deterministic opaque ID also makes simultaneous same-email signups
        # collide on the database's existing unique constraint, not create twins.
        self.instance.username = 'customer_' + sha256(email.encode('utf-8')).hexdigest()
        return email


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = (('cash_on_delivery', 'Cash on Delivery'), ('manual', 'Pay after order confirmation'))
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    shipping_name = forms.CharField(max_length=150)
    shipping_address_line_1 = forms.CharField(max_length=255)
    shipping_address_line_2 = forms.CharField(max_length=255, required=False)
    shipping_city = forms.CharField(max_length=100)
    shipping_state = forms.CharField(max_length=100)
    shipping_postal_code = forms.CharField(max_length=20)
    billing_same_as_shipping = forms.BooleanField(required=False, initial=True)
    billing_name = forms.CharField(max_length=150, required=False)
    billing_address_line_1 = forms.CharField(max_length=255, required=False)
    billing_address_line_2 = forms.CharField(max_length=255, required=False)
    billing_city = forms.CharField(max_length=100, required=False)
    billing_state = forms.CharField(max_length=100, required=False)
    billing_postal_code = forms.CharField(max_length=20, required=False)
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES, initial='cash_on_delivery')
    notes = forms.CharField(widget=forms.Textarea, required=False)
    save_address = forms.BooleanField(required=False)
    terms = forms.BooleanField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('billing_same_as_shipping'):
            for field in ('billing_name', 'billing_address_line_1', 'billing_city', 'billing_state', 'billing_postal_code'):
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required for a separate billing address.')
        return cleaned_data


class AddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = ('label', 'full_name', 'phone', 'address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country', 'is_default_shipping')

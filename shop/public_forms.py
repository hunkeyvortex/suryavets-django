from django import forms
from .models import ContactSubmission

class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    class Meta:
        model = ContactSubmission
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {'message': forms.Textarea(attrs={'rows': 6})}

class NewsletterForm(forms.Form):
    email = forms.EmailField(max_length=254)
    consent = forms.BooleanField(required=True)

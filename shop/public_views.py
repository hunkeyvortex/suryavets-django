import logging
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import PasswordResetView
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from .models import NewsletterSubscription
from .public_forms import ContactForm, NewsletterForm
from .services.throttling import allowed

@require_http_methods(['GET', 'POST'])
def contact(request):
    form = ContactForm(request.POST if request.method == 'POST' else None)
    status = 200
    if request.method == 'POST':
        if not allowed(request, 'contact'):
            form.add_error(None, 'Too many submissions. Please try again later.')
            status = 429
        elif form.is_valid():
            if not form.cleaned_data['website']:
                form.save()
            messages.success(request, 'Your message has been received by SuryaVets.')
            return redirect('shop:contact')
        else:
            status = 400
    return render(request, 'public/contact.html', {'form': form}, status=status)

@require_POST
def newsletter(request):
    if not allowed(request, 'newsletter'):
        return JsonResponse({'success': False, 'message': 'Please try again later.'}, status=429)
    form = NewsletterForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'success': False, 'message': 'Enter a valid email and agree to receive updates.'}, status=400)
    NewsletterSubscription.objects.get_or_create(email=form.cleaned_data['email'].lower(), defaults={'consent_at': timezone.now()})
    return JsonResponse({'success': True, 'message': 'Your request is recorded. Existing opt-outs are respected.'})

class SafePasswordResetView(PasswordResetView):
    template_name = 'registration/reset_form.html'
    email_template_name = 'registration/reset_email.txt'
    html_email_template_name = 'registration/reset_email.html'
    subject_template_name = 'registration/reset_subject.txt'
    success_url = reverse_lazy('shop:password_reset_done')
    def form_valid(self, form):
        ip_ok = allowed(self.request, 'password-reset', limit=5)
        email_ok = allowed(self.request, 'password-reset-email', limit=3, identity=form.cleaned_data['email'].strip().lower())
        origin = urlsplit(settings.PUBLIC_SITE_URL)
        if ip_ok and email_ok and settings.PASSWORD_RESET_EMAIL_ENABLED and origin.netloc:
            try:
                form.save(domain_override=origin.netloc, use_https=origin.scheme == 'https', email_template_name=self.email_template_name,
                    html_email_template_name=self.html_email_template_name, subject_template_name=self.subject_template_name, from_email=settings.DEFAULT_FROM_EMAIL)
            except Exception:
                logging.getLogger(__name__).warning('Password reset delivery unavailable')
        return redirect(self.success_url)

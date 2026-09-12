"""Explicit operator-only transport test, never creates or modifies orders."""
from email.utils import formataddr, parseaddr
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from shop.mail_backends import DeliveryError


class Command(BaseCommand):
    help = 'Send a clearly labelled test to your own explicit address using the configured email backend.'

    def add_arguments(self, parser):
        parser.add_argument('--to', required=True, help='Your own test inbox, not a customer list.')
        parser.add_argument('--allow-live', action='store_true', help='Explicit consent for a real send when not using sandbox/local output.')

    def handle(self, *args, **options):
        if not settings.ORDER_EMAIL_ENABLED:
            raise CommandError('ORDER_EMAIL_ENABLED must be enabled explicitly for this test.')
        try:
            validate_email(options['to'])
        except ValidationError:
            raise CommandError('Supply a valid test recipient.') from None
        backend = settings.MAILERS['default']['BACKEND']
        sandbox = backend == 'shop.mail_backends.BrevoEmailBackend' and settings.BREVO_SANDBOX
        local = backend in ('django.core.mail.backends.console.EmailBackend', 'django.core.mail.backends.filebased.EmailBackend',
            'django.core.mail.backends.locmem.EmailBackend', 'django.core.mail.backends.dummy.EmailBackend')
        if not local and not sandbox and not options['allow_live']:
            raise CommandError('Real delivery requires --allow-live and an inbox you control.')
        name, address = parseaddr(settings.DEFAULT_FROM_EMAIL)
        message = EmailMultiAlternatives('[TEST] SuryaVets transactional email',
            'SuryaVets email connection test. This is not an order confirmation. No order or payment was created.',
            formataddr((name or settings.DEFAULT_FROM_NAME, address)), [options['to']])
        message.attach_alternative('<!doctype html><html><body style="font-family:Arial,sans-serif;background:#fff;color:#243e32">'
            '<h1 style="color:#00884a">SuryaVets</h1><h2>Email connection test</h2>'
            '<p>This is a test, not an order confirmation. No order or payment was created.</p></body></html>', 'text/html')
        try:
            if message.send() != 1:
                raise DeliveryError('acceptance_unconfirmed')
        except DeliveryError as error:
            raise CommandError(f'Test not confirmed: {error}. Check configuration/provider logs before any retry.') from None
        except Exception:
            raise CommandError('Test delivery outcome unknown. Check provider logs before retrying.') from None
        result = 'Sandbox accepted; NO email delivered and no Brevo email log expected.' if sandbox else 'Local backend only; NO real delivery.' if local else 'Provider accepted; check your inbox/spam and Brevo transactional logs.'
        self.stdout.write(result)
        if getattr(message, 'provider_message_id', ''):
            self.stdout.write(f'Provider message ID: {message.provider_message_id}')

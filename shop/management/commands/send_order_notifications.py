"""Explicit outbox worker. Disabled by default; no page-save email side effects."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from shop.services.notifications import deliver_pending


class Command(BaseCommand):
    help = 'Deliver pending email order events only when ORDER_EMAIL_ENABLED is true.'

    def handle(self, *args, **options):
        if not getattr(settings, 'ORDER_EMAIL_ENABLED', False):
            raise CommandError('Order email delivery is disabled. Configure a verified email backend before enabling it.')
        deliver_pending()
        self.stdout.write('Pending email events processed. Failed/sending rows require manual reconciliation; never blindly resend.')

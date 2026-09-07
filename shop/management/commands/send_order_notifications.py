"""Explicit outbox worker. Disabled by default; no page-save email side effects."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone
from shop.models import OrderNotification


class Command(BaseCommand):
    help = 'Deliver pending email order events only when ORDER_EMAIL_ENABLED is true.'

    def handle(self, *args, **options):
        if not getattr(settings, 'ORDER_EMAIL_ENABLED', False):
            raise CommandError('Order email delivery is disabled. Configure a verified email backend before enabling it.')
        for pk in OrderNotification.objects.filter(state='pending', channel='email').values_list('pk', flat=True).iterator():
            if not OrderNotification.objects.filter(pk=pk, state='pending').update(state='sending', attempts=F('attempts') + 1):
                continue
            item = OrderNotification.objects.select_related('event__order').get(pk=pk)
            event, order = item.event, item.event.order
            # Explicit customer fields only. Never serialize internal notes or payment references.
            body = f'Order {order.order_number}\n{event.label}\n{event.customer_note}\n\nSign in to your Surya Vets account to view your order.'
            try:
                sent = send_mail(f'Surya Vets — {order.order_number}: {event.label}', body, settings.DEFAULT_FROM_EMAIL, [order.email])
                if sent != 1: raise RuntimeError('Email backend did not confirm acceptance')
            except Exception:
                OrderNotification.objects.filter(pk=pk).update(state='failed', error='Delivery not confirmed. Review with the email provider before retrying.')
            else:
                OrderNotification.objects.filter(pk=pk).update(state='sent', sent_at=timezone.now(), error='')
        self.stdout.write('Pending email events processed. Failed/sending rows require manual reconciliation; never blindly resend.')

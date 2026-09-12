"""Event outbox; claim once, send after commit, retain uncertain deliveries for review."""
import logging
from urllib.parse import urlsplit
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from shop.models import OrderNotification

logger = logging.getLogger(__name__)


def absolute_link(path):
    origin = settings.PUBLIC_SITE_URL
    parsed = urlsplit(origin)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return ''
    if parsed.scheme != 'https' and not (settings.DEBUG and parsed.hostname in ('localhost', '127.0.0.1')):
        return ''
    return origin + path


def deliver_event_safely(event_id):
    if not settings.ORDER_EMAIL_ENABLED or not settings.ORDER_EMAIL_AUTO_SEND:
        return
    try:
        deliver_pending(event_id)
    except Exception:
        # No SMTP responses, recipient addresses or secrets in logs.
        logger.warning('Order outbox processing deferred for event %s', event_id)


def deliver_pending(event_id=None):
    if not settings.ORDER_EMAIL_ENABLED:
        return
    rows = OrderNotification.objects.filter(state='pending', channel='email')
    if event_id is not None:
        rows = rows.filter(event_id=event_id)
    for pk in list(rows.values_list('pk', flat=True)):
        item = OrderNotification.objects.select_related('event__order').get(pk=pk)
        event, order = item.event, item.event.order
        if not event.customer_visible:
            continue
        if order.payment_method == 'online' and order.payment_status not in ('paid', 'refund_pending', 'partially_refunded', 'refunded'):
            continue
        recipient = item.recipient or (settings.ORDER_NOTIFICATION_EMAIL if item.audience == 'admin' else order.email)
        try:
            validate_email(recipient)
        except Exception:
            continue  # Missing admin configuration remains pending, never silently discarded.
        if not OrderNotification.objects.filter(pk=pk, state='pending').update(state='sending', recipient=recipient, attempts=F('attempts') + 1):
            continue
        try:
            admin = item.audience == 'admin'
            new = event.kind == 'order' and event.status == 'pending'
            title = 'New order received' if admin else 'Order confirmation' if new else event.label
            path = reverse('crm:order_detail', args=[order.pk]) if admin else reverse('shop:order_number', args=[order.order_number]) if order.user_id else ''
            context = {'order': order, 'items': order.items.all(), 'title': title, 'admin_email': admin,
                'new_order': new, 'customer_note': event.customer_note, 'order_url': absolute_link(path) if path else '',
                'link_label': 'View order in CRM' if admin else 'View your order'}
            subject = f'NEW SURYAVETS ORDER – #{order.order_number} – INR {order.total}' if admin else f'SuryaVets {title} – #{order.order_number}'
            message = EmailMultiAlternatives(subject=subject,
                body=render_to_string('emails/order.txt', context), from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient], headers={'Message-ID': f'<suryavets-notification-{pk}@notifications.suryavets.invalid>'})
            message.attach_alternative(render_to_string('emails/order.html', context), 'text/html')
            if message.send() != 1:
                raise RuntimeError('Delivery acceptance unconfirmed')
        except Exception:
            OrderNotification.objects.filter(pk=pk).update(state='failed', error='Delivery not confirmed. Reconcile with the provider before retrying.')
            logger.warning('Notification %s delivery unconfirmed; provider reconciliation required', pk)
        else:
            OrderNotification.objects.filter(pk=pk).update(state='sent', sent_at=timezone.now(), error='')

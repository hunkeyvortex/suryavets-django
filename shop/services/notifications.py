"""Event outbox; claim once, send after commit, retain uncertain deliveries for review."""
import logging
import uuid
from datetime import timedelta
from email.utils import formataddr, parseaddr
from urllib.parse import urlsplit
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db.models import F, Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from shop.models import OrderNotification
from shop.mail_backends import DeliveryError

logger = logging.getLogger(__name__)


def eligible_notifications():
    """Only the new policy's explicit outbox rows; never replay legacy mail."""
    return OrderNotification.objects.filter(channel='email', deduplication_key__startswith='v2:', event__kind='order').filter(
        Q(audience='admin', event__status='pending') | Q(audience='customer', event__status='confirmed'))


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


def deliver_pending(event_id=None, notification_id=None, limit=100):
    if not settings.ORDER_EMAIL_ENABLED:
        return
    rows = eligible_notifications().filter(state='pending', attempts__lt=settings.ORDER_EMAIL_MAX_ATTEMPTS).filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=timezone.now()))
    if event_id is not None:
        rows = rows.filter(event_id=event_id)
    if notification_id is not None:
        rows = rows.filter(pk=notification_id)
    for pk in list(rows.order_by('pk').values_list('pk', flat=True)[:max(1, min(500, limit))]):
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
        if not OrderNotification.objects.filter(pk=pk, state='pending', attempts__lt=settings.ORDER_EMAIL_MAX_ATTEMPTS).update(state='sending', recipient=recipient, attempts=F('attempts') + 1, next_attempt_at=None):
            continue
        try:
            admin = item.audience == 'admin'
            new = True
            title = 'New order received' if admin else 'Order Confirmed'
            path = reverse('crm:order_detail', args=[order.pk]) if admin else reverse('shop:order_number', args=[order.order_number]) if order.user_id else ''
            context = {'order': order, 'items': order.items.all(), 'title': title, 'admin_email': admin,
                'new_order': new, 'customer_note': event.customer_note, 'order_url': absolute_link(path) if path else '',
                'tracking_url': absolute_link(path) + '#tracking' if path and not admin and absolute_link(path) else '',
                'support_email': parseaddr(settings.DEFAULT_FROM_EMAIL)[1],
                'link_label': 'View order in CRM' if admin else 'View your order'}
            subject = f'New SuryaVets Order — {order.order_number}' if admin else f'Your SuryaVets Order {order.order_number} is Confirmed'
            sender_name, sender_email = parseaddr(settings.DEFAULT_FROM_EMAIL)
            message = EmailMultiAlternatives(subject=subject,
                body=render_to_string('emails/order.txt', context), from_email=formataddr((sender_name or settings.DEFAULT_FROM_NAME, sender_email)),
                to=[recipient], headers={'Message-ID': f'<suryavets-notification-{pk}@notifications.suryavets.invalid>'})
            message.attach_alternative(render_to_string('emails/order.html', context), 'text/html')
            message.idempotency_key = str(uuid.uuid5(uuid.NAMESPACE_URL, f'suryavets:{order.pk}:{pk}'))
            message.notification_reference = f'notification-{pk}'
            if message.send() != 1:
                raise RuntimeError('Delivery acceptance unconfirmed')
        except DeliveryError as error:
            attempt = item.attempts + 1
            retry_at = timezone.now() + timedelta(seconds=max(error.retry_after or 0, 60 * 2 ** (attempt - 1))) if error.retry_after is not None and attempt < settings.ORDER_EMAIL_MAX_ATTEMPTS else None
            OrderNotification.objects.filter(pk=pk).update(state='pending' if retry_at else 'failed',
                error=str(error), retryable=error.retryable, next_attempt_at=retry_at)
            logger.warning('Notification %s delivery failed (%s); retryable=%s', pk, str(error), error.retryable)
        except Exception:
            OrderNotification.objects.filter(pk=pk).update(state='failed', retryable=False, next_attempt_at=None,
                error='Delivery not confirmed. Reconcile with the provider before retrying.')
            logger.warning('Notification %s delivery unconfirmed; provider reconciliation required', pk)
        else:
            sandbox = getattr(message, 'delivery_sandbox', False)
            OrderNotification.objects.filter(pk=pk).update(state='preview' if sandbox else 'sent',
                sent_at=None if sandbox else timezone.now(), error='', retryable=False,
                provider_message_id=getattr(message, 'provider_message_id', ''))

"""Shared order events and customer-safe tracking. No gateway operations here."""
from django.db import transaction
from django.utils import timezone
from shop.models import Order, OrderStatusHistory, OrderNotification

STAGES = ['pending', 'confirmed', 'processing', 'packed', 'shipped', 'out_for_delivery', 'delivered']
NOTIFIABLE = {'pending', 'confirmed', 'shipped', 'out_for_delivery', 'delivered', 'cancelled'}


def record_event(order, status, *, kind='order', actor=None, internal_note='', customer_note=''):
    event = OrderStatusHistory.objects.create(order=order, kind=kind, status=status,
        timestamp=timezone.now(), changed_by=actor, internal_note=internal_note, customer_note=customer_note)
    if (kind == 'order' and status in NOTIFIABLE) or (kind == 'payment' and status == 'refunded'):
        OrderNotification.objects.get_or_create(event=event, channel='email', audience='customer', defaults={'recipient': order.email})
        if kind == 'order' and status == 'pending':
            from django.conf import settings
            OrderNotification.objects.get_or_create(event=event, channel='email', audience='admin', defaults={'recipient': settings.ORDER_NOTIFICATION_EMAIL})
        from .notifications import deliver_event_safely
        transaction.on_commit(lambda: deliver_event_safely(event.pk))
    return event


def tracker(order):
    events = list(order.events.filter(customer_visible=True))
    recorded = {e.status: e for e in events if e.kind == 'order'}
    current = STAGES.index(order.status) if order.status in STAGES else -1
    return [{'label': Order.Status(status).label, 'status': status,
             'timestamp': recorded[status].timestamp if status in recorded else None,
             'state': 'current' if status == order.status else 'done' if status in recorded or 0 <= i < current else 'future'}
            for i, status in enumerate(STAGES)]


def customer_can_cancel(order):
    return order.status in ('pending', 'confirmed') and order.payment_status in ('pending', 'failed') and (not order.stock_deducted or order.inventory_recorded)


@transaction.atomic
def update_review(user, order_id, kind, expected, status, note, reference=''):
    from .crm import require_staff, CRMError
    require_staff(user, 'manage_crm_payments' if kind == 'payment' else 'manage_crm_orders')
    if kind not in ('payment', 'return') or not 3 <= len(note.strip()) <= 1000:
        raise CRMError('Select a valid review type and explain the outcome.')
    order = Order.objects.select_for_update().get(pk=order_id)
    if kind == 'payment' and order.payment_method == 'online' and status == 'paid':
        raise CRMError('Online payments must be verified through the gateway, not marked paid manually.')
    field = kind + '_status'
    transitions = ({'pending': ('paid', 'failed'), 'failed': ('paid',), 'paid': ('refund_pending', 'partially_refunded', 'refunded'),
                   'refund_pending': ('partially_refunded', 'refunded'), 'partially_refunded': ('refund_pending', 'refunded')}
                  if kind == 'payment' else {'requested': ('approved', 'rejected'), 'approved': ('received',)})
    if getattr(order, field) != expected or status not in transitions.get(expected, ()):
        raise CRMError('That review transition is not available. Reload this order.')
    if kind == 'payment' and not 3 <= len(reference.strip()) <= 150:
        raise CRMError('Record an externally verified payment/refund reference. This form does not move money.')
    values = {field: status, 'updated_at': timezone.now()}
    if not Order.objects.filter(pk=order.pk, **{field: expected}).update(**values):
        raise CRMError('This record changed. Reload before trying again.')
    if kind == 'payment':
        # Keep original payment reference unchanged; refund references belong to their event.
        note = f'{note.strip()}\nExternal reference: {reference.strip()}'
    record_event(order, status, kind=kind, actor=user, internal_note=note,
                 customer_note='Your return request has been reviewed.' if kind == 'return' else '')
    return order

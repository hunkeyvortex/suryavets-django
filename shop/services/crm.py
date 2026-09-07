"""Permission-checked, transactional staff operations. No payment gateway side effects."""
import uuid

from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from shop.models import CRMActivity, InventoryMovement, Order, Product, ProductVariant


class CRMError(Exception):
    pass


def require_staff(user, permission='access_crm'):
    if not user.is_authenticated or not user.is_active or not user.is_staff or not user.has_perm('shop.access_crm') or not user.has_perm('shop.' + permission):
        raise PermissionDenied


def adjustment_token(user, product, variant=None):
    target = variant or product
    return signing.dumps({'actor': user.pk, 'product': str(product.pk), 'variant': variant.pk if variant else None,
                          'stock': target.stock_quantity, 'key': str(uuid.uuid4())}, salt='surya.crm.stock')


def sync_variant_total(product_id):
    total = ProductVariant.objects.filter(product_id=product_id, is_active=True).aggregate(total=Sum('stock_quantity'))['total'] or 0
    Product.objects.filter(pk=product_id).update(stock_quantity=total, updated_at=timezone.now())


@transaction.atomic
def adjust_inventory(user, product_id, variant_id, delta, reason, token):
    require_staff(user, 'adjust_crm_inventory')
    if not isinstance(delta, int) or delta == 0 or abs(delta) > 1000000 or not 3 <= len(reason.strip()) <= 500:
        raise CRMError('Enter a non-zero quantity change and a reason (3–500 characters).')
    try:
        data = signing.loads(token, salt='surya.crm.stock', max_age=3600)
        key = uuid.UUID(data['key'])
        if data['actor'] != user.pk or data['product'] != str(product_id) or data['variant'] != variant_id:
            raise ValueError
    except (signing.BadSignature, KeyError, ValueError, TypeError):
        raise CRMError('This stock review expired. Reload and review the current quantity.')
    product = Product.objects.select_for_update().get(pk=product_id)
    variant = ProductVariant.objects.select_for_update().get(pk=variant_id, product=product) if variant_id else None
    existing = InventoryMovement.objects.filter(request_key=key).first()
    if existing:
        return existing
    if not variant and (not product.track_inventory or product.variants.exists()):
        raise CRMError('Adjust an individual variant, or enable inventory tracking for this simple product first.')
    target = variant or product
    before = target.stock_quantity
    after = before + delta
    if before != data['stock']:
        raise CRMError('Stock changed since you opened this form. Reload and review the current quantity.')
    if after < 0 or after > 2147483647:
        raise CRMError('This adjustment would put stock outside its valid range.')
    if not type(target).objects.filter(pk=target.pk, stock_quantity=before).update(stock_quantity=after, updated_at=timezone.now()):
        raise CRMError('Stock changed. Reload and try again.')
    movement = InventoryMovement.objects.create(product=product, variant=variant, actor=user, kind='adjustment',
        delta=delta, quantity_before=before, quantity_after=after, reason=reason.strip(), request_key=key)
    if variant:
        sync_variant_total(product.pk)
    return movement


TRANSITIONS = {'pending': ('confirmed', 'cancelled'), 'confirmed': ('processing', 'cancelled'),
               'processing': ('packed', 'cancelled'), 'packed': ('shipped', 'cancelled'),
               'shipped': ('out_for_delivery',), 'out_for_delivery': ('delivered',)}


@transaction.atomic
def transition_order(user, order_id, expected, status, reason, *, courier='', tracking_number='', tracking_url='', customer_note='', customer=False):
    from .order_tracking import customer_can_cancel, record_event
    from django.core.validators import URLValidator
    from django.core.exceptions import ValidationError
    if not customer:
        require_staff(user, 'manage_crm_orders')
    if not 3 <= len(reason.strip()) <= 500:
        raise CRMError('Explain the status change (3–500 characters).')
    order = Order.objects.select_for_update().get(pk=order_id)
    if customer and (not user.is_authenticated or not user.is_active or order.user_id != user.pk or status != 'cancelled' or not customer_can_cancel(order)):
        raise PermissionDenied
    if order.status == status:
        return order  # Duplicate submission must never restock twice.
    if order.status != expected or status not in TRANSITIONS.get(order.status, ()):
        raise CRMError('This status change is no longer available. Review the latest order.')
    if status != 'cancelled' and order.payment_status != 'paid' and not (order.payment_method == 'cash_on_delivery' and order.payment_status == 'pending'):
        raise CRMError('Fulfilment requires a confirmed payment or a pending cash-on-delivery order.')
    if status == 'cancelled':
        if order.payment_status not in ('pending', 'failed'):
            raise CRMError('Paid/refunded orders require a separate refund and returns review. No refund has been issued.')
        if order.stock_deducted and not order.inventory_recorded:
            raise CRMError('This older order has no complete stock ledger. Reconcile it manually before cancellation; no stock was changed.')
    updates = {'status': status, 'updated_at': timezone.now()}
    if len(customer_note) > 1000:
        raise CRMError('Customer note is too long.')
    if status == 'shipped':
        if not 1 <= len(courier.strip()) <= 100 or not 1 <= len(tracking_number.strip()) <= 150:
            raise CRMError('Enter the courier and tracking number before dispatch.')
        if tracking_url:
            try:
                URLValidator(schemes=['https'])(tracking_url)
                if len(tracking_url) > 500: raise ValidationError('Too long')
            except ValidationError:
                raise CRMError('Use a valid HTTPS courier tracking URL.')
        updates.update(courier=courier.strip(), tracking_number=tracking_number.strip(), tracking_url=tracking_url)
    # Compare-and-swap also prevents concurrent transitions on SQLite.
    if not Order.objects.filter(pk=order.pk, status=expected).update(**updates):
        raise CRMError('Another staff member changed this order. Reload before continuing.')
    if status == 'cancelled' and order.stock_deducted:
        deductions = list(order.stock_movements.filter(kind='checkout').order_by('product_id', 'variant_id'))
        if not deductions or any(m.delta >= 0 for m in deductions):
            raise CRMError('The stock ledger is incomplete. No cancellation or stock change was applied.')
        products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[m.product_id for m in deductions]).order_by('pk')}
        variants = {v.pk: v for v in ProductVariant.objects.select_for_update().filter(pk__in=[m.variant_id for m in deductions if m.variant_id]).order_by('pk')}
        for movement in deductions:
            target = variants[movement.variant_id] if movement.variant_id else products[movement.product_id]
            before = target.stock_quantity
            after = before - movement.delta
            if after > 2147483647 or not type(target).objects.filter(pk=target.pk, stock_quantity=before).update(stock_quantity=after, updated_at=timezone.now()):
                raise CRMError('Stock changed or exceeds its valid range. Reload before cancelling.')
            InventoryMovement.objects.create(product_id=movement.product_id, variant_id=movement.variant_id, order=order,
                actor=user, kind='cancellation', delta=-movement.delta, quantity_before=before, quantity_after=after,
                reason=reason.strip(), reversal_of=movement)
            target.stock_quantity = after
        for pk in {m.product_id for m in deductions if m.variant_id}:
            sync_variant_total(pk)
    CRMActivity.objects.create(actor=user, order=order, kind='status', text=f'{expected} → {status}: {reason.strip()}')
    record_event(order, status, actor=user, internal_note=reason.strip(), customer_note=customer_note.strip())
    order.status = status
    return order


def add_note(user, text, order=None, email=''):
    require_staff(user, 'write_crm_notes')
    if not 3 <= len(text.strip()) <= 2000:
        raise CRMError('Write a note of 3–2,000 characters.')
    return CRMActivity.objects.create(actor=user, order=order, customer_email=email.lower(), kind='note', text=text.strip())

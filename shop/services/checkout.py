"""Atomic checkout. Never trust browser prices, quantities or order identifiers."""
import hashlib
import json
import uuid
from collections import defaultdict

from django.core import signing
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from shop.models import Cart, CustomerAddress, InventoryMovement, Order, OrderItem, Product, ProductVariant
from shop.services.cart import cart_items
from shop.services.coupons import CouponError, checkout_totals, reserve_coupon

SALT = 'suryavets.checkout.v1'


class CheckoutError(Exception):
    """A recoverable cart/stock problem to display without creating an order."""


def fingerprint(items, coupon_snapshot=None):
    rows = sorted((str(item.pk), str(item.product_id), str(item.product_variant_id), item.quantity,
                   str((item.product_variant or item.product).current_price) if item.product else 'missing') for item in items)
    return hashlib.sha256(json.dumps({'items': rows, 'coupon': coupon_snapshot}).encode()).hexdigest()


def review_token(cart, items, coupon_code='', *, pricing=None):
    pricing = checkout_totals(items, coupon_code) if pricing is None else pricing
    return signing.dumps({'cart': str(cart.pk), 'key': str(uuid.uuid4()),
        'snapshot': fingerprint(items, pricing['coupon_snapshot'])}, salt=SALT)


def read_token(token, cart):
    if not isinstance(token, str):
        raise CheckoutError('Your checkout review expired or is invalid. Please review the current cart and submit again.')
    try:
        data = signing.loads(token, salt=SALT, max_age=1800)
        key = uuid.UUID(data['key'])
        if data['cart'] != str(cart.pk) or not isinstance(data['snapshot'], str):
            raise ValueError
        return key, data['snapshot']
    except (signing.BadSignature, ValueError, TypeError, KeyError):
        raise CheckoutError('Your checkout review expired or is invalid. Please review the current cart and submit again.')


@transaction.atomic
def place_order(cart, user, token, data):
    # All storefront cart mutations take this same lock. PostgreSQL serializes
    # concurrent checkouts; conditional stock updates also protect SQLite.
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    user_id = user.pk if user.is_authenticated else None
    if cart.user_id != user_id:
        raise CheckoutError('This cart is not available to your account.')
    key, expected = read_token(token, cart)
    existing = Order.objects.filter(checkout_key=key, checkout_cart=cart, user_id=user_id).first()
    if existing:
        return existing

    from .payments import enabled
    online = data.get('payment_method') == 'online'
    if data.get('payment_method') != 'cash_on_delivery' and not (online and enabled()):
        raise CheckoutError('Online payments are not available yet. Please choose Cash on Delivery.')

    items = list(cart_items(cart))
    if not items:
        raise CheckoutError('Your cart is empty or this checkout has already completed.')
    # Consistent lock order: cart, coupon, products, variants. Preview is not a reservation.
    try:
        totals = checkout_totals(items, data.get('coupon_code', ''), lock=True)
    except CouponError as error:
        raise CheckoutError(str(error)) from error
    # Lock in a stable order across carts. Do not lock nullable select_related joins.
    ids = {i.product_id for i in items}
    ids.update(Product.objects.filter(pk__in=ids, variant_family__isnull=False).values_list('variant_family_id', flat=True))
    products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
    for product in products.values():
        if product.variant_family_id:
            product.variant_family = products[product.variant_family_id]
    variants = {v.pk: v for v in ProductVariant.objects.select_for_update().filter(pk__in=[i.product_variant_id for i in items if i.product_variant_id]).order_by('pk')}
    product_stock, variant_stock = defaultdict(int), defaultdict(int)
    for item in items:
        product = products.get(item.product_id)
        variant = variants.get(item.product_variant_id)
        from .purchasing import purchase_state, rejected
        if variant and product:
            variant.product = product
        state = purchase_state(product, variant, item.quantity, required_variant=bool(item.product_variant_id))
        if not state.allowed:
            rejected(state, product, variant, 'checkout')
            raise CheckoutError(f'{product.name if product else "Cart item"}: {state.message}')
        item.product, item.product_variant = product, variant
        if variant:
            variant.product = product
            variant_stock[variant.pk] += item.quantity
        elif product.track_inventory:
            product_stock[product.pk] += item.quantity
    # Refresh prices from the locked product objects, retaining the locked coupon.
    try:
        totals = checkout_totals(items, data.get('coupon_code', ''), lock=True)
    except CouponError as error:
        raise CheckoutError(str(error)) from error
    if fingerprint(items, totals['coupon_snapshot']) != expected:
        raise CheckoutError('Your cart or its prices changed, or your coupon changed. Please review the updated total before placing your order.')
    if totals['coupon']:
        try:
            reserve_coupon(totals['coupon'])
        except CouponError as error:
            raise CheckoutError(str(error)) from error
    for pk, quantity in sorted(product_stock.items(), key=lambda pair: str(pair[0])):
        if not Product.objects.filter(pk=pk, is_active=True, stock_quantity__gte=quantity).update(stock_quantity=F('stock_quantity') - quantity, updated_at=timezone.now()):
            raise CheckoutError(f'{products[pk].name}: there is not enough stock. Please update your cart.')
    for pk, quantity in sorted(variant_stock.items()):
        if not ProductVariant.objects.filter(pk=pk, is_active=True, stock_quantity__gte=quantity).update(stock_quantity=F('stock_quantity') - quantity, updated_at=timezone.now()):
            raise CheckoutError(f'{variants[pk].product.name}: there is not enough stock for this pack.')
    for product_id in {variants[pk].product_id for pk in variant_stock}:
        total = ProductVariant.objects.filter(product_id=product_id, is_active=True).aggregate(total=Sum('stock_quantity'))['total'] or 0
        Product.objects.filter(pk=product_id).update(stock_quantity=total, updated_at=timezone.now())

    values = data.copy()
    if values['billing_same_as_shipping']:
        for suffix in ('name', 'address_line_1', 'address_line_2', 'city', 'state', 'postal_code'):
            values['billing_' + suffix] = values['shipping_' + suffix]
    order = Order.objects.create(user_id=user_id, checkout_key=key, checkout_cart=cart,
        status='awaiting_payment' if online else 'pending',
        stock_deducted=bool(product_stock or variant_stock), inventory_recorded=True,
        subtotal=totals['subtotal'], shipping_cost=totals['shipping'], total=totals['total'],
        discount_amount=totals['discount_amount'], coupon=totals['coupon'],
        coupon_code=totals['coupon'].code if totals['coupon'] else '',
        **{field: values[field] for field in (
            'email', 'phone', 'shipping_name', 'shipping_address_line_1', 'shipping_address_line_2',
            'shipping_city', 'shipping_state', 'shipping_postal_code', 'billing_same_as_shipping',
            'billing_name', 'billing_address_line_1', 'billing_address_line_2', 'billing_city',
            'billing_state', 'billing_postal_code', 'notes', 'payment_method')})
    snapshot_images = {item.pk: item.display_image for item in items}
    OrderItem.objects.bulk_create([OrderItem(order=order, product=item.product, product_variant=item.product_variant,
        product_name=item.product.name, sku=(item.product_variant or item.product).sku,
        variant_name=item.product_variant.name if item.product_variant else '',
        unit_price=(item.product_variant or item.product).current_price, quantity=item.quantity,
        image_reference=snapshot_images[item.pk].display_url if snapshot_images[item.pk] else '') for item in items])
    if online:
        from shop.models import PaymentAttempt
        if order.total <= 0:
            raise CheckoutError('Online payment requires a positive order total.')
        PaymentAttempt.objects.create(order=order, amount=int(order.total * 100))
    from .order_tracking import record_event
    record_event(order, order.status, actor=user if user_id else None)
    # Record only quantities actually deducted, inside the same transaction.
    movements = []
    for pk, quantity in product_stock.items():
        movements.append(InventoryMovement(product=products[pk], order=order, kind='checkout', delta=-quantity,
            quantity_before=products[pk].stock_quantity, quantity_after=products[pk].stock_quantity - quantity, reason='Checkout reservation'))
    for pk, quantity in variant_stock.items():
        movements.append(InventoryMovement(product_id=variants[pk].product_id, variant=variants[pk], order=order,
            kind='checkout', delta=-quantity, quantity_before=variants[pk].stock_quantity,
            quantity_after=variants[pk].stock_quantity - quantity, reason='Checkout reservation'))
    InventoryMovement.objects.bulk_create(movements)
    if values['save_address'] and user_id:
        from django.contrib.auth import get_user_model
        get_user_model().objects.select_for_update().get(pk=user_id)
        address = CustomerAddress.objects.filter(user_id=user_id, is_default_shipping=True).first()
        if address is None:
            address = CustomerAddress(user_id=user_id, label='Home', is_default_shipping=True)
        for target, source in {'full_name': 'shipping_name', 'phone': 'phone', 'address_line_1': 'shipping_address_line_1',
                               'address_line_2': 'shipping_address_line_2', 'city': 'shipping_city', 'state': 'shipping_state', 'postal_code': 'shipping_postal_code'}.items():
            setattr(address, target, values[source])
        address.save()
    cart.items.all().delete()
    return order

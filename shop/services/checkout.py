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
from shop.services.cart import cart_items, cart_totals

SALT = 'suryavets.checkout.v1'


class CheckoutError(Exception):
    """A recoverable cart/stock problem to display without creating an order."""


def fingerprint(items):
    rows = sorted((str(item.pk), str(item.product_id), str(item.product_variant_id), item.quantity,
                   str((item.product_variant or item.product).current_price) if item.product else 'missing') for item in items)
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def review_token(cart, items):
    return signing.dumps({'cart': str(cart.pk), 'key': str(uuid.uuid4()), 'snapshot': fingerprint(items)}, salt=SALT)


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

    items = list(cart_items(cart))
    if not items:
        raise CheckoutError('Your cart is empty or this checkout has already completed.')
    # Lock in a stable order across carts. Do not lock nullable select_related joins.
    products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[i.product_id for i in items]).order_by('pk')}
    variants = {v.pk: v for v in ProductVariant.objects.select_for_update().filter(pk__in=[i.product_variant_id for i in items if i.product_variant_id]).order_by('pk')}
    product_stock, variant_stock = defaultdict(int), defaultdict(int)
    for item in items:
        product = products.get(item.product_id)
        variant = variants.get(item.product_variant_id)
        if not product or not product.is_active:
            raise CheckoutError('A product in your cart is no longer available. Please update your cart.')
        if item.quantity < 1 or item.quantity > 10000:
            raise CheckoutError('Please choose a valid quantity for every cart item.')
        if item.product_variant_id and (not variant or not variant.is_active or variant.product_id != product.pk):
            raise CheckoutError(f'{product.name}: the selected pack is no longer available.')
        if not variant and product.variants.filter(is_active=True).exists():
            raise CheckoutError(f'{product.name}: please select a pack again.')
        item.product, item.product_variant = product, variant
        if variant:
            variant.product = product
            variant_stock[variant.pk] += item.quantity
        elif product.track_inventory:
            product_stock[product.pk] += item.quantity
        if (variant or product).current_price < 0:
            raise CheckoutError(f'{product.name}: pricing needs review before purchase.')
    if fingerprint(items) != expected:
        raise CheckoutError('Your cart or its prices changed. Please review the updated total before placing your order.')
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
    totals = cart_totals(items)
    order = Order.objects.create(user_id=user_id, checkout_key=key, checkout_cart=cart,
        stock_deducted=bool(product_stock or variant_stock), inventory_recorded=True,
        subtotal=totals['subtotal'], shipping_cost=totals['shipping'], total=totals['total'],
        **{field: values[field] for field in (
            'email', 'phone', 'shipping_name', 'shipping_address_line_1', 'shipping_address_line_2',
            'shipping_city', 'shipping_state', 'shipping_postal_code', 'billing_same_as_shipping',
            'billing_name', 'billing_address_line_1', 'billing_address_line_2', 'billing_city',
            'billing_state', 'billing_postal_code', 'notes', 'payment_method')})
    OrderItem.objects.bulk_create([OrderItem(order=order, product=item.product, product_variant=item.product_variant,
        product_name=item.product.name, sku=(item.product_variant or item.product).sku,
        variant_name=item.product_variant.name if item.product_variant else '',
        unit_price=(item.product_variant or item.product).current_price, quantity=item.quantity) for item in items])
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
        address = CustomerAddress.objects.filter(user_id=user_id, is_default_shipping=True).first()
        if address is None:
            address = CustomerAddress(user_id=user_id, label='Home', is_default_shipping=True)
        for target, source in {'full_name': 'shipping_name', 'phone': 'phone', 'address_line_1': 'shipping_address_line_1',
                               'address_line_2': 'shipping_address_line_2', 'city': 'shipping_city', 'state': 'shipping_state', 'postal_code': 'shipping_postal_code'}.items():
            setattr(address, target, values[source])
        address.save()
    cart.items.all().delete()
    return order

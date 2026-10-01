"""Reorder exact identities at current prices, without reserving stock."""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from shop.models import Cart, CartItem, Order, Product, ProductVariant


@transaction.atomic
def buy_again(user, order_id):
    order = Order.objects.get(pk=order_id)
    if not user.is_authenticated or order.user_id != user.pk:
        raise PermissionDenied
    cart, _ = Cart.objects.get_or_create(user=user)
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    skipped, added = [], 0
    for line in order.items.all():
        product = Product.objects.filter(pk=line.product_id, is_active=True).first()
        if product and product.variant_family_id and not Product.objects.filter(pk=product.variant_family_id, is_active=True).exists():
            product = None
        variant = ProductVariant.objects.filter(pk=line.product_variant_id, product=product, is_active=True).first() if product and line.product_variant_id else None
        # A deleted selected pack never falls back to the base product, even if FK is now NULL.
        missing_pack = (bool(line.variant_name) or bool(line.product_variant_id)) and not variant
        if not product or missing_pack or (not variant and product.variants.exists()):
            skipped.append(f'{line.product_name} {line.variant_name}: no longer available; no size substituted.')
            continue
        target = variant or product
        existing = cart.items.filter(product=product, product_variant=variant).first()
        quantity = line.quantity + (existing.quantity if existing else 0)
        from .purchasing import purchase_state, rejected
        state = purchase_state(product, variant, quantity, required_variant=bool(line.variant_name or line.product_variant_id))
        if not state.allowed:
            rejected(state, product, variant, 'reorder')
            skipped.append(f'{line.product_name} {line.variant_name}: {state.message}')
            continue
        if existing:
            existing.quantity = quantity
            existing.save(update_fields=['quantity'])
        else:
            CartItem.objects.create(cart=cart, product=product, product_variant=variant, quantity=line.quantity)
        added += line.quantity
    return added, skipped

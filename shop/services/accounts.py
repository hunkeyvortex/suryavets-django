"""Carry an anonymous basket into an account without transferring guest orders."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from shop.models import Cart, CartItem
from shop.services.cart import SESSION_CART_KEY


class CartMergeError(Exception):
    pass


@transaction.atomic
def merge_guest_cart(request, user):
    guest_id = request.session.get(SESSION_CART_KEY)
    if not guest_id:
        return
    try:
        guest = Cart.objects.filter(pk=guest_id, user__isnull=True).first()
    except (ValidationError, ValueError):
        return
    if not guest:
        return
    get_user_model().objects.select_for_update().get(pk=user.pk)
    account, _ = Cart.objects.get_or_create(user=user)
    locked = list(Cart.objects.select_for_update().filter(pk__in=[guest.pk, account.pk]).order_by('pk'))
    if not any(c.pk == guest.pk and c.user_id is None for c in locked):
        return
    for item in guest.items.all():
        existing = account.items.filter(product_id=item.product_id, product_variant_id=item.product_variant_id).first()
        quantity = item.quantity + (existing.quantity if existing else 0)
        if quantity > 10000:
            raise CartMergeError('The combined basket exceeds the quantity limit. Reduce your guest basket before signing in.')
        if existing:
            existing.quantity = quantity
            existing.save(update_fields=['quantity'])
        else:
            CartItem.objects.create(cart=account, product_id=item.product_id, product_variant_id=item.product_variant_id, quantity=quantity)
    guest.items.all().delete()
    # Preserve the anonymous cart ID for existing guest receipts; never reassign orders.

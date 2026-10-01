"""Session-aware cart helpers shared by storefront views and context processors."""

from decimal import Decimal
from django.core.exceptions import ValidationError

from shop.models import Cart


SESSION_CART_KEY = 'suryavets_cart_id'
FREE_DELIVERY_THRESHOLD = Decimal('499.00')
STANDARD_SHIPPING_COST = Decimal('50.00')


def get_cart(request, *, create=True):
    """Return the current user's cart or a cart identified by their Django session."""
    if request.user.is_authenticated:
        if not create:
            return Cart.objects.filter(user=request.user).first()
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    cart_id = request.session.get(SESSION_CART_KEY)
    try:
        cart = Cart.objects.filter(pk=cart_id, user__isnull=True).first() if cart_id else None
    except (ValidationError, ValueError):
        cart = None
    if cart or not create:
        return cart

    cart = Cart.objects.create()
    request.session[SESSION_CART_KEY] = str(cart.pk)
    return cart


def cart_items(cart):
    if not cart:
        return []
    return cart.items.select_related('product', 'product_variant', 'product_variant__product', 'product_variant__image').prefetch_related('product__images')


def cart_totals(items):
    subtotal = sum((item.total_price for item in items), Decimal('0.00'))
    shipping = Decimal('0.00') if not items or subtotal >= FREE_DELIVERY_THRESHOLD else STANDARD_SHIPPING_COST
    return {
        'subtotal': subtotal,
        'shipping': shipping,
        'total': subtotal + shipping,
        'total_items': sum(item.quantity for item in items),
        'amount_until_free_delivery': max(FREE_DELIVERY_THRESHOLD - subtotal, Decimal('0.00')),
        'free_delivery_threshold': FREE_DELIVERY_THRESHOLD,
    }


def cart_snapshot(cart):
    """Presentation values computed using the same Decimal totals as cart/checkout."""
    items = list(cart_items(cart))
    from .purchasing import cart_issues
    problems = cart_issues(items)
    totals = cart_totals(items)
    def currency(amount):
        return f'₹{amount:,.2f}'
    return {
        'purchase_issues': problems, 'checkout_allowed': not problems,
        'items': [{'id': item.pk, 'quantity': item.quantity,
                   'line_total': 'Unavailable' if item.purchase_issue else currency(item.total_price),
                   'unit_price': 'Unavailable' if item.purchase_issue else currency((item.product_variant or item.product).current_price)} for item in items],
        'total_items': totals['total_items'],
        'subtotal': currency(totals['subtotal']), 'shipping': currency(totals['shipping']),
        'total': currency(totals['total']), 'free_delivery': totals['shipping'] == 0,
        'progress': str(totals['subtotal']), 'threshold': str(totals['free_delivery_threshold']),
        'delivery_remaining': currency(totals['amount_until_free_delivery']),
    }

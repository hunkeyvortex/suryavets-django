"""Coupon quotes are recalculated on the server, then reserved within checkout."""
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import F, Q
from django.utils import timezone
from shop.models import Coupon
from shop.services.cart import cart_totals


class CouponError(Exception):
    pass


def checkout_totals(items, code='', *, lock=False):
    totals = cart_totals(items)
    totals.update(coupon=None, coupon_snapshot=None, discount_amount=Decimal('0.00'))
    code = str(code or '').strip().upper()
    if not code:
        return totals
    if len(code) > 40:
        raise CouponError('Please enter a valid coupon code.')
    coupons = Coupon.objects.select_for_update() if lock else Coupon.objects.all()
    coupon = coupons.filter(code=code).first()
    now = timezone.now()
    if not coupon or not coupon.is_active:
        raise CouponError('This coupon is invalid or is not active.')
    if coupon.starts_at and now < coupon.starts_at:
        raise CouponError('This coupon is not available yet.')
    if coupon.ends_at and now >= coupon.ends_at:
        raise CouponError('This coupon has expired.')
    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        raise CouponError('This coupon has reached its usage limit.')
    if totals['subtotal'] < coupon.minimum_subtotal:
        raise CouponError(f'This coupon needs a product subtotal of at least ₹{coupon.minimum_subtotal:,.2f}.')
    discount = coupon.value if coupon.kind == Coupon.Kind.FIXED else totals['subtotal'] * coupon.value / Decimal('100')
    if coupon.maximum_discount is not None:
        discount = min(discount, coupon.maximum_discount)
    discount = min(totals['subtotal'], discount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if discount <= 0:
        raise CouponError('This coupon does not give a discount on the current basket.')
    totals.update(coupon=coupon, discount_amount=discount, total=totals['total'] - discount,
        coupon_snapshot=[coupon.pk, coupon.code, coupon.updated_at.isoformat(), str(discount)])
    return totals


def reserve_coupon(coupon):
    """Called only inside place_order's transaction after the coupon row is locked."""
    now = timezone.now()
    available = Coupon.objects.filter(pk=coupon.pk, is_active=True).filter(
        Q(max_uses__isnull=True) | Q(used_count__lt=F('max_uses'))).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now)).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
    if not available.update(used_count=F('used_count') + 1):
        raise CouponError('This coupon is no longer available. Please review your order again.')

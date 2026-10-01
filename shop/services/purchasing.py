"""Shared purchase policy. No free-item exception and no source-data writes.

An explicit latest CRM hold blocks sale. Absence of a review is not a hold:
mandatory catalog approval remains a separate launch rollout.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Q, F, Value, OuterRef, Subquery, DecimalField, ExpressionWrapper, Exists
from django.db.models.functions import Coalesce, Round

logger = logging.getLogger('shop.purchase_safety')


@dataclass(frozen=True)
class PurchaseState:
    code: str = ''
    message: str = ''

    @property
    def allowed(self):
        return not self.code


def held_expression(reference):
    from shop.models import CatalogReviewEvent
    latest = CatalogReviewEvent.objects.filter(product_id=reference).order_by('-created_at', '-pk')
    return Coalesce(Subquery(latest.values('decision')[:1]), Value(''))


def annotate_products(queryset):
    return queryset.annotate(purchase_decision=held_expression(OuterRef('pk')))


def held(product):
    decision = getattr(product, 'purchase_decision', None)
    if decision is None:
        decision = product.catalog_reviews.order_by('-created_at', '-pk').values_list('decision', flat=True).first()
    return decision == 'held'


def has_packs(product):
    return bool(list(product.variants.all())) or any(list(p.variants.all()) for p in product.family_members.all())


def purchase_state(product, variant=None, quantity=1, *, required_variant=False):
    if not product or not product.is_active:
        return PurchaseState('inactive_product', 'This product is no longer available.')
    root = product.variant_family if product.variant_family_id else product
    if not root.is_active or root.variant_family_id:
        return PurchaseState('inactive_family', 'This product family is unavailable.')
    if variant and (variant.product_id != product.pk or not variant.is_active):
        return PurchaseState('invalid_variant', 'The selected pack is no longer available; please choose another pack.')
    if not variant and (required_variant or product.variant_family_id or has_packs(product)):
        return PurchaseState('variant_required', 'Please select an available pack; no size has been substituted.')
    if held(product) or (root.pk != product.pk and held(root)):
        return PurchaseState('held', 'This item is awaiting catalog review. Please contact SuryaVets.')
    item = variant or product
    price = Decimal(item.current_price)
    if not price.is_finite() or price <= 0:
        return PurchaseState('price_unavailable', 'Price unavailable. Please contact SuryaVets.')
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 10000:
        return PurchaseState('quantity', 'Please enter a quantity between 1 and 10000.')
    if (variant is not None or product.track_inventory) and (item.stock_quantity is None or item.stock_quantity < quantity):
        return PurchaseState('stock', 'The requested quantity is not currently available; there is not enough stock.')
    return PurchaseState()


def rejected(state, product, variant, path):
    if not state.allowed:
        logger.info('Purchase rejected path=%s reason=%s product=%s variant=%s',
            path, state.code, getattr(product, 'pk', None), getattr(variant, 'pk', None))


def cart_issues(items):
    issues = []
    for item in items:
        state = purchase_state(item.product, item.product_variant, item.quantity, required_variant=bool(item.product_variant_id))
        item.purchase_issue = state.message
        if not state.allowed:
            label = f'{item.product.name} — {item.product_variant.name}' if item.product_variant else item.product.name
            issues.append(f'{label}: {state.message}')
    return issues


def effective_price(*, variant=False):
    money = DecimalField(max_digits=10, decimal_places=2)
    regular = Coalesce(F('price_override'), F('product__base_price'), output_field=money) if variant else F('base_price')
    legacy = ExpressionWrapper(regular * (Value(Decimal('100.0')) - F('discount_percentage')) / Value(Decimal('100.0')), output_field=money)
    return Coalesce(F('selling_price'), Round(legacy, precision=2), output_field=money)


def eligible_variants(queryset):
    """SQL projection of the same activity/hold/positive-price/stock rules."""
    from shop.models import Product
    products = annotate_products(Product.objects.filter(pk=OuterRef('product_id'), is_active=True)).exclude(purchase_decision='held')
    roots = annotate_products(Product.objects.filter(pk=OuterRef('product__variant_family_id'), is_active=True, variant_family__isnull=True)).exclude(purchase_decision='held')
    return queryset.alias(purchase_price=effective_price(variant=True)).filter(
        Exists(products), Q(product__variant_family__isnull=True) | Exists(roots),
        is_active=True, stock_quantity__gt=0, purchase_price__gt=0)


def simple_price_expression():
    from shop.models import Product, ProductVariant
    packs = ProductVariant.objects.filter(Q(product_id=OuterRef('pk')) | Q(product__variant_family_id=OuterRef('pk')))
    candidates = annotate_products(Product.objects.filter(pk=OuterRef('pk'), is_active=True,
        variant_family__isnull=True)).filter(~Exists(packs)).exclude(purchase_decision='held').alias(
        price=effective_price()).filter(Q(track_inventory=False) | Q(stock_quantity__gt=0), price__gt=0)
    return Subquery(candidates.annotate(result=F('price')).values('result')[:1])

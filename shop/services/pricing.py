"""Money calculations shared by importers, models and catalogue queries."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import DecimalField, ExpressionWrapper, F, Value, OuterRef, Subquery, Q, Exists
from django.db.models.functions import Coalesce, Round


CENT = Decimal('0.01')


def selling_price(regular, discount, exact=None):
    if exact is not None:
        return exact
    return (regular * (100 - discount) / 100).quantize(CENT, rounding=ROUND_HALF_UP)


def discount_percent(regular, current):
    if regular <= 0 or current >= regular:
        return 0
    return int(((regular - current) * 100 / regular).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def export_prices(row):
    """Reject missing/invalid prices rather than accidentally importing free items."""
    def money(value, label, optional=False):
        if value is None or not str(value).strip():
            if optional:
                return None
            raise ValueError(f'{label} is missing')
        try:
            result = Decimal(str(value).strip())
            if not result.is_finite() or result < 0 or result > Decimal('99999999.99'):
                raise ValueError(f'{label} must be a finite, non-negative price')
            if result != result.quantize(CENT):
                raise ValueError(f'{label} has more than two decimal places')
            return result.quantize(CENT)
        except InvalidOperation as error:
            raise ValueError(f'{label} is not a valid price') from error
    current = money(row.get('Variant Price'), 'Variant Price')
    compare = money(row.get('Variant Compare At Price'), 'Variant Compare At Price', optional=True)
    regular = max(compare, current) if compare is not None else current
    return regular, current, discount_percent(regular, current)


def family_variant_queryset(*, active_products=False):
    """Use indexed family IDs instead of an OR across a joined variant/product scan.

    This queryset is embedded once in an outer Product query. The member lookup
    is another level down, so its references must reach the outer Product.
    """
    from shop.models import Product, ProductVariant
    members = Product.objects.filter(
        Q(pk=OuterRef(OuterRef('pk'))) | Q(variant_family_id=OuterRef(OuterRef('pk')))
    ).order_by()
    members = members.values('pk')
    variants = ProductVariant.objects.filter(product_id__in=Subquery(members))
    if active_products:
        # Keep the active flag out of the family-ID OR and the price join. On
        # SQLite either can otherwise select the low-selectivity active index
        # and rescan the entire catalog for each root. This is one PK lookup.
        variants = variants.filter(Exists(Product.objects.filter(pk=OuterRef('product_id'), is_active=True)))
    return variants


def catalog_price_expression():
    from .purchasing import eligible_variants, simple_price_expression, effective_price
    money = DecimalField(max_digits=10, decimal_places=2)
    variants = eligible_variants(family_variant_queryset(active_products=True)).annotate(
        offer_price=effective_price(variant=True))
    return Coalesce(Subquery(variants.order_by('offer_price').values('offer_price')[:1]),
                    simple_price_expression(), output_field=money)

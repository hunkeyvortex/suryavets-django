"""Money calculations shared by importers, models and catalogue queries."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import DecimalField, ExpressionWrapper, F, Value, OuterRef, Subquery, Q
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


def catalog_price_expression():
    from shop.models import ProductVariant
    money = DecimalField(max_digits=10, decimal_places=2)
    legacy = ExpressionWrapper(
        F('base_price') * (Value(Decimal('100.0')) - F('discount_percentage')) / Value(Decimal('100.0')),
        output_field=money,
    )
    variant_regular = Coalesce(F('price_override'), F('product__base_price'), output_field=money)
    variant_legacy = ExpressionWrapper(variant_regular * (Value(Decimal('100')) - F('discount_percentage')) / Value(Decimal('100')), output_field=money)
    variants = ProductVariant.objects.filter(Q(product_id=OuterRef('pk')) | Q(product__variant_family_id=OuterRef('pk')), is_active=True, product__is_active=True).annotate(
        offer_price=Coalesce(F('selling_price'), Round(variant_legacy, precision=2), output_field=money))
    return Coalesce(Subquery(variants.filter(stock_quantity__gt=0).order_by('offer_price').values('offer_price')[:1]),
                    Subquery(variants.order_by('offer_price').values('offer_price')[:1]),
                    F('selling_price'), Round(legacy, precision=2), output_field=money)

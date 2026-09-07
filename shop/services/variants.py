"""Exact, opt-in comparisons. Never infer net quantity from a product name."""
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

CENT = Decimal('0.01')
UNITS = {'g': ('kg', Decimal('0.001')), 'kg': ('kg', Decimal(1)),
         'ml': ('L', Decimal('0.001')), 'L': ('L', Decimal(1)), 'count': ('item', Decimal(1))}


def variant_options(product, variants):
    options, groups = [], defaultdict(list)
    photos = {p.pk: p for p in product.images.all()}
    for variant in variants:
        if not variant.is_active:
            continue
        price, regular = variant.current_price, variant.original_price
        saving = max(Decimal(0), regular - price)
        photo = photos.get(variant.image_id)
        option = {'variant': variant, 'price': price, 'regular': regular, 'saving': saving,
                  'discount': int(saving * 100 / regular) if regular > 0 else 0,
                  'unit_price': None, 'unit_label': '', 'value_saving': Decimal(0),
                  'best_value': False, 'baseline': '', 'image_url': photo.display_url if photo else '',
                  'image_alt': (photo.alt_text or f'{product.name} — {variant.name}') if photo else ''}
        if variant.quantity and variant.quantity > 0 and variant.unit in UNITS:
            label, factor = UNITS[variant.unit]
            quantity = variant.quantity * factor
            option.update(normalized_quantity=quantity, rate=price / quantity, unit_label=label,
                          unit_price=(price / quantity).quantize(CENT, rounding=ROUND_HALF_UP))
            if variant.comparison_group.strip() and variant.is_in_stock:
                groups[(variant.comparison_group.strip().casefold(), label)].append(option)
        options.append(option)
    for group in groups.values():
        if len({o['normalized_quantity'] for o in group}) < 2:
            continue
        baseline = min(group, key=lambda o: (o['normalized_quantity'], o['rate']))
        best = min(o['rate'] for o in group)
        # Ties may all be best, but do not claim value when every unit rate is equal.
        meaningful = best < max(o['rate'] for o in group)
        for option in group:
            if option['normalized_quantity'] > baseline['normalized_quantity']:
                saved = baseline['rate'] * option['normalized_quantity'] - option['price']
                option['value_saving'] = max(Decimal(0), saved).quantize(CENT, rounding=ROUND_DOWN)
                option['baseline'] = baseline['variant'].name
            option['best_value'] = meaningful and option['rate'] == best
    return options


def card_offer(product):
    variants = [v for v in product.variants.all() if v.is_active]
    available = [v for v in variants if v.is_in_stock]
    item = min(available or variants, key=lambda v: v.current_price) if variants else product
    return {'price': item.current_price, 'regular': item.original_price,
            'discount': int((item.original_price - item.current_price) * 100 / item.original_price) if item.original_price > 0 and item.current_price < item.original_price else 0,
            'sale': item.current_price < item.original_price, 'multiple': len(variants) > 1,
            'variant': variants[0] if len(variants) == 1 else None}

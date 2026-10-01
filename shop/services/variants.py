"""Exact, opt-in comparisons. Never infer net quantity from a product name."""
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

CENT = Decimal('0.01')
UNITS = {'g': ('kg', Decimal('0.001')), 'kg': ('kg', Decimal(1)),
         'ml': ('L', Decimal('0.001')), 'L': ('L', Decimal(1)), 'count': ('item', Decimal(1))}


def variant_options(product, variants):
    options, groups = [], defaultdict(list)
    for variant in variants:
        if not variant.is_active:
            continue
        price, regular = variant.current_price, variant.original_price
        from .purchasing import purchase_state
        state = purchase_state(variant.product, variant)
        saving = max(Decimal(0), regular - price) if state.allowed else Decimal(0)
        from .pack_images import pack_photos
        photos = pack_photos(variant)
        photo = photos[0] if photos else None
        option = {'variant': variant, 'price': price, 'regular': regular, 'saving': saving,
                  'discount': int(saving * 100 / regular) if regular > 0 else 0,
                  'unit_price': None, 'unit_label': '', 'value_saving': Decimal(0),
                  'best_value': False, 'baseline': '', 'available': state.allowed, 'reason': state.message, 'image_url': photo.display_url if photo else '',
                  'image_alt': (photo.alt_text or f'{product.name} — {variant.name}') if photo else ''}
        option['image_missing'] = not photo
        option['photos'] = photos
        option['image_ids'] = ','.join(str(p.pk) for p in photos)
        if state.allowed and variant.quantity and variant.quantity > 0 and variant.unit in UNITS:
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
    from .purchasing import purchase_state
    from .pack_families import buying_variants
    variants = buying_variants(product)
    available = [v for v in variants if purchase_state(v.product, v).allowed]
    if not available and (variants or not purchase_state(product).allowed):
        return {'price': None, 'regular': None, 'in_stock': False, 'discount': 0,
                'sale': False, 'multiple': len(variants) > 1, 'variant': None}
    item = min(available or variants, key=lambda v: v.current_price) if variants else product
    return {'price': item.current_price, 'regular': item.original_price,
            'in_stock': bool(available) if variants else purchase_state(product).allowed,
            'discount': int((item.original_price - item.current_price) * 100 / item.original_price) if item.original_price > 0 and item.current_price < item.original_price else 0,
            'sale': item.current_price < item.original_price, 'multiple': len(variants) > 1,
            'variant': variants[0] if len(variants) == 1 else None}

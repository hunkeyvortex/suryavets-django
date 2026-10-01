"""Read-only presentation of verified packs; all purchase validation stays server-side."""
from decimal import Decimal
from .pack_families import family_products


def product_card(product):
    choices = []
    for source in family_products(product):
        if not source.is_active:
            continue
        variants = list(source.variants.all())
        for variant in variants:
            if not variant.is_active:
                continue
            from .pack_images import pack_photos
            photos = pack_photos(variant)
            photo = photos[0] if photos else None
            choices.append(_choice(variant, photo, variant))
    choices.sort(key=lambda option: (option['variant'].display_order, option['variant'].name, option['variant'].pk))
    available = [option for option in choices if option['available']]
    selected = min(available or choices, key=lambda option: option['price']) if choices else _choice(product, product.images.first(), None)
    return {'choices': choices, 'selected': selected, 'multiple': len(choices) > 1}


def _choice(item, photo, variant):
    from .purchasing import purchase_state
    state = purchase_state(variant.product if variant else item, variant)
    price, regular = item.current_price, item.original_price
    saving = max(Decimal(0), regular - price) if state.allowed else Decimal(0)
    tracked = variant is not None or item.track_inventory
    return {'variant': variant, 'price': price, 'regular': regular, 'saving': saving,
            'discount': int(saving * 100 / regular) if regular > 0 else 0,
            'sale': saving > 0, 'available': state.allowed, 'reason': state.message,
            'max_quantity': min(10000, max(1, item.stock_quantity)) if tracked else 10000,
            'image': photo.thumbnail_url if photo else '',
            'alt': (photo.alt_text or f'{item.product.name if variant else item.name} {variant.name if variant else ""}') if photo else ''}

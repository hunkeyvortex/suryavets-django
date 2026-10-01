"""Presentation only. Never borrow another source product's pack artwork."""


def pack_photos(variant):
    photos = product_photos(variant.product)
    if variant.image_id:
        selected = next((p for p in photos if p.pk == variant.image_id), None)
        if selected is None:
            return []
        if len(list(variant.product.variants.all())) == 1:
            return [selected, *[p for p in photos if p.pk != selected.pk]]
        return [selected]
    return [p for p in photos if not p.family_reference_for_id] if len(list(variant.product.variants.all())) == 1 else []


def product_photos(product):
    """Use recorded validation state; no storage or filesystem calls on requests."""
    return sorted([p for p in product.images.all() if p.is_active and p.product_id == product.pk and p.display_url],
                  key=lambda p: (not p.is_primary, p.order, p.pk))


def family_photo(product):
    from .pack_families import family_products
    root = product.variant_family if product.variant_family_id else product
    if not root.is_active or root.variant_family_id:
        return None
    for member in family_products(root):
        if not member.is_active:
            continue
        for photo in product_photos(member):
            if photo.family_reference_for_id == root.pk and photo.family_reference_note.strip():
                return photo
    return None

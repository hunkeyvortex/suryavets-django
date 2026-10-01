"""Presentation only. Never borrow another source product's pack artwork."""


def pack_photos(variant):
    photos = [p for p in variant.product.images.all() if p.is_active and p.product_id == variant.product_id]
    if variant.image_id:
        selected = next((p for p in photos if p.pk == variant.image_id), None)
        if selected is None:
            return []
        if len(list(variant.product.variants.all())) == 1:
            return [selected, *[p for p in photos if p.pk != selected.pk]]
        return [selected]
    return photos if len(list(variant.product.variants.all())) == 1 else []

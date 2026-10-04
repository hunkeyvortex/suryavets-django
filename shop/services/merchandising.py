"""Manual-only homepage selection. Never changes catalog or inventory data."""
from django.conf import settings
from .pack_review_snapshot import snapshot
from .pack_families import family_products
from .product_cards import product_card


def eligibility(product, evidence=None, *, require_image=True):
    if not product.is_active or product.variant_family_id:
        return 'Inactive or non-canonical family'
    evidence = snapshot() if evidence is None else evidence
    if not evidence.get('generated_at'):
        # Production does not ship generated audit files. Require a durable staff
        # publishing decision rather than silently trusting bulk import flags.
        decision = getattr(product, 'purchase_decision', None)
        if decision is None:
            decision = product.catalog_reviews.order_by('-created_at', '-pk').values_list('decision', flat=True).first()
        if not product.merchandising_active or decision != 'approved':
            return 'Identity review evidence unavailable; approve catalog review and CRM merchandising'
    members = family_products(product)
    for member in members:
        if any(row.get('Priority') == 'P0' for row in evidence['by_product'].get(str(member.pk), [])):
            return 'Unresolved P0 identity review'
    card = product_card(product)
    if not card['choices'] or not card['selected']['available']:
        return 'Blocked from purchase'
    if not require_image:
        return ''
    if not card['selected']['image']:
        return 'Missing exact-pack image'
    selected = card['selected']['variant']
    from .pack_images import pack_photos
    photos = pack_photos(selected) if selected else list(product.images.all())
    if not photos or photos[0].check_error:
        return 'Missing exact-pack image'
    if photos[0].image and not photos[0].checked_at:
        return 'Missing exact-pack image'
    if not photos[0].image and not photos[0].source_url.startswith('https://'):
        return 'Missing exact-pack image'
    return ''


def curated(products, limit=None, *, require_image=True):
    limit = limit or max(1, min(20, int(getattr(settings, 'HOMEPAGE_MERCHANDISING_LIMIT', 12))))
    evidence = snapshot()
    result = []
    candidates = products.filter(merchandising_active=True).order_by('merchandising_rank', 'name', 'pk')
    # Fetch ranked pages rather than loading thousands of flagged records at once.
    for start in range(0, candidates.count(), 48):
        for product in candidates[start:start + 48]:
            if not eligibility(product, evidence, require_image=require_image):
                result.append(product)
                if len(result) == limit:
                    return result
    return result

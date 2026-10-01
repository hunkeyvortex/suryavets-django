"""Review-only catalog decisions. Never changes publication, money, stock or orders."""
import hashlib
import json
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from shop.models import Product, ProductVariant, ProductImage, CatalogReviewEvent, InventoryMovement
from .crm import require_staff

SALT = 'surya.catalog-review.v1'


def snapshot(product, *, stock=False):
    fields = ['name', 'sku', 'category_id', 'brand_id', 'product_type_id', 'variant_family_id',
              'family_name', 'base_price', 'selling_price', 'discount_percentage',
              'track_inventory', 'is_active', 'requires_prescription', 'description',
              'short_description', 'ingredients', 'nutrition_information', 'nutrition_reviewed']
    pack_fields = ['id', 'name', 'sku', 'price_override', 'selling_price', 'discount_percentage',
                   'quantity', 'unit', 'attributes', 'image_id', 'is_active']
    if stock:
        fields.append('stock_quantity')
        pack_fields.append('stock_quantity')
    data = {
        'product': Product.objects.values(*fields).get(pk=product.pk),
        'packs': list(ProductVariant.objects.filter(product_id=product.pk).order_by('pk').values(*pack_fields)),
        'images': list(ProductImage.all_objects.filter(product_id=product.pk).order_by('pk').values(
            'id', 'image', 'source_url', 'is_active', 'check_error')),
    }
    if stock:
        data['last_movement'] = InventoryMovement.objects.filter(product_id=product.pk).order_by('-pk').values_list('pk', flat=True).first()
    return json.loads(json.dumps(data, default=str, sort_keys=True))


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def status(product):
    if not product.catalog_approved_digest:
        return 'Needs review'
    return 'Reviewed' if product.catalog_approved_digest == digest(snapshot(product)) else 'Changed — review again'


def issues(product):
    problems = []
    if not product.is_active:
        problems.append('Restore the product before approving its review.')
    packs = list(product.variants.filter(is_active=True))
    if not packs and product.variants.exists():
        problems.append('There are no active packs.')
    if not packs and not product.track_inventory:
        problems.append('Enable tracked inventory for this simple product.')
    photos = {p.pk: p for p in product.images.all() if (p.image or p.source_url.startswith('https://')) and not p.check_error}
    for item in packs or [product]:
        label = item.name
        if not item.sku.strip():
            problems.append(f'{label}: an exact SKU is required.')
        if item.current_price <= 0 or item.original_price < item.current_price:
            problems.append(f'{label}: a positive selling price not exceeding MRP is required.')
        if item.stock_quantity < 0:
            problems.append(f'{label}: stock cannot be negative.')
        photo = photos.get(item.image_id) if packs else next(iter(photos.values()), None)
        if not photo and len(packs) == 1:
            photo = next(iter(photos.values()), None)
        if not photo:
            problems.append(f'{label}: supply an active exact-product image; assign each pack image for multi-pack products.')
        elif photo.image:
            try:
                exists = photo.image.storage.exists(photo.image.name)
            except (OSError, ConnectionError):
                exists = False
            if not exists:
                problems.append(f'{label}: the image file could not be verified in storage.')
    return problems


def review_token(user, product):
    return signing.dumps({'user': user.pk, 'product': str(product.pk), 'snapshot': digest(snapshot(product, stock=True)),
                          'decision_count': product.catalog_reviews.count()}, salt=SALT)


@transaction.atomic
def decide(user, product_id, token, decision, evidence, *, identity=False, prices=False, inventory=False):
    require_staff(user, 'approve_catalog')
    product = Product.objects.select_for_update().get(pk=product_id)
    list(ProductVariant.objects.select_for_update().filter(product=product).order_by('pk'))
    list(ProductImage.all_objects.select_for_update().filter(product=product).order_by('pk'))
    current = snapshot(product, stock=True)
    try:
        payload = signing.loads(token, salt=SALT, max_age=1800)
        if payload != {'user': user.pk, 'product': str(product.pk), 'snapshot': digest(current),
                       'decision_count': product.catalog_reviews.count()}:
            raise ValueError
    except (signing.BadSignature, ValueError, TypeError):
        raise ValidationError('The product, stock or review changed. Reload and verify the latest details.')
    if decision not in ('approved', 'held') or not isinstance(evidence, str) or not 15 <= len(evidence.strip()) <= 2000:
        raise ValidationError('Provide a review decision and a meaningful source/count reference.')
    if decision == 'approved':
        if not all(value is True for value in (identity, prices, inventory)):
            raise ValidationError('Confirm exact identity/images, source prices and current stock before approval.')
        problems = issues(product)
        if problems:
            raise ValidationError(problems)
    approved_digest = digest(snapshot(product)) if decision == 'approved' else ''
    Product.objects.filter(pk=product.pk).update(catalog_approved_digest=approved_digest)
    current['attestations'] = {'identity': identity, 'prices': prices, 'inventory': inventory}
    return CatalogReviewEvent.objects.create(product=product, actor=user, decision=decision,
        digest=approved_digest, evidence=evidence.strip(), snapshot=current)

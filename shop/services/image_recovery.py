"""Offline trusted-source indexing. No fuzzy image assignment or request-time file scans."""
import hashlib
import io
import csv
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from django.core.files.storage import FileSystemStorage
from PIL import Image
from django.conf import settings
from shop.models import Product, ProductImage
from .pack_identity import source_index, normalized, measurements
from .product_media import image_identity, allowed_image_url
from .pack_review_snapshot import snapshot
from shop.management.commands.import_shopify_products import option_name

HEADERS = ['Product ID', 'Product Name', 'Canonical Family', 'Variant ID', 'Variant Name', 'SKU',
    'Shopify Handle', 'Current Image', 'Candidate Image', 'Candidate Source', 'Confidence',
    'Match Reason', 'Exact Pack Match', 'Family Fallback', 'Recommended Action']


def validate_file(field):
    if not field or not field.name:
        return {'valid': False, 'error': 'No local file'}
    try:
        if Path(field.name).suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            raise ValueError('Unsupported image extension')
        if not field.storage.exists(field.name):
            return {'valid': False, 'error': 'File missing'}
        with field.storage.open(field.name, 'rb') as stream:
            data = stream.read(20 * 1024 * 1024 + 1)
        if not data or len(data) > 20 * 1024 * 1024:
            raise ValueError('Empty or oversized image')
        with Image.open(io.BytesIO(data)) as picture:
            if picture.format not in ('JPEG', 'PNG', 'WEBP', 'GIF') or min(picture.size) < 16 or picture.width * picture.height > 20000000:
                raise ValueError('Unsupported format or unreasonable dimensions')
            width, height = picture.size
            picture.verify()
        return {'valid': True, 'sha256': hashlib.sha256(data).hexdigest(), 'width': width, 'height': height,
                'bytes': len(data), 'url': field.url, 'error': ''}
    except Exception as exc:
        return {'valid': False, 'error': str(exc)[:180]}


def build_index(sources=()):
    groups, provenance = source_index(sources)
    products = list(Product.objects.select_related('brand').prefetch_related('variants').order_by('pk'))
    by_id = {p.pk: p for p in products}
    photos = list(ProductImage.all_objects.order_by('pk'))
    by_product = defaultdict(list)
    validation, index, file_hashes = {}, [], defaultdict(list)
    evidence = snapshot()['by_product']
    p0 = {pk for pk, rows in evidence.items() if any(row.get('Priority') == 'P0' for row in rows)}
    for photo in photos:
        product = by_id[photo.product_id]
        check = validate_file(photo.image)
        thumb = validate_file(photo.thumbnail) if photo.thumbnail else None
        validation[photo.pk] = {'image': check, 'thumbnail': thumb, 'image_name': photo.image.name, 'thumbnail_name': photo.thumbnail.name}
        by_product[photo.product_id].append(photo)
        if check.get('sha256'):
            file_hashes[check['sha256']].append(photo)
        index.append({'image_id': photo.pk, 'path': photo.image.name, 'source_url': photo.source_url,
            'filename': Path(photo.image.name).name, 'product_id': str(product.pk), 'handle': product.slug,
            'product_title': product.name, 'brand': product.brand.name if product.brand else '',
            'variants': [{'id': v.pk, 'sku': v.sku, 'title': v.name, 'assigned': v.image_id == photo.pk} for v in product.variants.all()],
            'active': photo.is_active, 'file': check, 'thumbnail_file': thumb,
            'family_reference_for': str(photo.family_reference_for_id or ''),
            'candidate_assignment': '', 'shopify_product_id': '', 'shopify_variant_id': ''})

    def usable(photo):
        return photo.is_active and not photo.check_error and validation[photo.pk]['image']['valid']

    coverage = {'products': len(products), 'canonical_families': len({p.variant_family_id or p.pk for p in products})}
    covered, family_covered, exact_covered, explicit = set(), set(), set(), set()
    rows, plans = [], []
    counts = Counter(scanned=0, exact_matches=0, family_fallbacks=0, ambiguous=0, missing=0, existing=0, failed=0)
    for product in products:
        owned = by_product[product.pk]
        valid = [p for p in owned if usable(p)]
        variants = list(product.variants.all())
        root = product.variant_family_id or product.pk
        if valid:
            covered.add(product.pk); family_covered.add(root)
        source = groups.get(product.slug, [])
        primary = next((r for r in source if r.get('Title')), {})
        product_match = normalized(primary.get('Title')) == normalized(product.name) and normalized(primary.get('Vendor')) == normalized(product.brand.name if product.brand else '')
        source_variants = {(option_name(r), (r.get('Variant SKU') or '').strip()) for r in source if r.get('Option1 Value') or r.get('Variant SKU')}
        for variant in variants or [None]:
            counts['scanned'] += 1
            selected = next((p for p in valid if variant and p.pk == variant.image_id), None)
            if not selected and (not variant or (not variant.image_id and len(variants) == 1)):
                selected = next((p for p in valid if not p.family_reference_for_id), None)
            if selected and variant:
                exact_covered.add(variant.pk)
                if variant.image_id == selected.pk:
                    explicit.add(variant.pk)
            state, confidence, reason, url = 'missing', 'LOW', 'No trusted source artwork available.', ''
            candidate = None
            if selected:
                state, confidence, reason = 'existing', 'HIGH', 'Existing source-owned mapping and validated file; preserve assignment.'
            elif str(product.pk) in p0:
                state, confidence, reason = 'ambiguous', 'LOW', 'Critical pack identity discrepancy; never auto-assign.'
            elif variant and variant.image_id:
                state, confidence, reason = 'ambiguous', 'LOW', 'Existing explicit assignment is missing, invalid or foreign; staff review required.'
            elif variant and product_match:
                matched = [r for r in source if variant.sku and (r.get('Variant SKU') or '').strip() == variant.sku and normalized(option_name(r)) == normalized(variant.name)]
                urls = {image_identity(r.get('Variant Image') or '') for r in matched if r.get('Variant Image')}
                if not urls and len(source_variants) == 1 and matched:
                    urls = {image_identity(r.get('Image Src') or '') for r in source if r.get('Image Src')}
                if len(urls) == 1:
                    url = next(iter(urls))
                    existing = [p for p in owned if image_identity(p.source_url) == url]
                    pack = measurements(variant.name)
                    url_pack = measurements(url)
                    if not allowed_image_url(url) or any(not p.is_active or p.check_error for p in existing) or (pack and url_pack and pack != url_pack):
                        state, confidence, reason = 'ambiguous', 'MEDIUM', 'Source mapping has a rejected image, unapproved URL, or conflicting pack clue.'
                    else:
                        state, confidence, reason = 'exact_matches', 'HIGH', 'Exact handle, title/vendor, SKU and option identity; unique source image.'
                        candidate = {'product_id': str(product.pk), 'variant_id': variant.pk, 'url': url,
                            'product_name': product.name, 'sku': variant.sku, 'variant_name': variant.name,
                            'photo_id': existing[0].pk if len(existing) == 1 else None,
                            'confidence': 'HIGH'}
                        if len(existing) > 1:
                            candidate = None
                            state, confidence, reason = 'ambiguous', 'MEDIUM', 'Duplicate existing image relationships need review.'
                elif urls or owned or any(r.get('Image Src') or r.get('Variant Image') for r in source):
                    state, confidence, reason = 'ambiguous', 'MEDIUM', 'Artwork exists but exact pack relationship is not unique.'
            approved = [p for p in photos if p.family_reference_for_id == root and p.family_reference_note and usable(p) and (by_id[p.product_id].variant_family_id or p.product_id) == root] if not selected else []
            if state == 'missing' and approved:
                state, confidence, reason = 'family_fallbacks', 'MEDIUM', 'Staff-approved family reference only; not an exact pack.'
                url = approved[0].image.url
            counts[state] += 1
            if candidate:
                plans.append(candidate)
            if selected and str(product.pk) in p0:
                confidence, reason = 'LOW', 'Existing artwork has recorded critical pack discrepancy; unchanged and requires review.'
            rows.append([str(product.pk), product.name, str(root), str(variant.pk) if variant else '',
                variant.name if variant else '', variant.sku if variant else product.sku, product.slug,
                selected.image.url if selected else '', url, 'Shopify export' if url and not approved else ('Staff approval' if approved else ''),
                confidence, reason, 'YES' if (selected or candidate) and confidence == 'HIGH' else 'NO', 'YES' if approved else 'NO',
                'PRESERVE / REVIEW' if selected and confidence == 'LOW' else ('PRESERVE' if selected else ('RECOVER' if candidate else 'REVIEW / PLACEHOLDER'))])
    coverage.update(products_with_images=len(covered), products_missing_images=len(products)-len(covered),
        families_covered=len(family_covered), exact_variant_images=len(exact_covered), explicit_variant_images=len(explicit))
    # File-only assets stay unassigned: a filename is not identity evidence.
    referenced = {str((Path(settings.MEDIA_ROOT)/p.image.name).resolve()) for p in photos if p.image}
    unassigned = []
    for folder in (Path(settings.MEDIA_ROOT), Path(settings.BASE_DIR)/'catalog_exports'/'images'):
        if folder.exists():
            for path in folder.rglob('*'):
                if path.is_file() and 'thumbnails' not in path.parts and str(path.resolve()) not in referenced:
                    unassigned.append({'path': str(path), 'bytes': path.stat().st_size, 'confidence': 'LOW',
                        'validation': validate_file(SimpleNamespace(storage=FileSystemStorage(location=path.parent),name=path.name,url='')),
                        'reason': 'No deterministic assignment; never match by filename alone.'})
    duplicates = [{'sha256': digest, 'image_ids': [p.pk for p in group],
        'cross_family': len({by_id[p.product_id].variant_family_id or p.product_id for p in group}) > 1,
        'reason': 'Shared bytes are not proof of incorrect identity; no automatic reassignment.'}
        for digest, group in file_hashes.items() if len(group) > 1]
    source_images = []
    for handle, records in groups.items():
        for row in records:
            for field in ('Image Src', 'Variant Image'):
                if row.get(field):
                    source_images.append({'handle': handle, 'url': row[field], 'role': field, 'sku': row.get('Variant SKU', ''),
                        'variant_title': option_name(row), 'product_title': row.get('Title', ''), 'vendor': row.get('Vendor', ''),
                        'shopify_product_id': row.get('Product ID', ''), 'shopify_variant_id': row.get('Variant ID', ''), 'evidence': row.get('_evidence', '')})
    historical = []
    for path in (Path(settings.BASE_DIR)/'catalog_review').rglob('variant_pack_review.csv'):
        if not path.is_file():
            continue
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                artwork = row.get('Variant Image') or row.get('Product Image') or ''
                if artwork:
                    historical.append({'file': str(path), 'product_id': row.get('Product ID',''),
                        'variant_id': row.get('Variant ID',''), 'sku':row.get('SKU',''), 'handle':row.get('Shopify Handle',''),
                        'image':artwork,'confidence':'MEDIUM','reason':'Historical audit evidence, not new approval. Never restore a rejected assignment automatically.'})
    counts['invalid_local_files'] = sum(not v['image']['valid'] for v in validation.values())
    return {'headers': HEADERS, 'rows': rows, 'plans': plans, 'counts': dict(counts), 'coverage': coverage, 'source_images': source_images,
        'index': index, 'unassigned_files': unassigned, 'duplicates': duplicates, 'sources': provenance, 'historical_references': historical,
        'validation': validation}

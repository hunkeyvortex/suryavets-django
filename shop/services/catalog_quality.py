"""Read-only catalog diagnostics. Findings are not approvals or data corrections."""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.utils.html import strip_tags
from PIL import Image

from shop.models import Product, ProductVariant, ProductImage, InventoryMovement, Order, OrderItem, CatalogReviewEvent, Category, Brand
from shop.management.commands.import_shopify_products import Command as ShopifyReader, option_name
from .catalog_approval import status as approval_status
from .pack_families import pack_quantity
from .pricing import export_prices
from .product_media import image_identity


HEADERS = ['Product ID', 'Product Name', 'Slug', 'Shopify Handle', 'Brand/Vendor', 'Category',
    'Canonical Family', 'Family ID', 'Variant ID', 'Variant Display Name', 'Pack Size', 'SKU',
    'MRP', 'Selling Price', 'Discount %', 'Stock', 'Active', 'Publishable', 'Review Status',
    'Primary Image', 'Image Count', 'Variant Image', 'Missing Image', 'Zero Price', 'Blank SKU',
    'Suspicious Stock', 'Best Seller', 'Featured', 'Needs Review', 'Review Reason',
    'Missing Primary Image', 'Missing Variant Image', 'Image Issues', 'Family Image Available',
    'Source Match', 'Source Title', 'Source Options', 'Source SKU', 'Source Price', 'Source MRP',
    'Source Image', 'Source Inventory Snapshot', 'Pack Issues', 'Ledger Count', 'Ledger Opening Observed',
    'Ledger Net Change', 'Ledger Derived Stock', 'Ledger Last Stock', 'Ledger Issues', 'Stock Issues',
    'Description Status', 'Specialist Review', 'Recommended Action', 'Owner Decision', 'Owner Evidence']


def select_only(execute, sql, params, many, context):
    if not sql.lstrip().upper().startswith(('SELECT ', 'EXPLAIN ')):
        raise RuntimeError('Catalog audit blocked a non-read-only database statement.')
    return execute(sql, params, many, context)


def fingerprint():
    """Hash all business rows, not just counts. Never output private row values."""
    result = {}
    for model in (Product, ProductVariant, ProductImage, Category, Brand, InventoryMovement, Order, OrderItem, CatalogReviewEvent,
                  Product.collections.through, Product.pet_categories.through):
        rows = list(model._base_manager.order_by('pk').values())
        result[model._meta.label] = {'rows': len(rows), 'sha256': hashlib.sha256(
            json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()}
    return result


def normalize(text):
    return ' '.join(re.sub(r'[^\w]+', ' ', text.casefold()).split())


def packed(text):
    """Possible quantities only; product titles can describe animal weights/doses."""
    found = set()
    for amount, unit in re.findall(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(kg|gm|g|ml|ltr|l)\b', text, re.I):
        parsed = pack_quantity(amount + unit)
        if parsed:
            quantity, unit = parsed
            found.add(('mass' if unit in ('g', 'kg') else 'volume', quantity * (1000 if unit in ('kg', 'L') else 1)))
    return found


def sources(paths, inventory=None):
    groups = dict(ShopifyReader()._product_groups(paths)) if paths else {}
    stock = defaultdict(list)
    if inventory:
        with Path(inventory).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            identity = {'Handle', 'Title', 'SKU', 'HS Code', 'COO', *(f'Option{i} {kind}' for i in range(1, 4) for kind in ('Name', 'Value'))}
            columns = [key for key in reader.fieldnames if key not in identity]
            for row in reader:
                stock[(row.get('Handle', '').strip(), option_name(row), row.get('SKU', '').strip())].append(
                    '; '.join(f'{key}={row.get(key, "")}' for key in columns))
    provenance = [{'file': str(Path(path).resolve()), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                  for path in [*paths, *([inventory] if inventory else [])]]
    return groups, stock, provenance


def inspect_photo(photo, cache):
    key = (photo.image.name, photo.thumbnail.name, photo.source_url, photo.is_active, photo.check_error)
    if key in cache:
        return cache[key]
    issues, usable = [], False
    if not photo.is_active:
        issues.append('Inactive image')
    if photo.check_error:
        issues.append('Recorded media check failure: ' + photo.check_error)
    if photo.image:
        if isinstance(photo.image.storage, FileSystemStorage):
            try:
                path = Path(photo.image.path)
                if not path.is_file():
                    issues.append('Missing local original')
                else:
                    with Image.open(path) as img:
                        img.verify()
                    usable = True
                if photo.thumbnail and not Path(photo.thumbnail.path).is_file():
                    issues.append('Missing local thumbnail')
            except (OSError, ValueError, Image.DecompressionBombError):
                issues.append('Unreadable local image')
        else:
            issues.append('External storage availability unverified')
    elif photo.source_url.startswith('https://'):
        issues.append('Remote image not fetched; availability unverified')
    else:
        issues.append('No usable image reference')
    result = (usable and photo.is_active and not photo.check_error, issues)
    cache[key] = result
    return result


def build_report(source_paths=(), inventory=None):
    groups, stock_source, provenance = sources(source_paths, inventory)
    products = list(Product.objects.select_related('category', 'brand', 'product_type').prefetch_related('variants').order_by('pk'))
    by_id = {p.pk: p for p in products}
    family_members = defaultdict(set)
    for p in products:
        family_members[p.variant_family_id or p.pk].add(p.pk)
    variants = [v for p in products for v in p.variants.all()]
    photos = list(ProductImage.all_objects.order_by('order', '-is_primary', 'pk'))
    photos_by_product, photos_by_id, reference_owners = defaultdict(list), {}, defaultdict(set)
    photo_cache, checked = {}, {}
    for photo in photos:
        photos_by_product[photo.product_id].append(photo)
        photos_by_id[photo.pk] = photo
        checked[photo.pk] = inspect_photo(photo, photo_cache)
        for ref in [photo.image.name, image_identity(photo.source_url) if photo.source_url else '']:
            if ref:
                reference_owners[ref].add(photo.product_id)
    movements = defaultdict(list)
    for movement in InventoryMovement.objects.order_by('created_at', 'pk'):
        movements[(movement.product_id, movement.variant_id)].append(movement)
    quantity_counts = Counter(v.stock_quantity for v in variants)
    common = {n for n, count in quantity_counts.items() if count >= max(20, len(variants) * .1)}
    sku_packs = defaultdict(set)
    for v in variants:
        if v.sku.strip():
            sku_packs[v.sku.strip()].add((normalize(v.name), str(v.quantity), v.unit))
    rows = []
    for p in products:
        packs = list(p.variants.all())
        family = by_id.get(p.variant_family_id, p)
        family_ids = family_members[family.pk] | {family.pk}
        family_photo = any(checked[photo.pk][0] for fid in family_ids for photo in photos_by_product[fid])
        source_rows = groups.get(p.slug, [])
        source_title = next((r.get('Title', '') for r in source_rows if r.get('Title')), '')
        review = approval_status(p) if p.catalog_approved_digest else 'Needs review'
        active_photos = [i for i in photos_by_product[p.pk] if i.is_active]
        primary = active_photos[0] if active_photos else None
        ref_counts = Counter(image_identity(i.source_url) if i.source_url else i.image.name for i in active_photos)
        for v in packs or [None]:
            item = v or p
            image_problems = [problem for image in active_photos for problem in checked[image.pk][1]]
            variant_photo = photos_by_id.get(v.image_id) if v else None
            if variant_photo and variant_photo.product_id != p.pk:
                image_problems.append('Variant image belongs to another product; verify exact pack')
            if variant_photo and not checked[variant_photo.pk][0]:
                image_problems.extend(checked[variant_photo.pk][1])
            if any(ref and count > 1 for ref, count in ref_counts.items()):
                image_problems.append('Duplicate image references within product')
            if any(len(reference_owners[ref]) > 1 for image in active_photos for ref in
                   [image.image.name, image_identity(image.source_url) if image.source_url else ''] if ref):
                image_problems.append('Image reference shared by multiple source products; verify pack')
            exact_photo = variant_photo if v else primary
            if v and not variant_photo and len(packs) == 1:
                exact_photo = primary  # existing single-pack fallback, not an approval
            missing_image = not exact_photo or not checked[exact_photo.pk][0] or exact_photo.product_id != p.pk
            missing_primary = not primary or not checked[primary.pk][0]
            missing_variant = bool(v and (not variant_photo or not checked[variant_photo.pk][0] or variant_photo.product_id != p.pk))
            pack_issues, ledger_issues, stock_issues = [], [], []
            exact_rows = [r for r in source_rows if option_name(r) == (v.name if v else 'Default Title') and
                          (r.get('Variant Price') or r.get('Variant SKU') or option_name(r) != 'Default Title')]
            source_candidates = {(r.get('Variant SKU', ''), r.get('Variant Price', ''), r.get('Variant Compare At Price', ''),
                                  r.get('Variant Image', ''), *(r.get(f'Option{i} Value', '') for i in range(1, 4))) for r in exact_rows}
            source = exact_rows[0] if len(source_candidates) == 1 else None
            match = 'Exact handle/options/SKU' if source and source.get('Variant SKU', '').strip() == item.sku.strip() else (
                'SKU differs' if source else 'Ambiguous source rows' if len(source_candidates) > 1 else 'No exact source option match')
            if match != 'Exact handle/options/SKU':
                pack_issues.append(match)
            if v:
                option_pack = packed(v.name)
                for label, text in [('title', p.name), ('handle', p.slug.replace('-', ' '))]:
                    possible = packed(text)
                    if possible and option_pack and possible.isdisjoint(option_pack):
                        pack_issues.append(f'Possible {label}/option quantity conflict (may describe animal weight/dose)')
                if bool(v.quantity) != bool(v.unit):
                    pack_issues.append('Incomplete normalized pack quantity/unit')
                if v.quantity and v.unit and option_pack and packed(f'{v.quantity}{v.unit}') != option_pack:
                    pack_issues.append('Normalized quantity differs from exact option')
                if not v.quantity or not v.unit:
                    pack_issues.append('Net pack quantity/unit unverified; do not claim unit savings')
                if v.sku.strip() and len(sku_packs[v.sku.strip()]) > 1:
                    pack_issues.append('Same SKU used for conflicting pack identities')
            if family.pk != p.pk and (family.variant_family_id or family.pk == p.variant_family_id == p.pk):
                pack_issues.append('Nested/cyclic family link requires review')
            if family.pk != p.pk and (family.brand_id != p.brand_id or normalize(family.name) != normalize(p.name)):
                pack_issues.append('Family naming/brand differs; verify existing grouping')
            source_price, source_mrp = '', ''
            if source:
                try:
                    source_mrp, source_price, _ = export_prices(source)
                except ValueError:
                    pack_issues.append('Source price missing/invalid')
            history = movements[(p.pk, v.pk if v else None)]
            derived = history[0].quantity_before + sum(m.delta for m in history) if history else None
            if not history:
                ledger_issues.append('No ledger observation; opening stock not verified')
            else:
                if any(a.quantity_after != b.quantity_before for a, b in zip(history, history[1:])):
                    ledger_issues.append('Ledger chain discontinuity')
                if history[-1].quantity_after != item.stock_quantity or derived != item.stock_quantity:
                    ledger_issues.append('Current stock differs from ledger-derived balance')
                if any(m.quantity_before + m.delta != m.quantity_after for m in history):
                    ledger_issues.append('Invalid ledger arithmetic')
            if item.stock_quantity is None: stock_issues.append('Missing stock')
            elif item.stock_quantity < 0: stock_issues.append('Negative stock')
            elif item.stock_quantity == 0: stock_issues.append('Zero stock; availability review, not proof of error')
            if item.stock_quantity == 10: stock_issues.append('Stock=10; known development-default risk')
            if item.stock_quantity in common: stock_issues.append(f'Quantity shared by {quantity_counts[item.stock_quantity]} variants')
            if any(re.search(r'\b(test|development|default|set.catalog.stock)\b', m.reason, re.I) for m in history):
                stock_issues.append('Development/test/default language in ledger reason')
            stock_issues.extend(ledger_issues)
            if packs and p.stock_quantity != sum(pack.stock_quantity for pack in packs if pack.is_active):
                stock_issues.append('Source product stock total differs from active pack sum')
            context = ' '.join([p.name, p.category.name, p.product_type.name if p.product_type else '', *p.shopify_tags]).lower()
            specialist = []
            if p.requires_prescription: specialist.append('Prescription flag already set; owner verification required')
            if any(word in context for word in ('medicine', 'antibiotic', 'injectable', 'vaccine', 'vaccination')):
                specialist.append('Specialist handling/prescription/shipping policy review; keyword signal only')
            if any(word in context for word in ('vaccine', 'vaccination', 'cold chain', 'cold-chain')):
                specialist.append('Confirm whether cold-chain applies; no rule inferred')
            active = p.is_active and (not v or v.is_active) and family.is_active
            reasons = []
            if not active: reasons.append('Inactive product/pack/family')
            if item.current_price <= 0: reasons.append('Nonpositive selling price')
            if item.original_price < item.current_price: reasons.append('Selling price exceeds MRP')
            if not item.sku.strip(): reasons.append('Blank SKU')
            if missing_image: reasons.append('Exact-pack usable image not verified')
            if not p.category.is_active: reasons.append('Inactive category')
            if review != 'Reviewed': reasons.append('Catalog identity/prices/stock not approved or approval stale')
            if not strip_tags(p.description).strip(): reasons.append('CONTENT REQUIRED')
            if source_price != '' and source_price != item.current_price: reasons.append('Current/source selling price differs; review age and edits')
            reasons.extend(pack_issues + stock_issues + specialist)
            rows.append(dict(zip(HEADERS, [str(p.pk), p.name, p.slug, p.slug if source_rows else '',
                p.brand.name if p.brand else p.manufacturer, p.category.name, family.family_name or family.name, str(family.pk),
                v.pk if v else '', v.name if v else '', f'{v.quantity} {v.unit}' if v and v.quantity and v.unit else '', item.sku,
                item.original_price, item.current_price, (Decimal(100)*(item.original_price-item.current_price)/item.original_price).quantize(Decimal('.01')) if item.original_price > 0 else '',
                item.stock_quantity, active, 'REVIEW REQUIRED' if reasons else 'REVIEWED CANDIDATE (not launch approval)', review,
                primary.image.name or primary.source_url if primary else '', len(active_photos),
                variant_photo.image.name or variant_photo.source_url if variant_photo else '', missing_image, item.current_price <= 0,
                not bool(item.sku.strip()), bool(stock_issues), p.is_bestseller, p.is_featured, bool(reasons), '; '.join(dict.fromkeys(reasons)),
                missing_primary, missing_variant, '; '.join(dict.fromkeys(image_problems)), family_photo, match, source_title,
                ' / '.join(source.get(f'Option{i} Value', '') for i in range(1,4) if source.get(f'Option{i} Value')) if source else '',
                source.get('Variant SKU', '') if source else '', source_price, source_mrp, source.get('Variant Image', '') if source else '',
                ' | '.join(stock_source.get((p.slug, v.name if v else 'Default Title', item.sku), [])), '; '.join(pack_issues), len(history),
                history[0].quantity_before if history else '', sum(m.delta for m in history) if history else '',
                derived if derived is not None else '', history[-1].quantity_after if history else '', '; '.join(ledger_issues), '; '.join(stock_issues),
                'Present' if strip_tags(p.description).strip() else 'CONTENT REQUIRED', '; '.join(specialist),
                'Verify exact source identity, current prices, images and dated physical stock; use CRM review. Do not auto-correct.' if reasons else 'Owner launch review required', '', ''])))
    buckets = defaultdict(list)
    for row in rows:
        if row['SKU'].strip(): buckets[('Exact SKU', row['SKU'].strip())].append(row)
        buckets[('Normalized name + brand + pack', normalize(row['Product Name']) + '|' + normalize(row['Brand/Vendor']) + '|' + normalize(row['Variant Display Name']))].append(row)
        buckets[('Same name + brand, possible pack family', normalize(row['Product Name']) + '|' + normalize(row['Brand/Vendor']))].append(row)
    duplicates = []
    for (signal, key), members in sorted(buckets.items()):
        if len({(r['Product ID'], r['Variant ID']) for r in members}) < 2: continue
        duplicates.append({'Signal': signal, 'Matching Value': key, 'Confidence': 'Exact shared identifier; verify identity' if signal == 'Exact SKU' else 'Candidate only; not a confirmed duplicate',
            'Product IDs': ' | '.join(sorted({r['Product ID'] for r in members})), 'Variant IDs': ' | '.join(str(r['Variant ID']) for r in members),
            'Products': ' | '.join(sorted({r['Product Name'] for r in members})), 'SKUs': ' | '.join(sorted({r['SKU'] for r in members})),
            'Packs': ' | '.join(sorted({r['Variant Display Name'] for r in members})), 'Already Same Family': len({r['Family ID'] for r in members}) == 1,
            'Recommended Action': 'Review source evidence; do not automatically merge', 'Owner Decision': '', 'Owner Evidence': ''})
    by_family = defaultdict(list)
    for row in rows: by_family[row['Family ID']].append(row)
    best = []
    sales = Counter()
    for item in OrderItem.objects.select_related('order').filter(order__payment_status='paid').exclude(order__status='cancelled'):
        if item.product_id: sales[str(by_id[item.product_id].variant_family_id or item.product_id)] += item.quantity
    for p in products:
        if p.variant_family_id: continue
        members = by_family[str(p.pk)]
        best.append({'Product ID': str(p.pk), 'Product': p.name, 'Family': p.family_name or p.name,
            'Variant Count': sum(bool(r['Variant ID']) for r in members), 'Current Best Seller Flag': p.is_bestseller,
            'Sales Evidence Available?': 'Local paid-order units only; may be test orders, not verified Shopify history',
            'Local Paid Units': sales[str(p.pk)], 'Featured?': p.is_featured,
            'Image Available?': any(not r['Missing Image'] for r in members), 'Price Valid?': any(r['Selling Price'] > 0 and r['MRP'] >= r['Selling Price'] for r in members),
            'Stock Valid?': 'Owner confirmation required', 'Recommended Status': 'Manual curation required; do not infer best seller from import flag',
            'Owner Decision': '', 'Owner Rank': '', 'Owner Evidence': ''})
    reports = {'catalog_master_review.csv': rows,
        'zero_price_variants.csv': [r for r in rows if r['Variant ID'] and r['Zero Price']],
        'blank_sku_variants.csv': [r for r in rows if r['Variant ID'] and r['Blank SKU']],
        'missing_images.csv': [r for r in rows if r['Missing Image'] or r['Missing Primary Image'] or r['Missing Variant Image'] or r['Image Issues']],
        'suspicious_stock.csv': [r for r in rows if r['Suspicious Stock']],
        'duplicate_or_similar_products.csv': duplicates,
        'variant_pack_review.csv': [r for r in rows if r['Pack Issues']],
        'unpublished_recommendations.csv': [r for r in rows if r['Needs Review']], 'best_seller_review.csv': best}
    counts = {'total_products': len(products), 'canonical_listings': sum(not p.variant_family_id for p in products),
        'total_variants': len(variants), 'zero_price_variants': len(reports['zero_price_variants.csv']),
        'active_in_stock_zero_price_variants': sum(r['Active'] and r['Stock'] > 0 for r in reports['zero_price_variants.csv']),
        'blank_sku_variants': len(reports['blank_sku_variants.csv']),
        'products_without_verified_usable_image': sum(not any(checked[i.pk][0] for i in photos_by_product[p.pk]) for p in products),
        'products_without_active_image_record': sum(not any(i.is_active for i in photos_by_product[p.pk]) for p in products),
        'suspicious_stock_variants': sum(bool(r['Variant ID']) for r in reports['suspicious_stock.csv']),
        'variants_at_stock_10': sum(v.stock_quantity == 10 for v in variants),
        'variants_with_ledger_balance_or_chain_issue': sum(bool(r['Variant ID']) and any(word in r['Ledger Issues'] for word in ('differs', 'discontinuity', 'arithmetic')) for r in rows),
        'duplicate_candidate_groups': len(duplicates), 'pack_review_rows': len(reports['variant_pack_review.csv']),
        'possible_pack_quantity_conflict_rows': sum('quantity conflict' in r['Pack Issues'] or 'differs from exact option' in r['Pack Issues'] for r in rows),
        'variants_without_normalized_quantity': sum(not v.quantity or not v.unit for v in variants),
        'best_seller_products_all': sum(p.is_bestseller for p in products),
        'best_seller_active_canonical': sum(p.is_bestseller and p.is_active and not p.variant_family_id for p in products),
        'approved_current_products': sum(approval_status(p) == 'Reviewed' for p in products if p.catalog_approved_digest),
        'source_handles': len(groups), 'inventory_source_identities': len(stock_source),
        'inventory_exact_matched_rows': sum(bool(r['Source Inventory Snapshot']) for r in rows),
        'blank_description_products': sum(not strip_tags(p.description).strip() for p in products),
        'specialist_review_products': len({r['Product ID'] for r in rows if r['Specialist Review']})}
    return reports, counts, provenance

"""Read-only identity evidence, not an import, approval or grouping engine."""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote, urlsplit

from shop.models import Product, ProductImage
from shop.management.commands.import_shopify_products import Command as SourceReader, option_name
from .product_media import image_identity

UNITS = {'kg': ('mass', Decimal(1000), 'kg'), 'g': ('mass', Decimal(1), 'g'), 'gm': ('mass', Decimal(1), 'g'),
         'ml': ('volume', Decimal(1), 'ml'), 'l': ('volume', Decimal(1000), 'L'), 'ltr': ('volume', Decimal(1000), 'L'),
         'mm': ('length', Decimal(1), 'mm'), 'cm': ('length', Decimal(10), 'cm'),
         'pcs': ('count', Decimal(1), 'count'), 'pc': ('count', Decimal(1), 'count'), 'count': ('count', Decimal(1), 'count')}
MEASURE = re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)\s*(kg|gm|ml|ltr|mm|cm|pcs|count|pc|g|l)(?![a-z])', re.I)
HEADERS = ['Product ID', 'Product Name', 'Shopify Handle', 'Canonical Family', 'Family ID', 'Brand/Vendor',
    'Variant ID', 'Variant Display Name', 'Parsed Pack Size', 'Parsed Unit', 'SKU', 'Slug', 'Product Image',
    'Variant Image', 'Family Member Count', 'Conflict Type', 'Priority', 'Confidence', 'Recommended Action',
    'Evidence Source', 'Evidence Detail', 'Review Status', 'Image Review', 'Source Match', 'Suspected Identity',
    'Visual Image Observation', 'Owner Decision', 'Owner Evidence']


def normalized(text):
    return ' '.join(str(text or '').casefold().split())


def measurements(text, *, slug=False):
    text = unquote(str(text or ''))
    # Strength expressions are not the bottle's net pack volume.
    text = re.sub(r'\d+(?:\.\d+)?\s*(?:mg|mcg|iu)\s*[/\-]\s*\d+(?:\.\d+)?\s*ml', '', text, flags=re.I)
    if slug:
        # Decimal slugs are an ambiguous clue, never authoritative net quantity.
        text = re.sub(r'(\d)-(\d+)(?=(?:kg|gm|ml|ltr|mm|cm|g|l)\b)', r'\1.\2', text, flags=re.I).replace('-', ' ')
    return {(UNITS[m[2].lower()][0], Decimal(m[1]) * UNITS[m[2].lower()][1]) for m in MEASURE.finditer(text)}


def exact_pack(text):
    match = MEASURE.fullmatch(str(text or '').strip())
    if not match or Decimal(match[1]) <= 0:
        return None
    return Decimal(match[1]), UNITS[match[2].lower()][2]


def title_identity(text):
    """Drop a terminal package measurement/size code only; retain formula words."""
    text = re.sub(r'\s*\((?:xxs|xs|s|m|l|xl|xxl|xxxl)\)\s*$', '', text, flags=re.I)
    text = re.sub(r'\s*\(?\d+(?:\.\d+)?\s*(?:kg|gm|ml|ltr|mm|cm|pcs|count|pc|g|l)\)?\s*$', '', text, flags=re.I)
    return normalized(text)


def source_index(paths):
    groups, provenance = defaultdict(list), []
    reader = SourceReader()
    for path in paths:
        path = Path(path)
        provenance.append({'file': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        stream, archive = reader._open_csv(path)
        member = next((p.filename for p in archive.infolist() if p.filename.lower().endswith('.csv')), '') if archive else ''
        try:
            rows = csv.DictReader(stream)
            if not {'Handle', 'Variant SKU'}.issubset(rows.fieldnames or []):
                raise ValueError('Expected a Shopify product export with Handle and Variant SKU.')
            for line, row in enumerate(rows, 2):
                handle = (row.get('Handle') or '').strip()
                if handle:
                    row['_evidence'] = f'{path.name}{":" + member if member else ""}: CSV record {line}'
                    groups[handle].append(row)
        finally:
            stream.close()
            if archive:
                archive.close()
    return groups, provenance


def build_identity_report(source_paths=(), image_observations=None):
    source, provenance = source_index(source_paths)
    observations = {}
    if image_observations:
        path = Path(image_observations)
        observations = {str(r['image_id']): r for r in json.loads(path.read_text(encoding='utf-8'))['observations']}
        provenance.append({'file': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    products = list(Product.objects.select_related('brand').prefetch_related('variants', 'pet_categories').order_by('pk'))
    by_id = {p.pk: p for p in products}
    members, names, sku_packs = defaultdict(list), defaultdict(list), defaultdict(list)
    photos = list(ProductImage.all_objects.order_by('order', '-is_primary', 'pk'))
    photo_by_id = {p.pk: p for p in photos}
    photos_by_product = defaultdict(list)
    for photo in photos:
        if photo.is_active:
            photos_by_product[photo.product_id].append(photo)
    latest_reviews = {}
    from shop.models import CatalogReviewEvent
    for event in CatalogReviewEvent.objects.order_by('created_at', 'pk'):
        latest_reviews[event.product_id] = event.decision
    for product in products:
        members[product.variant_family_id or product.pk].append(product)
        names[(product.brand_id, title_identity(product.name))].append(product)
        for variant in product.variants.all():
            if variant.sku.strip():
                sku_packs[variant.sku.strip()].append(variant)
    rows = []
    for product in products:
        root = by_id.get(product.variant_family_id, product)
        family = members[root.pk]
        packs = list(product.variants.all())
        source_rows = source.get(product.slug, [])
        source_titles = {r['Title'].strip() for r in source_rows if r.get('Title', '').strip()}
        source_vendors = {normalized(r['Vendor']) for r in source_rows if r.get('Vendor', '').strip()}
        pack_rows = [r for r in source_rows if r.get('Variant SKU') or r.get('Variant Price') or option_name(r) != 'Default Title']
        primary = next(iter(photos_by_product[product.pk]), None)
        identities = {title_identity(p.name) for p in family}
        brands = {p.brand_id for p in family}
        species = [{pet.pk for pet in p.pet_categories.all()} for p in family]
        disjoint_species = any(a and b and a.isdisjoint(b) for i, a in enumerate(species) for b in species[i + 1:])
        kinds = {p.product_type_id for p in family if p.product_type_id}
        prescription = {p.requires_prescription for p in family}
        family_packs = [v for p in family for v in p.variants.all()]
        dimensions = {dimension for v in family_packs for dimension, _ in measurements(v.name)}
        for variant in packs or [None]:
            issues = []
            def issue(code, priority, confidence, evidence, action):
                if not any(i['code'] == code for i in issues):
                    issues.append(dict(code=code, priority=priority, confidence=confidence, evidence=evidence, action=action))
            item_name = variant.name if variant else ''
            sku = (variant.sku if variant else product.sku).strip()
            parsed = exact_pack(item_name)
            measures = measurements(item_name)
            exact_sources = [r for r in pack_rows if option_name(r) == (item_name or 'Default Title') and (r.get('Variant SKU') or '').strip() == sku]
            signatures = {(option_name(r), (r.get('Variant SKU') or '').strip()) for r in exact_sources}
            source_match = 'Exact handle/options/SKU' if exact_sources and len(signatures) == 1 else 'Missing exact source match'
            if not exact_sources:
                issue('SOURCE_IDENTITY_UNCONFIRMED', 'P1', 'Low', f'No exact handle/options/SKU match for {product.slug} / {item_name} / {sku}.', 'Check original Shopify export and supplier identity; do not infer a handle or pack.')
            if len({title_identity(t) for t in source_titles}) > 1 or len(source_vendors) > 1:
                issue('HANDLE_MULTIPLE_IDENTITIES', 'P0', 'High', f'Source handle has titles={sorted(source_titles)}; vendors={sorted(source_vendors)}.', 'Resolve conflicting source snapshots before any grouping.')
            if source_titles and title_identity(product.name) not in {title_identity(t) for t in source_titles}:
                issue('SOURCE_TITLE_IDENTITY_DIFFERENCE', 'P1', 'Medium', f'Django title={product.name}; source titles={sorted(source_titles)}.', 'Confirm whether a deliberate rename or different formulation. Preserve title and slug.')
            if len(source_vendors) == 1 and product.brand and normalized(product.brand.name) not in source_vendors:
                issue('SOURCE_VENDOR_DIFFERENCE', 'P1', 'Medium', f'Current vendor={product.brand.name}; source={sorted(source_vendors)}.', 'Verify exact manufacturer/vendor; do not merge by similar title.')
            if variant and parsed:
                for code, text, is_slug in [('TITLE_VARIANT_MISMATCH', product.name, False), ('SLUG_VARIANT_MISMATCH', product.slug, True)]:
                    observed = measurements(text, slug=is_slug)
                    same_dimension = {m for m in observed if m[0] in {x[0] for x in measures}}
                    if same_dimension and not same_dimension.intersection(measures):
                        issue(code, 'P1', 'Low', f'{text!r} mentions {sorted(same_dimension)}; variant={item_name!r}.', 'Check package/source; numbers may be animal weight, dosage or a historical URL. No automatic correction.')
                if variant.quantity and variant.unit:
                    stored = measurements(f'{variant.quantity}{variant.unit}')
                    if stored and stored != measures:
                        issue('NORMALIZED_QUANTITY_CONFLICT', 'P0', 'High', f'Display={item_name}; normalized={variant.quantity} {variant.unit}.', 'Verify net quantity before using unit-price comparisons.')
                formatted = f'{parsed[0]:f}'.rstrip('0').rstrip('.') if '.' in f'{parsed[0]:f}' else f'{parsed[0]:f}'
                formatted += ' ' + parsed[1]
                if item_name != formatted:
                    issue('DISPLAY_FORMAT_ONLY', 'P2', 'High', f'Current label={item_name!r}; formatting candidate={formatted!r}.', 'Optional display formatting only, after identity conflicts are resolved. No database changes applied.')
            if sku:
                same_sku = sku_packs[sku]
                sizes = {tuple(sorted(measurements(v.name))) for v in same_sku if measurements(v.name)}
                if len(sizes) > 1:
                    issue('SKU_CONFLICTING_PACKS', 'P0', 'High', f'SKU={sku}; variant IDs and labels={[(v.pk, v.name) for v in same_sku]}.', 'Owner must confirm exact SKU/size mapping; do not combine or renumber.')
                elif len({normalized(v.name) for v in same_sku}) > 1 and any(not measurements(v.name) for v in same_sku):
                    issue('SKU_LABEL_REVIEW', 'P1', 'Low', f'SKU={sku}; labels={[(v.pk, v.name) for v in same_sku]}.', 'Confirm label equivalence against source. Abbreviations alone do not prove conflicting quantities.')
            if product.variant_family_id and (root.variant_family_id or root.pk == product.pk):
                issue('INVALID_FAMILY_GRAPH', 'P0', 'High', 'Nested or cyclic canonical-family link.', 'Review canonical links; no automatic regrouping.')
            if len(family) > 1 and (len(identities) > 1 or len(brands) > 1 or disjoint_species or len(kinds) > 1 or len(prescription) > 1):
                issue('WRONG_GROUPING_CANDIDATE', 'P0', 'Medium', f'Linked identities={sorted(identities)}; vendor IDs={sorted(str(b) for b in brands)}; disjoint pet categories={disjoint_species}; product types={sorted(kinds)}; prescription flags={sorted(prescription)}.', 'Check formulation, flavour, diet, age, species and strength against source before retaining links.')
            if len(dimensions) > 1:
                issue('FAMILY_INCOMPATIBLE_UNITS', 'P0', 'High', f'Family measurement dimensions={sorted(dimensions)}.', 'Verify grouping; do not compare mass, volume, length or counts as one value group.')
            # Exact titles only nominate review candidates. They NEVER authorize a merge.
            peers = names[(product.brand_id, title_identity(product.name))]
            separate = [p for p in peers if (p.variant_family_id or p.pk) != root.pk]
            if separate:
                same_sizes = [p for p in separate if any(measurements(v.name) == measures and measures for v in p.variants.all())]
                code = 'POSSIBLE_DUPLICATE_PRODUCT' if same_sizes else 'POSSIBLE_SPLIT_PRODUCT'
                issue(code, 'P1', 'Low', 'Exact normalized title/vendor peers with separate roots: ' + ', '.join(p.slug for p in separate), 'Compare source options, formulation and SKUs. Title agreement alone is insufficient to group.')
            if variant:
                nonpack = {k: val for k, val in variant.attributes.items() if k.casefold() not in ('size', 'weight', 'pack', 'option 1')} if isinstance(variant.attributes, dict) else {}
                if nonpack and len(family) > 1:
                    issue('FORMULATION_OPTIONS_REVIEW', 'P1', 'Medium', f'Additional options={nonpack}.', 'Verify whether flavour/formulation options intentionally belong to the same source product.')
            photo = photo_by_id.get(variant.image_id) if variant else primary
            displayed = photo or (primary if len(packs) == 1 else None)
            image_review = 'IMAGE REVIEW REQUIRED — packaging pixels not verified'
            visual_note = ''
            if photo and (photo.product_id != product.pk or not photo.is_active):
                issue('WRONG_IMAGE_OWNERSHIP', 'P0', 'High', f'Assigned image {photo.pk}: owner={photo.product_id}; active={photo.is_active}.', 'Verify exact source packaging before reassigning. Foreign/inactive images must not display as this pack.')
            if displayed:
                # Imported alt text often repeats the title. Do not count it as
                # independent evidence that a bottle contains the title's dose.
                alt = '' if normalized(displayed.alt_text) == normalized(product.name) else displayed.alt_text
                metadata = ' '.join([alt, unquote(urlsplit(displayed.source_url).path).rsplit('/', 1)[-1]])
                pictured = measurements(metadata)
                compatible = {m for m in pictured if m[0] in {x[0] for x in measures}}
                if measures and compatible and not compatible.intersection(measures):
                    issue('IMAGE_PACK_MISMATCH_CANDIDATE', 'P0', 'Medium', f'Image metadata={metadata!r}; pack={item_name!r}.', 'IMAGE REVIEW REQUIRED: inspect actual packaging. Filename/alt text is evidence, not visual confirmation.')
                source_images = {image_identity(r['Variant Image']) for r in exact_sources if r.get('Variant Image')}
                if source_images and displayed.source_url and image_identity(displayed.source_url) not in source_images:
                    issue('SOURCE_VARIANT_IMAGE_DIFFERENCE', 'P0', 'Medium', 'Assigned/fallback source URL differs from exact Shopify Variant Image.', 'Review export and current packaging; no automatic image replacement.')
                image_review += '; single-pack fallback' if not photo else '; assigned reference'
            else:
                image_review = 'IMAGE REVIEW REQUIRED — no unambiguous pack image'
            observation = observations.get(str(displayed.pk)) if displayed else None
            if observation and displayed.image:
                try:
                    image_hash = hashlib.sha256(Path(displayed.image.path).read_bytes()).hexdigest()
                except (OSError, ValueError, NotImplementedError):
                    image_hash = ''
                if image_hash == observation['sha256'].lower():
                    visual_note = observation['observed_text'] + ' [visual inspection ' + observation['reviewed_at'] + '; SHA-256 ' + image_hash + ']'
                    visible = measurements(observation['visible_pack'])
                    if visible and measures:
                        issues = [i for i in issues if i['code'] != 'IMAGE_PACK_MISMATCH_CANDIDATE']
                        if visible != measures:
                            issue('IMAGE_PACK_VISUAL_DISCREPANCY', 'P0', 'High', visual_note + '; catalog option=' + item_name, 'Owner must verify the supplied pack and correct artwork. No replacement or catalog edit applied.')
                        else:
                            image_review = 'Visible pack amount matches option in inspected file; not full identity approval'
                else:
                    visual_note = 'Prior image observation is stale or unreadable; not applied.'
            if variant and not photo and len(packs) > 1 and primary:
                issue('MULTIPACK_IMAGE_AMBIGUOUS', 'P1', 'Medium', 'Multiple packs share unassigned product photos.', 'Review exact pack photos; do not silently use first pack artwork for every size.')
            priorities = sorted(i['priority'] for i in issues)
            row = dict(zip(HEADERS, [''] * len(HEADERS)))
            row.update({'Product ID': str(product.pk), 'Product Name': product.name,
                'Shopify Handle': product.slug if source_rows else '', 'Canonical Family': root.family_name or root.name,
                'Family ID': str(root.pk), 'Brand/Vendor': product.brand.name if product.brand else '',
                'Variant ID': variant.pk if variant else '', 'Variant Display Name': item_name,
                'Parsed Pack Size': str(parsed[0]) if parsed else '', 'Parsed Unit': parsed[1] if parsed else '',
                'SKU': sku, 'Slug': product.slug, 'Product Image': primary.display_url if primary else '',
                'Variant Image': photo.display_url if photo else '', 'Family Member Count': len(family),
                'Conflict Type': '; '.join(i['code'] for i in issues), 'Priority': priorities[0] if priorities else '',
                'Confidence': '; '.join(f'{i["code"]}: {i["confidence"]}' for i in issues),
                'Recommended Action': ' | '.join(dict.fromkeys(i['action'] for i in issues)) or 'No automated identity conflict detected. Confirm exact source and packaging manually.',
                'Evidence Source': ' | '.join(dict.fromkeys(r['_evidence'] for r in (exact_sources or source_rows)[:8])) or 'Current Django catalog; Shopify source match unavailable',
                'Evidence Detail': ' | '.join(f'{i["code"]}: {i["evidence"]}' for i in issues),
                'Review Status': latest_reviews.get(product.pk, 'Not reviewed'), 'Image Review': image_review,
                'Visual Image Observation': visual_note,
                'Source Match': source_match, 'Suspected Identity': 'Owner verification required; current slug retained'})
            rows.append(row)
    counts = Counter(row['Priority'] for row in rows if row['Priority'])
    types = Counter(code for row in rows for code in row['Conflict Type'].split('; ') if code)
    summary = {'products_reviewed': len(products), 'families_reviewed': len(members),
        'linked_families_reviewed': sum(len(group) > 1 for group in members.values()),
        'variants_reviewed': sum(bool(row['Variant ID']) for row in rows), 'report_rows': len(rows),
        'rows_with_conflicts': sum(counts.values()), 'issue_occurrences': sum(types.values()),
        'P0': counts['P0'], 'P1': counts['P1'], 'P2': counts['P2'], 'by_conflict_type': dict(types),
        'wrong_grouping_families': len({r['Family ID'] for r in rows if 'WRONG_GROUPING_CANDIDATE' in r['Conflict Type'] or 'INVALID_FAMILY_GRAPH' in r['Conflict Type']}),
        'wrong_image_candidate_rows': sum(any(c in r['Conflict Type'] for c in ('WRONG_IMAGE_OWNERSHIP', 'IMAGE_PACK_MISMATCH_CANDIDATE', 'IMAGE_PACK_VISUAL_DISCREPANCY', 'SOURCE_VARIANT_IMAGE_DIFFERENCE')) for r in rows),
        'visually_inspected_rows': sum('visual inspection' in r['Visual Image Observation'] for r in rows),
        'image_review_required_rows': sum(r['Image Review'].startswith('IMAGE REVIEW REQUIRED') for r in rows), 'safe_formatting_fixes_applied': 0, 'source_records_changed': 0}
    return rows, summary, provenance

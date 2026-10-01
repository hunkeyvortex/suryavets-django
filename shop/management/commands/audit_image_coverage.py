"""Read-only image recovery plan. Exact source identities, never name-based borrowing."""
import json
from collections import Counter
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from shop.models import Product
from shop.services.pack_images import pack_photos
from shop.services.pack_identity import source_index, normalized
from shop.services.product_media import image_identity
from shop.services.catalog_quality import fingerprint
from shop.services.pack_review_snapshot import snapshot


HEADERS = ['Product ID', 'Product Name', 'Canonical Family', 'Variant ID', 'Variant Name',
    'SKU', 'Brand', 'Current Image Count', 'Primary Image', 'Variant Image', 'Recovered Image',
    'Recovery Source', 'Confidence', 'Missing Image', 'Needs Review', 'Reason']


def local_usable(photo):
    if not photo.is_active or photo.check_error:
        return False
    return bool(photo.image and photo.image.storage.exists(photo.image.name))


class Command(BaseCommand):
    help = 'Read-only exact-pack image coverage and recovery candidates. No writes to catalog or downloads.'

    def add_arguments(self, parser):
        parser.add_argument('--sources', nargs='*', default=[])
        parser.add_argument('--dry-run', action='store_true', help='Explicit read-only mode (also the default).')
        parser.add_argument('--output', default='catalog_review/image_coverage_data.json')

    def handle(self, *args, **options):
        before = fingerprint()
        sources, provenance = source_index(options['sources'])
        evidence = snapshot()['by_product']
        counts = Counter(products=0, products_with_images=0, products_without_images=0,
            variants_with_exact_images=0, missing_variants=0, matched=0, skipped=0,
            ambiguous=0, missing=0, failed=0, recovered=0)
        rows, families, usable_families = [], set(), set()
        for product in Product.objects.select_related('brand', 'variant_family').prefetch_related('images', 'variants').order_by('pk'):
            counts['products'] += 1
            root = product.variant_family or product
            families.add(str(root.pk))
            photos = list(product.images.all())
            usable = [photo for photo in photos if local_usable(photo)]
            if usable:
                counts['products_with_images'] += 1
                usable_families.add(str(root.pk))
            else:
                counts['products_without_images'] += 1
            source_rows = sources.get(product.slug, [])
            titles = {normalized(row.get('Title')) for row in source_rows if row.get('Title')}
            vendors = {normalized(row.get('Vendor')) for row in source_rows if row.get('Vendor')}
            identity_ok = titles == {normalized(product.name)} and (not product.brand or vendors == {normalized(product.brand.name)})
            for variant in list(product.variants.all()) or [None]:
                exact = [photo for photo in pack_photos(variant) if local_usable(photo)] if variant else usable
                if variant:
                    counts['variants_with_exact_images' if exact else 'missing_variants'] += 1
                confidence, reason, candidate = 'LOW', 'No verified local image for this exact pack.', ''
                matching = [row for row in source_rows if variant and variant.sku and (row.get('Variant SKU') or '').strip() == variant.sku]
                urls = {image_identity(row.get('Variant Image') or '') for row in matching if row.get('Variant Image')}
                if exact:
                    confidence, reason = 'HIGH', 'Existing source-owned pack mapping and readable local file. Not a new visual approval.'
                    counts['skipped'] += 1
                elif identity_ok and len(urls) == 1:
                    candidate = next(iter(urls))
                    # Source evidence only: do not activate a previously rejected photo or replace a staff mapping.
                    conflicts = [p for p in photos if image_identity(p.source_url) == candidate and p.check_error]
                    confidence = 'MEDIUM' if conflicts or (variant and variant.image_id) else 'HIGH'
                    reason = 'Exact handle, title, vendor and SKU source mapping; download/pack review still required.'
                    counts['matched' if confidence == 'HIGH' else 'ambiguous'] += 1
                elif photos or any(row.get('Image Src') or row.get('Variant Image') for row in source_rows):
                    confidence, reason = 'MEDIUM', 'Source or local references exist, but exact-pack identity or file availability is unresolved.'
                    counts['ambiguous'] += 1
                else:
                    counts['missing'] += 1
                primary = next((p for p in photos if p.is_primary), photos[0] if photos else None)
                conflict = any(r.get('Priority') == 'P0' for r in evidence.get(str(product.pk), []))
                if conflict:
                    confidence, reason = 'LOW', 'Existing image has a recorded critical pack discrepancy. Staff review required; no mapping changed.'
                    counts['known_critical_image_conflicts'] += 1
                rows.append([str(product.pk), product.name, str(root.pk), str(variant.pk) if variant else '',
                    variant.name if variant else '', variant.sku if variant else product.sku,
                    product.brand.name if product.brand else '', len(usable), primary.display_url if primary else '',
                    next((p.display_url for p in photos if variant and p.pk == variant.image_id), ''), '',
                    candidate, confidence, 'NO' if exact else 'YES', 'NO' if exact and not conflict else 'YES', reason])
        counts['canonical_families'] = len(families)
        counts['families_with_usable_image'] = len(usable_families)
        counts['catalog_export_files'] = sum(1 for p in (Path(settings.BASE_DIR)/'catalog_exports'/'images').rglob('*') if p.is_file())
        after = fingerprint()
        if before != after:
            raise RuntimeError('Catalog changed during audit. Do not use this snapshot.')
        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({'headers': HEADERS, 'rows': rows, 'summary': dict(counts),
            'sources': provenance, 'catalog_unchanged': True}, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(json.dumps(dict(counts)))

"""Build source-evidenced mappings and a neutral review matrix; never guesses handles."""
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from shop.models import Product, Category
from shop.services.pack_identity import source_index, title_identity

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--sources', nargs='+', required=True)
    def handle(self, *args, **options):
        source, provenance = source_index(options['sources'])
        mappings, rows = {}, []
        products = {p.slug: p for p in Product.objects.filter(is_active=True)}
        for handle, records in source.items():
            product = products.get(handle)
            titles = {title_identity(r['Title']) for r in records if r.get('Title')}
            confirmed = product is not None and titles == {title_identity(product.name)}
            target = product.get_absolute_url() if product else ''
            path = '/products/' + handle
            rows.append([path, target, 'HIGH' if confirmed else 'LOW', 'Exact exported handle and title identity' if confirmed else 'Missing or conflicting identity; do not guess', 'IMPLEMENTED' if confirmed else 'REVIEW'])
            if confirmed:
                mappings[path] = target
        groups = {}
        for category in Category.objects.filter(is_active=True):
            if category.reference_path.startswith('/collections/'):
                groups.setdefault(category.reference_path.rstrip('/'), []).append(category)
        for path, categories in groups.items():
            confirmed = len(categories) == 1 and not any(not a.is_active for a in categories[0].get_ancestors())
            target = categories[0].get_absolute_url() if len(categories) == 1 else ''
            rows.append([path, target, 'HIGH' if confirmed else 'LOW', 'Stored reference path' if confirmed else 'Ambiguous/inactive reference path', 'IMPLEMENTED' if confirmed else 'REVIEW'])
            if confirmed:
                mappings[path] = target
        for handle in ('about', 'contact', 'shipping', 'returns', 'privacy', 'terms'):
            rows.append(['/pages/'+handle, '/'+handle+'/', 'LOW', 'Source page handle not verified', 'REVIEW'])
        folder = Path(settings.BASE_DIR) / 'catalog_review'
        folder.mkdir(exist_ok=True)
        (folder/'seo_redirects.json').write_text(json.dumps(mappings, indent=2), encoding='utf-8')
        (folder/'seo_redirect_matrix.json').write_text(json.dumps({'headers': ['old_path','candidate_new_path','confidence','reason','status'], 'rows': rows, 'sources': provenance}), encoding='utf-8')
        self.stdout.write(f'{len(rows)} review rows; {len(mappings)} deterministic mappings. No catalog changes.')

"""Restore public navigation and exported tags without overwriting prices, variants or stock."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from shop.models import Category, Product
from shop.management.commands.import_shopify_products import Command as ProductImporter
from shop.services.taxonomy import collection_tag_index, matching_collections


class Command(BaseCommand):
    help = 'Restore reference navigation and attach existing products using exact Shopify export tags.'

    def add_arguments(self, parser):
        parser.add_argument('sources', nargs='*')
        parser.add_argument('--navigation', default=str(Path(__file__).resolve().parents[2] / 'data' / 'reference_navigation.json'))

    @transaction.atomic
    def handle(self, *args, **options):
        tree = json.loads(Path(options['navigation']).read_text(encoding='utf-8'))
        seen = set()
        def restore(nodes, parent=None):
            for order, item in enumerate(nodes, 1):
                handle = item['url'].rstrip('/').rsplit('/', 1)[-1]
                if handle in seen:
                    raise CommandError(f'Duplicate navigation handle: {handle}')
                seen.add(handle)
                # Reuse local root slugs so previously shared category URLs remain valid.
                node = Category.objects.filter(name=item['name']).first() or Category.objects.filter(slug=handle).first()
                if node is None:
                    node = Category(name=item['name'], slug=handle)
                node.parent = parent
                node.order = order
                node.reference_path = item['url']
                node.is_active = True
                node.full_clean()
                node.save()
                restore(item.get('children', []), node)
        restore(tree)
        index = collection_tag_index()
        products = {p.slug: p for p in Product.objects.only('id', 'slug', 'shopify_tags')}
        updated, links, tagged = {}, set(), 0
        importer = ProductImporter()
        for handle, rows in importer._product_groups(options['sources']):
            product = products.get(handle)
            if product is None:
                continue
            primary = next((r for r in rows if r.get('Title')), rows[0])
            product.shopify_tags = sorted(importer._tags(primary))
            updated[product.pk] = product
            matched = matching_collections(product.shopify_tags, index)
            if matched:
                tagged += 1
            links.update((product.pk, category_id) for category_id in matched)
        Product.objects.bulk_update(updated.values(), ['shopify_tags'], batch_size=200)
        through = Product.collections.through
        through.objects.bulk_create([through(product_id=p, category_id=c) for p,c in links], ignore_conflicts=True, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f'Navigation nodes={len(seen)}, products with restored tags={len(updated)}, matched products={tagged}, collection memberships={len(links)}. Existing prices/stock/variants preserved.'))

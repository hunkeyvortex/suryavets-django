"""Repair only prices from owned exports, without reimporting stock or deleting rows."""
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shop.management.commands.import_shopify_products import Command as ProductImporter, option_name
from shop.models import Product, ProductVariant
from shop.services.pricing import export_prices


class Command(BaseCommand):
    help = 'Validate exact Shopify prices (read-only by default). Use --apply to update only price fields.'

    def add_arguments(self, parser):
        parser.add_argument('sources', nargs='+')
        parser.add_argument('--apply', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        importer = ProductImporter()
        counts = Counter()
        products_to_update, variants_to_update = [], []
        products = {item.slug: item for item in Product.objects.prefetch_related('variants')}
        for handle, rows in importer._product_groups(options['sources']):
            priced_rows = importer._priced_rows(handle, rows)
            product = products.get(handle)
            if product is None:
                counts['products_missing_locally'] += 1
                continue
            variants = {variant.name: variant for variant in product.variants.all()}
            regular, price, discount = export_prices(priced_rows[0])
            counts['product_display_prices_corrected'] += product.current_price != price
            product.base_price, product.selling_price, product.discount_percentage = regular, price, discount
            products_to_update.append(product)
            for row in priced_rows:
                name = option_name(row)
                if name == 'Default Title' and len(priced_rows) == 1 and not variants:
                    continue
                variant = variants.get(name)
                if variant is None:
                    raise CommandError(f'{handle}: variant {name!r} is missing locally. No prices applied; reconcile identity first.')
                if variant.sku != (row.get('Variant SKU') or '')[:100]:
                    raise CommandError(f'{handle} / {name}: SKU changed. No prices applied; reconcile identity first.')
                regular, price, discount = export_prices(row)
                counts['variant_display_prices_corrected'] += variant.current_price != price
                variant.price_override, variant.selling_price, variant.discount_percentage = regular, price, discount
                variants_to_update.append(variant)
        counts['products_validated'] = len(products_to_update)
        counts['variants_validated'] = len(variants_to_update)
        if options['apply']:
            Product.objects.bulk_update(products_to_update, ['base_price', 'selling_price', 'discount_percentage'], batch_size=300)
            ProductVariant.objects.bulk_update(variants_to_update, ['price_override', 'selling_price', 'discount_percentage'], batch_size=300)
        mode = 'Applied price-only repair' if options['apply'] else 'Read-only validation; use --apply to repair'
        self.stdout.write(self.style.SUCCESS(mode + ': ' + ', '.join(f'{key}={value}' for key, value in sorted(counts.items()))))

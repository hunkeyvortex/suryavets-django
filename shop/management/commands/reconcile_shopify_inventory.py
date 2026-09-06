"""Conservative, explicit-location stock reconciliation. Read-only by default."""
import csv
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum

from shop.management.commands.import_shopify_products import option_name
from shop.models import Order, Product, ProductVariant, InventoryMovement


class Command(BaseCommand):
    help = 'Match inventory by exact handle/pack/SKU. Choose one location. Omitted products are never zeroed.'

    def add_arguments(self, parser):
        parser.add_argument('source')
        parser.add_argument('--location', required=True)
        parser.add_argument('--apply', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['apply'] and Order.objects.filter(stock_deducted=True).exists():
            raise CommandError('Local orders have deducted stock. Reconcile order movements before applying an external snapshot.')
        if options['apply'] and InventoryMovement.objects.exists():
            raise CommandError('Local CRM stock movements exist. Reconcile these before applying an external snapshot.')
        with Path(options['source']).open(encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source)
            if not {'Handle', 'SKU', 'Option1 Value', options['location']}.issubset(reader.fieldnames or []):
                raise CommandError('Required inventory columns or the selected location are missing.')
            rows = list(reader)
        counts, seen, updates = Counter(), set(), []
        for row in sorted(rows, key=lambda row: row.get('Handle', '')):
            handle, name, sku = row['Handle'].strip(), option_name(row), row['SKU'].strip()
            key = handle, name
            if not handle or key in seen:
                raise CommandError(f'Blank or duplicate inventory identity: {handle} / {name}')
            seen.add(key)
            raw = row[options['location']].strip()
            if not raw.isdecimal() or int(raw) > 2147483647:
                raise CommandError(f'{handle} / {name}: quantity must be a non-negative whole number; blanks are not zero.')
            quantity = int(raw)
            counts['source_rows'] += 1; counts['source_units'] += quantity
            query = Product.objects.filter(slug=handle)
            product = (query.select_for_update() if options['apply'] else query).first()
            target = None
            status = 'product_missing'
            if product:
                variants = product.variants.all()
                if options['apply']:
                    variants = variants.select_for_update()
                candidates = list(variants)
                target = next((variant for variant in candidates if variant.name == name), None)
                if not candidates and name == 'Default Title':
                    target = product
                status = 'variant_missing' if target is None else 'matched'
                if target and sku and target.sku != sku:
                    status, target = 'sku_mismatch', None
            counts[status] += 1
            self.stdout.write(f'{handle} | {name} | source={quantity} | local={target.stock_quantity if target else "unmatched"} | {status}')
            if target:
                updates.append((target, quantity))
        if options['apply']:
            # Recheck after taking product locks: an order may have committed
            # between the initial guard and this snapshot's lock acquisition.
            if Order.objects.filter(stock_deducted=True).exists() or InventoryMovement.objects.exists():
                raise CommandError('Stock changed during reconciliation. No snapshot quantities were applied.')
            for target, quantity in updates:
                target.stock_quantity = quantity
                target.save(update_fields=['stock_quantity', 'updated_at'])
            for product_id in {target.product_id for target, _ in updates if isinstance(target, ProductVariant)}:
                total = ProductVariant.objects.filter(product_id=product_id, is_active=True).aggregate(total=Sum('stock_quantity'))['total'] or 0
                Product.objects.filter(pk=product_id).update(stock_quantity=total)
        mode = 'Applied matched quantities only' if options['apply'] else 'Read-only reconciliation'
        self.stdout.write(self.style.SUCCESS(mode + ': ' + ', '.join(f'{key}={value}' for key, value in sorted(counts.items()))))
        self.stdout.write('Stock-tracking flags are unchanged. This location snapshot does not verify the rest of the catalogue.')

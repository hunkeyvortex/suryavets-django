"""Explicit, audited local stock reset. No price, visibility or order edits."""
import uuid
from collections import Counter
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from shop.models import Product, ProductVariant, InventoryMovement, CRMActivity


class Command(BaseCommand):
    help = 'Set every existing pack (or simple product) to a quantity, preserving an append-only movement history.'

    def add_arguments(self, parser):
        parser.add_argument('--quantity', type=int, required=True)
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--batch', type=uuid.UUID, required=True, help='Idempotency UUID; reuse it when retrying this same reset.')
        parser.add_argument('--reason', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        quantity=options['quantity']; reason=options['reason'].strip()
        if not 0 <= quantity <= 1000000 or not 3 <= len(reason) <= 350:
            raise CommandError('Use a quantity between 0 and 1000000 and a reason of 3–350 characters.')
        marker=f'Stock reset [{options["batch"]}]'
        products=list(Product.objects.select_for_update().order_by('pk'))
        if CRMActivity.objects.filter(text__startswith=marker).exists():
            self.stdout.write('This batch has already been applied; stock was not reset again.'); return
        variants=list(ProductVariant.objects.select_for_update().order_by('pk'))
        packed={v.product_id for v in variants}; totals=Counter()
        movements=[]; changed_products=[]; changed_variants=[]; now=timezone.now()
        for item in [*variants, *(p for p in products if p.pk not in packed)]:
            is_pack=isinstance(item,ProductVariant)
            if is_pack and item.is_active: totals[item.product_id]+=quantity
            if item.stock_quantity==quantity: continue
            movements.append(InventoryMovement(product_id=item.product_id if is_pack else item.pk,
                variant=item if is_pack else None, kind='adjustment', delta=quantity-item.stock_quantity,
                quantity_before=item.stock_quantity,quantity_after=quantity,reason=f'{marker}: {reason}',
                request_key=uuid.uuid5(options['batch'],f'{"variant" if is_pack else "product"}:{item.pk}')))
            item.stock_quantity=quantity; item.updated_at=now
            (changed_variants if is_pack else changed_products).append(item)
        for product in products:
            if product.pk in packed and product.stock_quantity != totals[product.pk]:
                product.stock_quantity=totals[product.pk]; product.updated_at=now; changed_products.append(product)
        self.stdout.write(f'Products={len(products)}, packs={len(variants)}, stock movements={len(movements)}, quantity per pack/simple product={quantity}')
        if not options['apply']:
            self.stdout.write('DRY RUN: no changes.'); return
        ProductVariant.objects.bulk_update(changed_variants,['stock_quantity','updated_at'],batch_size=300)
        Product.objects.bulk_update(changed_products,['stock_quantity','updated_at'],batch_size=300)
        InventoryMovement.objects.bulk_create(movements,batch_size=300)
        CRMActivity.objects.create(kind='note',text=f'{marker}: {reason}. Set {len(variants)} packs and {len(products)-len(packed)} simple products to {quantity}; {len(movements)} ledger entries. Visibility and tracking flags unchanged. This is an owner-requested balance, not physical stock verification.')
        self.stdout.write('Applied with inventory history. Prices, orders, visibility and tracking flags preserved.')

import csv
import io
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from shop.models import Category, Order, Product, ProductVariant, InventoryMovement


class InventoryReconciliationTests(TestCase):
    def test_snapshot_writes_blocked_after_crm_adjustment_but_preview_remains_available(self):
        InventoryMovement.objects.create(product=self.product, variant=self.variant, kind='adjustment',
            delta=1, quantity_before=1, quantity_after=2, reason='Opening stock correction')
        with self.assertRaisesMessage(CommandError, 'Local CRM stock movements exist'):
            self.reconcile(apply=True)
        with self.assertRaisesMessage(CommandError, 'Local CRM stock movements exist'):
            call_command('import_shopify_products', 'not-opened.csv')
        self.assertIn('matched=1', self.reconcile())

    def setUp(self):
        self.product = Product.objects.create(name='Inventory test', category=Category.objects.create(name='Dog'), base_price=100, stock_quantity=2)
        self.variant = ProductVariant.objects.create(product=self.product, name='1 KG', sku='SKU-1', stock_quantity=2)
        self.row = {'Handle': self.product.slug, 'Option1 Value': '1 KG', 'SKU': 'SKU-1', 'Andheri West': '7'}

    def reconcile(self, rows=None, apply=False):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'inventory.csv'
            with path.open('w', encoding='utf-8', newline='') as source:
                writer = csv.DictWriter(source, fieldnames=list(self.row)); writer.writeheader(); writer.writerows(rows or [self.row])
            output = io.StringIO()
            call_command('reconcile_shopify_inventory', str(path), location='Andheri West', apply=apply, stdout=output)
            return output.getvalue()

    def test_read_only_is_default(self):
        self.assertIn('matched=1', self.reconcile())
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock_quantity, 2)

    def test_apply_only_updates_exact_matches_and_preserves_missing_products(self):
        untouched = Product.objects.create(name='Not exported', category=self.product.category, base_price=10, stock_quantity=9)
        self.reconcile(apply=True)
        self.variant.refresh_from_db(); self.product.refresh_from_db(); untouched.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 7)
        self.assertEqual(self.product.stock_quantity, 7)
        self.assertEqual(untouched.stock_quantity, 9)

    def test_invalid_quantities_and_duplicate_rows_are_rejected_without_writes(self):
        for raw in ('', 'NaN', '-1', '1.5', 'untracked'):
            with self.assertRaises(CommandError):
                self.reconcile([{**self.row, 'Andheri West': raw}], apply=True)
        with self.assertRaises(CommandError):
            self.reconcile([self.row, self.row], apply=True)
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock_quantity, 2)

    def test_sku_mismatch_is_not_guessed(self):
        self.assertIn('sku_mismatch=1', self.reconcile([{**self.row, 'SKU': 'DIFFERENT'}], apply=True))
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock_quantity, 2)

    def test_existing_local_stock_movements_block_snapshot_application(self):
        Order.objects.create(email='test@example.com', total=100, subtotal=100, stock_deducted=True)
        with self.assertRaises(CommandError):
            self.reconcile(apply=True)
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock_quantity, 2)

    def test_full_product_import_is_blocked_after_checkout_stock_movements(self):
        Order.objects.create(email='test@example.com', total=100, subtotal=100, stock_deducted=True)
        with self.assertRaisesMessage(CommandError, 'Local checkout orders have deducted stock'):
            call_command('import_shopify_products', 'not-opened.csv')

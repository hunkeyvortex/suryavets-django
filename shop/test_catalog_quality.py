import csv
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import TestCase, override_settings
from PIL import Image

from .models import Category, Product, ProductVariant, ProductImage, InventoryMovement
from .services.catalog_quality import build_report, fingerprint, select_only, HEADERS


class CatalogQualityTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Dog')
        self.product = Product.objects.create(name='Food 80GM', slug='food-80gm', category=self.category,
            base_price=100, selling_price=90, stock_quantity=10, is_bestseller=True)
        self.pack = ProductVariant.objects.create(product=self.product, name='70GM', sku='', selling_price=0, stock_quantity=10)

    def test_zero_price_blank_sku_missing_image_and_default_stock_are_reported(self):
        reports, counts, _ = build_report()
        self.assertEqual(counts['zero_price_variants'], 1)
        self.assertEqual(counts['blank_sku_variants'], 1)
        self.assertEqual(counts['suspicious_stock_variants'], 1)
        self.assertEqual(counts['products_without_verified_usable_image'], 1)
        row = reports['catalog_master_review.csv'][0]
        self.assertEqual(len(row), len(HEADERS))
        self.assertTrue(row['Missing Image'])
        self.assertIn('quantity conflict', row['Pack Issues'])
        self.assertEqual(row['Publishable'], 'REVIEW REQUIRED')

    def test_reports_and_fingerprints_do_not_mutate_data(self):
        before = fingerprint()
        with connection.execute_wrapper(select_only):
            build_report()
        self.assertEqual(before, fingerprint())

    def test_readonly_guard_refuses_database_writes(self):
        with self.assertRaises(RuntimeError), transaction.atomic(), connection.execute_wrapper(select_only):
            Product.objects.filter(pk=self.product.pk).update(stock_quantity=0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    def test_ledger_uses_observed_opening_not_zero_and_detects_gaps(self):
        InventoryMovement.objects.create(product=self.product, variant=self.pack, kind='adjustment',
            quantity_before=8, delta=2, quantity_after=10, reason='Physical stock adjustment')
        row = build_report()[0]['catalog_master_review.csv'][0]
        self.assertEqual(row['Ledger Derived Stock'], 10)
        self.assertEqual(row['Ledger Issues'], '')
        InventoryMovement.objects.create(product=self.product, variant=self.pack, kind='adjustment',
            quantity_before=7, delta=1, quantity_after=8, reason='Second adjustment')
        row = build_report()[0]['catalog_master_review.csv'][0]
        self.assertIn('discontinuity', row['Ledger Issues'])
        self.assertIn('differs', row['Ledger Issues'])

    def test_exact_source_options_sku_and_price_preserved(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / 'products.csv'
            with source.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=['Handle', 'Title', 'Option1 Value', 'Variant SKU', 'Variant Price', 'Variant Compare At Price'])
                writer.writeheader()
                writer.writerow({'Handle': self.product.slug, 'Title': 'Original 70GM', 'Option1 Value': '70GM', 'Variant SKU': '', 'Variant Price': '0', 'Variant Compare At Price': '100'})
            row = build_report([str(source)])[0]['catalog_master_review.csv'][0]
            self.assertEqual(row['Source Match'], 'Exact handle/options/SKU')
            self.assertEqual(row['Source Price'], 0)
            self.assertEqual(row['Source Title'], 'Original 70GM')

    def test_ambiguous_source_price_not_silently_selected(self):
        from collections import defaultdict
        records = [{'Option1 Value': '70GM', 'Variant Price': p} for p in ('10', '20')]
        with patch('shop.services.catalog_quality.sources', return_value=({self.product.slug: records}, defaultdict(list), [])):
            row = build_report()[0]['catalog_master_review.csv'][0]
        self.assertEqual(row['Source Match'], 'Ambiguous source rows')
        self.assertEqual(row['Source Price'], '')

    def test_inventory_coverage_does_not_count_unmatched_lookups(self):
        from collections import defaultdict
        stock = defaultdict(list, {('unrelated', 'Default Title', 'OTHER'): ['Warehouse=2']})
        with patch('shop.services.catalog_quality.sources', return_value=({}, stock, [])):
            _, counts, _ = build_report()
        self.assertEqual(counts['inventory_source_identities'], 1)
        self.assertEqual(counts['inventory_exact_matched_rows'], 0)
        self.assertEqual(len(stock), 1)

    def test_image_verification_detects_missing_files_and_wrong_owner(self):
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            photo = ProductImage.objects.create(product=self.product, image='missing.png')
            self.pack.image = photo; self.pack.save()
            row = build_report()[0]['catalog_master_review.csv'][0]
            self.assertIn('Missing local original', row['Image Issues'])
            Image.new('RGB', (20, 20), 'white').save(Path(folder) / 'missing.png')
            row = build_report()[0]['catalog_master_review.csv'][0]
            self.assertFalse(row['Missing Image'])
            other = Product.objects.create(name='Different food', category=self.category, base_price=10)
            photo.product = other; photo.save()
            row = next(r for r in build_report()[0]['catalog_master_review.csv'] if r['Variant ID'] == self.pack.pk)
            self.assertTrue(row['Missing Image'])
            self.assertIn('another product', row['Image Issues'])

    def test_duplicate_candidates_never_merge_families(self):
        self.pack.sku = 'SHARED'; self.pack.save()
        other = Product.objects.create(name='Unrelated supplement', category=self.category, base_price=120)
        ProductVariant.objects.create(product=other, name='1KG', sku='SHARED', stock_quantity=1)
        before = fingerprint()
        candidates = build_report()[0]['duplicate_or_similar_products.csv']
        self.assertTrue(any(r['Signal'] == 'Exact SKU' for r in candidates))
        self.assertEqual(before, fingerprint())

    def test_command_generates_reports_preserves_existing_and_escapes_formulas(self):
        self.product.name = '=Untrusted'; self.product.save()
        with TemporaryDirectory() as folder:
            before = fingerprint()
            call_command('audit_catalog_quality', output_dir=folder, stdout=io.StringIO())
            self.assertEqual(len(list(Path(folder).glob('*.csv'))), 9)
            with (Path(folder) / 'catalog_master_review.csv').open(encoding='utf-8-sig', newline='') as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row['Product Name'], "'=Untrusted")
            self.assertEqual(row['Stock'], '10')
            manifest = json.loads((Path(folder) / 'audit_manifest.json').read_text())
            self.assertTrue(manifest['business_data_unchanged'])
            with self.assertRaises(CommandError):
                call_command('audit_catalog_quality', output_dir=folder, stdout=io.StringIO())
            call_command('audit_catalog_quality', output_dir=folder, archive_existing=True, stdout=io.StringIO())
            self.assertEqual(len(list(Path(folder).glob('history-*'))), 1)
            self.assertEqual(fingerprint(), before)

    def test_empty_catalog_exports_headers(self):
        self.pack.delete(); self.product.delete()
        with TemporaryDirectory() as folder:
            call_command('audit_catalog_quality', output_dir=folder, stdout=io.StringIO())
            for path in Path(folder).glob('*.csv'):
                with path.open(encoding='utf-8-sig') as stream:
                    self.assertTrue(next(csv.reader(stream)))

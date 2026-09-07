import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .models import Product, ProductVariant, Category


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set SURYA_BROWSER_NODE for catalog browser verification.')
class CatalogBrowserTests(StaticLiveServerTestCase):
    def test_inventory_editor_and_archive_flow(self):
        get_user_model().objects.create_superuser('catalog-fixture', 'fixture@example.com', 'Catalog-fixture-482!')
        category = Category.objects.create(name='Dog')
        product = Product.objects.create(name='Daily Care Supplement', category=category, sku='CARE-60', base_price=499, selling_price=399, stock_quantity=18)
        ProductVariant.objects.create(product=product, name='60 tablets', price_override=499, selling_price=399, stock_quantity=18)
        Product.objects.create(name='Everyday Nutrition', category=category, base_price=899, selling_price=799, stock_quantity=0)
        Product.objects.create(name='Gentle Grooming Shampoo', category=category, base_price=250, selling_price=200, is_active=False)
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('catalog_browser_test.cjs')),
            self.live_server_url, str(product.pk)], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        created = Product.objects.get(slug='browser-catalog-new')
        self.assertEqual(created.name, 'New daily supplement')
        self.assertEqual(created.stock_quantity, 0)
        self.assertTrue(created.is_active)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 18)
        self.assertEqual(product.variants.get().selling_price, 349)

import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .models import Category, Product, ProductVariant, CartItem


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set browser runtime for cart autosave verification.')
class CartAutosaveBrowserTests(StaticLiveServerTestCase):
    def test_automatic_quantity_saving(self):
        product = Product.objects.create(name='Autosave food', slug='autosave-food',
            category=Category.objects.create(name='Dog'), base_price=100, stock_quantity=8)
        pack = ProductVariant.objects.create(product=product, name='3 KG', selling_price=90, stock_quantity=8)
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'],
            str(Path(__file__).with_name('cart_autosave_browser_test.cjs')), self.live_server_url],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(CartItem.objects.values_list('quantity', flat=True)), [2, 2])
        pack.refresh_from_db()
        self.assertEqual(pack.stock_quantity, 8)

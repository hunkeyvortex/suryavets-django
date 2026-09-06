"""Optional real-browser checkout on Django's disposable test database."""
import os
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from shop.models import Category, Order, Product


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set SURYA_BROWSER_NODE to run the optional browser test.')
class CheckoutBrowserTest(StaticLiveServerTestCase):
    def test_guest_purchase_and_duplicate_post(self):
        product = Product.objects.create(name='Browser checkout fixture', category=Category.objects.create(name='Dog'),
            slug='browser-checkout-fixture', base_price=100, selling_price=90, stock_quantity=5)
        script = Path(__file__).with_name('checkout_browser_test.cjs')
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(script), self.live_server_url],
            capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().subtotal, 180)
        self.assertEqual(Order.objects.get().items.get().unit_price, 90)
        product.refresh_from_db(); self.assertEqual(product.stock_quantity, 3)

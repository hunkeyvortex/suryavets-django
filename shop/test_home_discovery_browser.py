import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .models import Category, Product, ProductVariant, ProductImage, CartItem


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set browser runtime for homepage verification.')
class HomeDiscoveryBrowserTests(StaticLiveServerTestCase):
    @patch('shop.services.merchandising.snapshot', return_value={'generated_at': 'test', 'by_product': {}})
    def test_mobile_discovery_and_variant_purchase(self, evidence):
        for pet in ('Dog', 'Cat'):
            root = Category.objects.create(name=pet)
            food = Category.objects.create(name=f'{pet} Food', slug=f'food-for-{pet.lower()}s', parent=root)
            for number in range(6):
                product = Product.objects.create(name=f'{pet} meal {number}', category=food,
                    base_price=100, is_bestseller=True, stock_quantity=10, merchandising_active=True)
                photo = ProductImage.objects.create(product=product, source_url='https://example.com/pack.jpg')
                ProductVariant.objects.create(product=product, name='3 KG', selling_price=90, stock_quantity=10, image=photo)
                ProductVariant.objects.create(product=product, name='6 KG', selling_price=180, stock_quantity=10, image=photo)
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'],
            str(Path(__file__).with_name('home_discovery_browser_test.cjs')), self.live_server_url],
            capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        item = CartItem.objects.get()
        self.assertEqual(item.product_variant.name, '6 KG')
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.total_price, 180)

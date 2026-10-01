import json
import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client
from .models import Category, Product, ProductVariant, Cart, CartItem, Order, InventoryMovement
from .services.cart import SESSION_CART_KEY


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set browser runtime for purchase-safety verification.')
class PurchaseSafetyBrowserTests(StaticLiveServerTestCase):
    def test_safety_at_desktop_and_mobile_widths(self):
        cat = Category.objects.create(name='Dog')
        mixed = Product.objects.create(name='Safety mixed family', slug='safety-mixed', category=cat, base_price=200, stock_quantity=10)
        good = ProductVariant.objects.create(product=mixed, name='1 KG', selling_price=180, stock_quantity=10)
        bad = ProductVariant.objects.create(product=mixed, name='4 KG', selling_price=0, stock_quantity=10)
        blocked = Product.objects.create(name='Safety unavailable family', slug='safety-unavailable', category=cat, base_price=200)
        ProductVariant.objects.create(product=blocked, name='5 KG', selling_price=0, stock_quantity=10)
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=mixed, product_variant=bad, quantity=1)
        client = Client()
        session = client.session
        session[SESSION_CART_KEY] = str(cart.pk)
        session.save()
        args = {'good': good.pk, 'bad': bad.pk, 'product': str(mixed.pk), 'cookie': session.session_key, 'cookieName': settings.SESSION_COOKIE_NAME}
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('purchase_safety_browser_test.cjs')), self.live_server_url, json.dumps(args)], capture_output=True, text=True, timeout=200)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(InventoryMovement.objects.exists())
        self.assertEqual(ProductVariant.objects.get(pk=good.pk).stock_quantity, 10)

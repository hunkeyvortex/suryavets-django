"""CRM and original account UI tested with fake records in a disposable database."""
import os
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from shop.forms import CheckoutForm
from shop.models import Cart, CartItem, Category, InventoryMovement, Order, Product
from shop.services.cart import cart_items
from shop.services.checkout import place_order, review_token
from shop.test_checkout import CHECKOUT_DATA


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set SURYA_BROWSER_NODE for browser verification.')
class CRMBrowserTest(StaticLiveServerTestCase):
    def test_staff_operations_and_customer_signup(self):
        get_user_model().objects.create_superuser('crm-fixture', 'fixture@example.com', 'CRM-browser-fixture-482!')
        product = Product.objects.create(name='Browser inventory fixture', category=Category.objects.create(name='Dog'),
                                         slug='browser-inventory-fixture', base_price=100, stock_quantity=10)
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=product, quantity=2)
        form = CheckoutForm(CHECKOUT_DATA)
        self.assertTrue(form.is_valid())
        order = place_order(cart, AnonymousUser(), review_token(cart, list(cart_items(cart))), form.cleaned_data)
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('crm_browser_test.cjs')),
                                 self.live_server_url, str(product.pk), str(order.pk)], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        product.refresh_from_db(); order.refresh_from_db()
        self.assertEqual(product.stock_quantity, 13)
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(InventoryMovement.objects.count(), 3)
        self.assertFalse(get_user_model().objects.get(email='browser-parent@gmail.com').is_staff)

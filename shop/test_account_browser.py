import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .models import Order, OrderItem, Category, Product, ProductVariant, PetCategory, CustomerPet, CustomerAddress, WishlistItem, SupportRequest
from .services.order_tracking import record_event


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set SURYA_BROWSER_NODE to verify account mobile UI.')
class AccountBrowserTests(StaticLiveServerTestCase):
    def test_shared_tracking_and_mobile_account(self):
        buyer = get_user_model().objects.create_user('account-browser', email='account-browser@example.com', password='Account-fixture-921!')
        get_user_model().objects.create_superuser('account-staff', email='account-staff@example.com', password='Account-fixture-921!')
        product = Product.objects.create(name='Nutrition fixture', category=Category.objects.create(name='Dog'), base_price=100)
        variant = ProductVariant.objects.create(product=product, name='5 KG', selling_price=100, stock_quantity=20)
        order = Order.objects.create(user=buyer, email=buyer.email, phone='9876543210', shipping_name='Test Parent',
            shipping_address_line_1='1 Test Street', shipping_city='Mumbai', shipping_state='Maharashtra', shipping_postal_code='400001',
            subtotal=100, total=100, payment_method='cash_on_delivery')
        OrderItem.objects.create(order=order, product=product, product_variant=variant, product_name='Nutrition fixture', variant_name='5 KG', quantity=1, unit_price=100)
        record_event(order, 'pending')
        CustomerPet.objects.create(user=buyer, name='Bruno', pet_type=PetCategory.objects.create(name='Dog'), breed='Golden retriever')
        WishlistItem.objects.create(user=buyer, product=product)
        CustomerAddress.objects.create(user=buyer, full_name='Test Parent', phone='9876543210', address_line_1='1 Test Street', city='Mumbai', state='Maharashtra', postal_code='400001')
        SupportRequest.objects.create(user=buyer, order=order, category='delivery', subject='Delivery question', message='Please confirm the delivery address.')
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('account_browser_test.cjs')), self.live_server_url, str(order.pk)], capture_output=True, text=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

"""Complete UI journey with a simulated Razorpay adapter, never a real charge."""
import os
import json
import subprocess
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import override_settings
from shop.models import Category, Product, ProductVariant, Order, PaymentAttempt, OrderNotification
from shop.test_purchase_flow import TEST_CONFIG


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Enable browser runtime for simulated payment UI test.')
@override_settings(**TEST_CONFIG)
class PurchaseBrowserTests(StaticLiveServerTestCase):
    def test_signed_payment_ui_to_crm_account_and_admin_email(self):
        get_user_model().objects.create_user('flow-buyer', email='flow@example.com', password='Flow-fixture-921!')
        get_user_model().objects.create_superuser('flow-staff', email='staff@example.com', password='Flow-fixture-921!')
        product = Product.objects.create(name='Complete flow fixture', slug='complete-flow-fixture', category=Category.objects.create(name='Dog'), base_price='3500')
        small = ProductVariant.objects.create(product=product, name='1.5 KG', selling_price='1050', stock_quantity=10)
        large = ProductVariant.objects.create(product=product, name='5 KG', selling_price='2950', stock_quantity=3)
        def gateway(path, payload=None):
            if payload is not None:
                return {**payload, 'id':'order_browser'}
            attempt = PaymentAttempt.objects.get()
            if path.startswith('payments/'):
                return {'id':'pay_browser','order_id':'order_browser','status':'captured','captured':True,'currency':'INR','amount':attempt.amount}
            return {'id':'order_browser','status':'paid','amount':attempt.amount,'amount_paid':attempt.amount,'currency':'INR'}
        with patch('shop.services.payments.api', side_effect=gateway):
            result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('purchase_browser_test.cjs')), self.live_server_url], capture_output=True, text=True, timeout=150)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get(); self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.items.get().product_variant_id, large.pk)
        large.refresh_from_db(); small.refresh_from_db()
        self.assertEqual(large.stock_quantity, 2); self.assertEqual(small.stock_quantity, 10)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(OrderNotification.objects.filter(state='sent').count(), 1)
        preview = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('email_browser_test.cjs'))],
            input=json.dumps([message.alternatives[0].content for message in mail.outbox]), capture_output=True, text=True, timeout=45)
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)

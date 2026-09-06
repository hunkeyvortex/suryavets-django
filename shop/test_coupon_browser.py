"""Create/edit a coupon through CRM, redeem it through the real checkout UI."""
import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from shop.models import Category, Coupon, Order, Product


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set SURYA_BROWSER_NODE for coupon browser verification.')
class CouponBrowserTests(StaticLiveServerTestCase):
    def test_coupon_crm_and_checkout(self):
        get_user_model().objects.create_superuser('coupon-browser-staff', 'fixture@example.com', 'Coupon-browser-fixture-482!')
        product = Product.objects.create(name='Browser checkout fixture', category=Category.objects.create(name='Dog'),
            slug='browser-checkout-fixture', base_price=100, selling_price=90, stock_quantity=5)
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('checkout_browser_test.cjs')),
                                 self.live_server_url, 'coupons'], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        order = Order.objects.get()
        self.assertEqual(order.discount_amount, 27)
        self.assertEqual(order.total, 203)
        self.assertEqual(order.coupon_code, 'BROWSER15')
        self.assertEqual(Coupon.objects.get().used_count, 1)
        self.assertEqual(Coupon.objects.get().activity.count(), 2)
        product.refresh_from_db(); self.assertEqual(product.stock_quantity, 3)

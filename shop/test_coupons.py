from datetime import timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import time
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core.management import call_command
from django.db import close_old_connections, OperationalError, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from shop.crm_forms import CouponForm
from shop.models import Cart, CartItem, Coupon, Order, Product, Category
from shop.forms import CheckoutForm
from shop.services.cart import cart_items
from shop.services.checkout import CheckoutError, place_order, review_token
from shop.services.coupons import CouponError, reserve_coupon
from shop.test_checkout import CHECKOUT_DATA


class CouponCheckoutTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Coupon fixture', category=Category.objects.create(name='Dog'), base_price=100, stock_quantity=10)
        self.coupon = Coupon.objects.create(code='care10', name='Fixture campaign', kind='percent', value=10, is_active=True)
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 2})
        self.cart = Cart.objects.get()

    def apply(self, code='CARE10', **data):
        return self.client.post(reverse('shop:checkout'), {'action': 'apply_coupon', 'coupon_code': code, **data})

    def place(self, token, code='CARE10', **data):
        return self.client.post(reverse('shop:checkout'), {**CHECKOUT_DATA, 'coupon_code': code, 'checkout_token': token, **data})

    def test_apply_preserves_fields_without_creating_order_or_consuming_usage(self):
        response = self.apply(shipping_name='Keep my name', email='keep@example.com', billing_same_as_shipping='on')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Keep my name"')
        self.assertNotContains(response, 'This field is required.')
        self.assertEqual(response.context['discount_amount'], Decimal('20.00'))
        self.assertEqual(response.context['total'], Decimal('230.00'))
        self.assertFalse(Order.objects.exists())
        self.coupon.refresh_from_db(); self.assertEqual(self.coupon.used_count, 0)

    def test_valid_coupon_saves_exact_snapshot_and_duplicate_is_idempotent(self):
        token = self.apply(' care10 ').context['checkout_token']
        first = self.place(token)
        self.assertEqual(first.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.discount_amount, Decimal('20.00'))
        self.assertEqual(order.total, Decimal('230.00'))
        self.assertEqual(order.coupon_code, 'CARE10')
        self.assertEqual(order.coupon, self.coupon)
        self.assertEqual(self.place(token).url, first.url)
        self.coupon.refresh_from_db(); self.assertEqual(self.coupon.used_count, 1)
        self.assertContains(self.client.get(first.url), 'CARE10')
        self.coupon.value = 50; self.coupon.save()
        order.refresh_from_db(); self.assertEqual(order.discount_amount, Decimal('20.00'))

    def test_remove_coupon_preserves_form_and_restores_total(self):
        response = self.client.post(reverse('shop:checkout'), {'action': 'remove_coupon', 'coupon_code': 'CARE10', 'shipping_name': 'Still here'})
        self.assertContains(response, 'value="Still here"')
        self.assertEqual(response.context['discount_amount'], 0)
        self.assertEqual(response.context['total'], 250)
        self.assertIsNone(response.context['coupon'])

    def test_applied_coupon_survives_refresh_and_removal_clears_it(self):
        self.apply()
        response = self.client.get(reverse('shop:checkout'))
        self.assertEqual(response.context['discount_amount'], 20)
        self.assertContains(response, 'value="CARE10"')
        self.client.post(reverse('shop:checkout'), {'action': 'remove_coupon'})
        self.assertEqual(self.client.get(reverse('shop:checkout')).context['discount_amount'], 0)

    def test_invalid_expired_scheduled_minimum_and_exhausted_codes(self):
        self.assertContains(self.apply('MISSING'), 'invalid or is not active')
        self.coupon.ends_at = timezone.now() - timedelta(minutes=1); self.coupon.save()
        self.assertContains(self.apply(), 'has expired')
        self.coupon.ends_at = None; self.coupon.starts_at = timezone.now() + timedelta(days=1); self.coupon.save()
        self.assertContains(self.apply(), 'not available yet')
        self.coupon.starts_at = None; self.coupon.minimum_subtotal = 500; self.coupon.save()
        self.assertContains(self.apply(), 'at least')
        self.coupon.minimum_subtotal = 0; self.coupon.max_uses = 1; self.coupon.used_count = 1; self.coupon.save()
        self.assertContains(self.apply(), 'usage limit')
        self.assertFalse(Order.objects.exists())

    def test_fixed_discount_is_capped_at_subtotal_not_shipping(self):
        self.coupon.kind = 'fixed'; self.coupon.value = 500; self.coupon.save()
        response = self.apply()
        self.assertEqual(response.context['discount_amount'], 200)
        self.assertEqual(response.context['total'], 50)

    def test_percentage_cap_and_decimal_rounding(self):
        self.coupon.value = Decimal('12.34'); self.coupon.maximum_discount = 20; self.coupon.save()
        self.assertEqual(self.apply().context['discount_amount'], 20)
        self.coupon.maximum_discount = None; self.coupon.save()
        self.assertEqual(self.apply().context['discount_amount'], Decimal('24.68'))

    def test_shipping_threshold_is_before_coupon(self):
        self.cart.items.update(quantity=5)
        response = self.apply()
        self.assertEqual(response.context['shipping'], 0)
        self.assertEqual(response.context['total'], 450)

    def test_changed_disabled_or_exhausted_coupon_requires_review(self):
        token = self.apply().context['checkout_token']
        self.coupon.value = 15; self.coupon.save()
        self.assertContains(self.place(token), 'coupon changed')
        self.assertFalse(Order.objects.exists())
        token = self.apply().context['checkout_token']
        self.coupon.is_active = False; self.coupon.save()
        self.assertContains(self.place(token), 'not active')
        self.assertFalse(Order.objects.exists())

    def test_injected_coupon_or_browser_discount_cannot_change_reviewed_total(self):
        token = self.client.get(reverse('shop:checkout')).context['checkout_token']
        self.assertContains(self.place(token, discount_amount='199'), 'coupon changed')
        response = self.place(token, code='', discount_amount='199', total='1')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.get().total, 250)

    def test_stock_failure_rolls_back_coupon_reservation(self):
        token = self.apply().context['checkout_token']
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=1)
        self.assertContains(self.place(token), 'not enough stock')
        self.coupon.refresh_from_db(); self.assertEqual(self.coupon.used_count, 0)
        self.assertFalse(Order.objects.exists())

    def test_usage_reservation_rechecks_limit(self):
        self.coupon.max_uses = 1; self.coupon.save()
        with transaction.atomic():
            reserve_coupon(self.coupon)
            with self.assertRaises(CouponError):
                reserve_coupon(self.coupon)
        self.coupon.refresh_from_db(); self.assertEqual(self.coupon.used_count, 1)

    def test_coupon_application_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('shop:checkout'), {'action': 'apply_coupon', 'coupon_code': 'CARE10'}).status_code, 403)


class CouponCRMTests(TestCase):
    def setUp(self):
        call_command('setup_crm_roles', verbosity=0)
        self.manager = get_user_model().objects.create_user('coupon-manager', is_staff=True)
        self.manager.groups.add(Group.objects.get(name='Surya CRM Manager'))
        self.viewer = get_user_model().objects.create_user('coupon-viewer', is_staff=True)
        self.viewer.groups.add(Group.objects.get(name='Surya CRM Viewer'))
        self.data = {'code': 'hello10', 'name': 'Welcome fixture', 'kind': 'percent', 'value': '10', 'minimum_subtotal': '100', 'is_active': 'on'}

    def test_manager_creates_edits_and_disables_with_history(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.post(reverse('crm:coupon_create'), self.data).status_code, 302)
        coupon = Coupon.objects.get(code='HELLO10')
        self.assertEqual(coupon.activity.count(), 1)
        self.assertEqual(self.client.post(reverse('crm:coupon_edit', args=[coupon.pk]), {**self.data, 'value': '15', 'version': coupon.updated_at.isoformat()}).status_code, 302)
        coupon.refresh_from_db(); self.assertEqual(coupon.value, 15)
        payload = {**self.data, 'version': coupon.updated_at.isoformat()}; payload.pop('is_active')
        self.client.post(reverse('crm:coupon_edit', args=[coupon.pk]), payload)
        coupon.refresh_from_db(); self.assertFalse(coupon.is_active)
        self.assertEqual(coupon.activity.count(), 3)

    def test_viewer_can_read_but_cannot_edit_and_post_requires_csrf(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse('crm:coupons')).status_code, 200)
        self.assertEqual(self.client.get(reverse('crm:coupon_create')).status_code, 403)
        self.assertEqual(self.client.post(reverse('crm:coupon_create'), self.data).status_code, 403)
        client = Client(enforce_csrf_checks=True); client.force_login(self.manager)
        self.assertEqual(client.post(reverse('crm:coupon_create'), self.data).status_code, 403)

    def test_invalid_rules_and_duplicate_codes_rejected(self):
        for changes in [{'value': '101'}, {'value': '-1'}, {'max_uses': '0'}, {'minimum_subtotal': '-1'},
                        {'maximum_discount': '0'}, {'code': 'bad space'}, {'starts_at': '2026-09-10T10:00', 'ends_at': '2026-09-09T10:00'}]:
            form = CouponForm({**self.data, **changes})
            self.assertFalse(form.is_valid(), changes)
        Coupon.objects.create(code='HELLO10', name='Existing', kind='percent', value=10)
        self.assertFalse(CouponForm(self.data).is_valid())

    def test_stale_edit_does_not_overwrite_and_uses_cannot_be_reset(self):
        coupon = Coupon.objects.create(code='HELLO10', name='Existing', kind='percent', value=10)
        old_version = coupon.updated_at.isoformat()
        coupon.value = 20; coupon.used_count = 2; coupon.save()
        self.client.force_login(self.manager)
        response = self.client.post(reverse('crm:coupon_edit', args=[coupon.pk]), {**self.data, 'version': old_version, 'used_count': '0'})
        self.assertContains(response, 'Another staff member edited')
        coupon.refresh_from_db(); self.assertEqual(coupon.value, 20); self.assertEqual(coupon.used_count, 2)
        self.assertFalse(CouponForm({**self.data, 'max_uses': '1', 'version': coupon.updated_at.isoformat()}, instance=coupon).is_valid())


class CouponConcurrencyTests(TransactionTestCase):
    def test_two_carts_cannot_consume_the_last_coupon_use(self):
        product = Product.objects.create(name='Concurrent coupon', category=Category.objects.create(name='Dog'), base_price=100, stock_quantity=10)
        coupon = Coupon.objects.create(code='ONCE', name='One use fixture', value=10, max_uses=1, is_active=True)
        form = CheckoutForm({**CHECKOUT_DATA, 'coupon_code': 'ONCE'})
        self.assertTrue(form.is_valid())
        jobs = []
        for _ in range(2):
            cart = Cart.objects.create()
            CartItem.objects.create(cart=cart, product=product, quantity=1)
            jobs.append((cart.pk, review_token(cart, list(cart_items(cart)), 'ONCE')))
        barrier = Barrier(2)

        def worker(job):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                for attempt in range(12):
                    try:
                        place_order(Cart.objects.get(pk=job[0]), AnonymousUser(), job[1], form.cleaned_data)
                        return 'placed'
                    except CheckoutError:
                        return 'unavailable'
                    except OperationalError:
                        time.sleep(.02 * (attempt + 1))
                return 'busy'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(worker, jobs))
        self.assertEqual(outcomes.count('placed'), 1, outcomes)
        self.assertEqual(Order.objects.count(), 1)
        coupon.refresh_from_db(); product.refresh_from_db()
        self.assertEqual(coupon.used_count, 1)
        self.assertEqual(product.stock_quantity, 9)

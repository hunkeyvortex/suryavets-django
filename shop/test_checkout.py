from decimal import Decimal
import time
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import signing
from django.db import OperationalError, connections, close_old_connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from shop.forms import CheckoutForm
from shop.models import Cart, CartItem, Category, Order, OrderItem, Product, ProductVariant
from shop.services.cart import cart_items
from shop.services.checkout import CheckoutError, place_order, review_token

CHECKOUT_DATA = {
    'email': 'buyer@example.com', 'phone': '9999999999', 'shipping_name': 'Test Buyer',
    'shipping_address_line_1': '1 Test Street', 'shipping_city': 'Mumbai',
    'shipping_state': 'Maharashtra', 'shipping_postal_code': '400001',
    'billing_same_as_shipping': 'on', 'payment_method': 'cash_on_delivery', 'terms': 'on',
}


class CheckoutSafetyTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Checkout test', category=Category.objects.create(name='Dog'),
            base_price='100', selling_price='90', stock_quantity=5)
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 2})
        self.cart = Cart.objects.get()
        self.token = self.client.get(reverse('shop:checkout')).context['checkout_token']

    def submit(self, **overrides):
        return self.client.post(reverse('shop:checkout'), {**CHECKOUT_DATA, 'checkout_token': self.token, **overrides})

    def test_order_is_atomic_and_repeated_submission_returns_same_receipt(self):
        first = self.submit()
        self.assertEqual(first.status_code, 302)
        order = Order.objects.get()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(order.subtotal, Decimal('180'))
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertTrue(order.stock_deducted)
        self.assertFalse(self.cart.items.exists())
        self.assertEqual(self.submit().url, first.url)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db(); self.assertEqual(self.product.stock_quantity, 3)
        receipt = self.client.get(first.url)
        self.assertContains(receipt, order.order_number)
        self.assertEqual(receipt['Cache-Control'], 'private, no-store')

    def test_duplicate_old_token_does_not_clear_new_cart_items(self):
        self.submit()
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 1})
        self.submit()
        self.assertEqual(self.cart.items.get().quantity, 1)
        self.assertEqual(Order.objects.count(), 1)

    def test_shortage_blocks_order_and_preserves_cart(self):
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=1)
        self.assertContains(self.submit(), 'not enough stock')
        self.assertFalse(Order.objects.exists())
        self.assertTrue(self.cart.items.exists())
        self.product.refresh_from_db(); self.assertEqual(self.product.stock_quantity, 1)

    def test_price_changes_require_fresh_review(self):
        Product.objects.filter(pk=self.product.pk).update(selling_price='95')
        response = self.submit()
        self.assertContains(response, 'prices changed')
        self.assertFalse(Order.objects.exists())
        self.token = response.context['checkout_token']
        self.assertEqual(self.submit().status_code, 302)
        self.assertEqual(Order.objects.get().subtotal, Decimal('190'))

    def test_quantity_changes_require_fresh_review(self):
        self.cart.items.update(quantity=3)
        self.assertContains(self.submit(), 'prices changed')
        self.assertFalse(Order.objects.exists())

    def test_invalid_missing_expired_or_foreign_tokens_do_not_create_orders(self):
        for token in ('', 'tampered'):
            self.assertContains(self.submit(checkout_token=token), 'expired or is invalid')
        with patch('django.core.signing.time.time', return_value=time.time() - 3601):
            expired = review_token(self.cart, list(cart_items(self.cart)))
        self.assertContains(self.submit(checkout_token=expired), 'expired or is invalid')
        self.assertContains(self.client.post(reverse('shop:checkout'), CHECKOUT_DATA), 'expired or is invalid')
        foreign_cart = Cart.objects.create()
        foreign = review_token(foreign_cart, [])
        self.assertContains(self.submit(checkout_token=foreign), 'expired or is invalid')
        self.assertFalse(Order.objects.exists())

    def test_inactive_product_and_invalid_variant_are_rejected(self):
        self.product.is_active = False; self.product.save()
        self.assertContains(self.submit(), 'no longer available')
        self.product.is_active = True; self.product.save()
        other = Product.objects.create(name='Other', category=self.product.category, base_price=1)
        variant = ProductVariant.objects.create(product=other, name='Other pack', stock_quantity=5)
        self.cart.items.update(product_variant=variant)
        self.assertContains(self.submit(), 'selected pack is no longer available')
        self.assertFalse(Order.objects.exists())

    def test_variant_stock_deducted_and_parent_counter_updated(self):
        variant = ProductVariant.objects.create(product=self.product, name='Pack', price_override=100, selling_price=90, stock_quantity=5)
        self.cart.items.update(product_variant=variant)
        self.token = self.client.get(reverse('shop:checkout')).context['checkout_token']
        self.assertEqual(self.submit().status_code, 302)
        variant.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual(variant.stock_quantity, 3)
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(OrderItem.objects.get().product_variant_id, variant.pk)

    def test_duplicate_cart_lines_cannot_bypass_stock_limit(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=4)
        self.token = self.client.get(reverse('shop:checkout')).context['checkout_token']
        self.assertContains(self.submit(), 'not enough stock')
        self.product.refresh_from_db(); self.assertEqual(self.product.stock_quantity, 5)

    def test_untracked_simple_product_does_not_change_inventory(self):
        self.product.track_inventory = False; self.product.stock_quantity = 0; self.product.save()
        self.assertEqual(self.submit().status_code, 302)
        self.product.refresh_from_db(); self.assertEqual(self.product.stock_quantity, 0)
        self.assertFalse(Order.objects.get().stock_deducted)

    def test_failed_order_write_rolls_back_stock(self):
        with patch('shop.services.checkout.OrderItem.objects.bulk_create', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                self.submit()
        self.product.refresh_from_db(); self.assertEqual(self.product.stock_quantity, 5)
        self.assertFalse(Order.objects.exists()); self.assertTrue(self.cart.items.exists())

    def test_transient_database_conflict_returns_retryable_response(self):
        with patch('shop.views.place_order', side_effect=OperationalError('locked')):
            response = self.submit()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.context['checkout_token'], self.token)
        self.assertFalse(Order.objects.exists())

    def test_other_shoppers_cannot_change_cart_or_read_receipt(self):
        outsider = Client()
        item = self.cart.items.get()
        for route in ('shop:update_cart_item', 'shop:remove_from_cart'):
            self.assertEqual(outsider.post(reverse(route, args=[item.pk]), {'quantity': 0}).status_code, 404)
        receipt = self.submit().url
        self.assertEqual(outsider.get(receipt).status_code, 404)

    def test_cart_mutations_require_post_and_safe_return_url(self):
        item = self.cart.items.get()
        for route, pk in (('shop:add_to_cart', self.product.pk), ('shop:update_cart_item', item.pk), ('shop:remove_from_cart', item.pk)):
            self.assertEqual(self.client.get(reverse(route, args=[pk])).status_code, 405)
        response = self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'next': 'https://evil.example/'})
        self.assertEqual(response.url, reverse('shop:cart'))

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {}).status_code, 403)
        self.assertEqual(client.post(reverse('shop:checkout'), CHECKOUT_DATA).status_code, 403)

    def test_reading_empty_cart_does_not_create_a_cart_or_shipping_fee(self):
        user = get_user_model().objects.create_user('reader')
        client = Client(); client.force_login(user)
        response = client.get(reverse('shop:cart'))
        self.assertEqual(response.context['shipping'], Decimal('0'))
        self.assertFalse(Cart.objects.filter(user=user).exists())

    def test_two_independent_carts_cannot_both_buy_last_stock(self):
        self.product.stock_quantity = 2; self.product.save()
        second = Cart.objects.create()
        CartItem.objects.create(cart=second, product=self.product, quantity=2)
        token = review_token(second, list(cart_items(second)))
        self.assertEqual(self.submit().status_code, 302)
        form = CheckoutForm(CHECKOUT_DATA); self.assertTrue(form.is_valid())
        with self.assertRaises(CheckoutError):
            place_order(second, AnonymousUser(), token, form.cleaned_data)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db(); self.assertEqual(self.product.stock_quantity, 0)

    def test_authenticated_order_and_history_are_scoped_to_owner(self):
        owner = get_user_model().objects.create_user('owner')
        self.client.force_login(owner)
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 1})
        self.token = self.client.get(reverse('shop:checkout')).context['checkout_token']
        response = self.submit()
        order = Order.objects.get()
        self.assertEqual(order.user_id, owner.pk)
        self.assertEqual(self.client.get(response.url).status_code, 200)
        self.assertContains(self.client.get(reverse('shop:profile')), order.order_number)
        outsider = get_user_model().objects.create_user('outsider')
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(response.url).status_code, 404)
        self.assertEqual(self.client.get(reverse('shop:order_detail', args=[order.pk])).status_code, 404)


class ConcurrentCheckoutTests(TransactionTestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Last unit', category=Category.objects.create(name='Dog'), base_price=100, stock_quantity=1)
        self.carts = [Cart.objects.create(), Cart.objects.create()]
        for cart in self.carts:
            CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.tokens = [review_token(cart, list(cart_items(cart))) for cart in self.carts]
        form = CheckoutForm(CHECKOUT_DATA); form.is_valid(); self.data = form.cleaned_data

    def run_race(self, same_cart):
        barrier = Barrier(2)
        def buy(index):
            close_old_connections()
            try:
                slot = 0 if same_cart else index
                barrier.wait(timeout=10)
                order = place_order(self.carts[slot], AnonymousUser(), self.tokens[slot], self.data)
                return str(order.pk)
            except (CheckoutError, OperationalError):
                return None  # Busy SQLite requests are safely retryable.
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(buy, i) for i in range(2)]
            results = [future.result(timeout=15) for future in futures]
        # Retry failed requests after contention, as the UI permits.
        for slot in ([0, 0] if same_cart else [0, 1]):
            try:
                place_order(self.carts[slot], AnonymousUser(), self.tokens[slot], self.data)
            except CheckoutError:
                pass
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db(); self.assertEqual(self.product.stock_quantity, 0)
        self.assertLessEqual(len({value for value in results if value}), 1)

    def test_two_carts_race_for_one_unit(self):
        self.run_race(same_cart=False)

    def test_duplicate_requests_race_for_one_order(self):
        self.run_race(same_cart=True)

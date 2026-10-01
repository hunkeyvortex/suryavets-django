from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .models import Cart, CartItem, Category, Product, ProductVariant


class CartAutosaveTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Food', category=Category.objects.create(name='Dog'), base_price=100, stock_quantity=10)
        self.pack = ProductVariant.objects.create(product=self.product, name='3 KG', selling_price=90, stock_quantity=8)
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'variant_id': self.pack.pk})
        self.item = CartItem.objects.get()
        self.url = reverse('shop:update_cart_item', args=[self.item.pk])

    def update(self, quantity, client=None):
        return (client or self.client).post(self.url, {'quantity': quantity}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_autosave_returns_exact_server_totals_and_counts(self):
        response = self.update(3)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['subtotal'], '₹270.00')
        self.assertEqual(data['shipping'], '₹50.00')
        self.assertEqual(data['total'], '₹320.00')
        self.assertEqual(data['total_items'], 3)
        self.assertEqual(data['items'][0]['quantity'], 3)
        self.assertEqual(data['items'][0]['unit_price'], '₹90.00')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 3)
        self.assertEqual(self.item.product_variant, self.pack)

    def test_shipping_threshold_updates_in_both_directions(self):
        data = self.update(6).json()
        self.assertTrue(data['free_delivery'])
        self.assertEqual(data['total'], '₹540.00')
        data = self.update(1).json()
        self.assertFalse(data['free_delivery'])
        self.assertEqual(data['delivery_remaining'], '₹409.00')

    def test_overstock_preserves_quantity_and_returns_current_snapshot(self):
        self.update(3)
        response = self.update(9)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])
        self.assertEqual(response.json()['items'][0]['quantity'], 3)
        self.assertEqual(response.json()['total'], '₹320.00')

    def test_invalid_quantities_do_not_mutate_or_remove_items(self):
        for value in ('', 'abc', '1.5', 0, -1, 10001):
            with self.subTest(value=value):
                self.assertEqual(self.update(value).status_code, 400)
                self.item.refresh_from_db()
                self.assertEqual(self.item.quantity, 1)

    def test_other_sessions_cannot_edit_or_read_cart_totals(self):
        response = self.update(3, Client())
        self.assertEqual(response.status_code, 404)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 1)

    def test_authenticated_cart_is_ownership_scoped(self):
        owner = get_user_model().objects.create_user(username='owner', password='test-only')
        other = get_user_model().objects.create_user(username='other', password='test-only')
        cart = self.item.cart
        cart.user = owner
        cart.save()
        self.client.force_login(other)
        self.assertEqual(self.update(2).status_code, 404)
        self.client.force_login(owner)
        self.assertEqual(self.update(2).status_code, 200)

    def test_csrf_and_post_are_still_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(self.update(2, client).status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_normal_post_remains_available_without_javascript(self):
        response = self.client.post(self.url, {'quantity': 2})
        self.assertRedirects(response, reverse('shop:cart'))
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 2)

    def test_repeat_absolute_update_is_idempotent_and_stock_is_not_reserved(self):
        self.update(3)
        self.update(3)
        self.item.refresh_from_db()
        self.pack.refresh_from_db()
        self.assertEqual(self.item.quantity, 3)
        self.assertEqual(self.pack.stock_quantity, 8)

    def test_snapshot_includes_other_lines_and_uses_current_prices(self):
        other = Product.objects.create(name='Other', category=self.product.category, base_price=Decimal('19.95'), stock_quantity=2)
        CartItem.objects.create(cart=self.item.cart, product=other, quantity=2)
        self.pack.selling_price = Decimal('89.95')
        self.pack.save()
        data = self.update(2).json()
        self.assertEqual(data['subtotal'], '₹219.80')
        self.assertEqual(data['total_items'], 4)
        self.assertEqual(len(data['items']), 2)

"""Purchase policy regressions; all writes are isolated to the test database."""
from decimal import Decimal
from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from shop.models import Category, Product, ProductVariant, Cart, CartItem, Order, OrderItem, InventoryMovement, CatalogReviewEvent
from shop.services.purchasing import purchase_state
from shop.services.cart import cart_items, SESSION_CART_KEY
from shop.services.checkout import place_order, review_token, CheckoutError
from shop.services.reorder import buy_again
from shop.services.accounts import merge_guest_cart, CartMergeError
from shop.services.variants import card_offer, variant_options
from shop.services.pricing import catalog_price_expression
from shop.test_checkout import CHECKOUT_DATA


class PurchasePolicyTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Safety food', category=Category.objects.create(name='Dog'), base_price=200, stock_quantity=10)
        self.valid = ProductVariant.objects.create(product=self.product, name='1 KG', selling_price=180, stock_quantity=10, quantity=1, unit='kg', comparison_group='food')
        self.zero = ProductVariant.objects.create(product=self.product, name='4 KG', selling_price=0, stock_quantity=10, quantity=4, unit='kg', comparison_group='food')
        self.user = get_user_model().objects.create_user(username='buyer', password='test-password')

    def post(self, variant, **extra):
        return self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'variant_id': variant.pk, 'quantity': 1, **extra})

    def test_crafted_zero_and_buy_now_requests_rejected(self):
        for intent in ('', 'buy_now'):
            self.post(self.zero, intent=intent)
            self.assertFalse(CartItem.objects.exists())

    def test_negative_inactive_and_out_of_stock_rejected(self):
        for fields in ({'selling_price': -1}, {'selling_price': 180, 'is_active': False}, {'is_active': True, 'stock_quantity': 0}):
            ProductVariant.objects.filter(pk=self.valid.pk).update(**fields)
            self.post(self.valid)
            self.assertFalse(CartItem.objects.exists())

    def test_positive_exact_pack_works_without_touching_stock(self):
        self.post(self.valid)
        self.assertEqual(CartItem.objects.get().product_variant_id, self.valid.pk)
        self.valid.refresh_from_db()
        self.assertEqual(self.valid.stock_quantity, 10)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_wrong_relationship_and_missing_pack_rejected(self):
        other = Product.objects.create(name='Other', category=self.product.category, base_price=200)
        foreign = ProductVariant.objects.create(product=other, name='Pack', selling_price=100, stock_quantity=10)
        self.post(foreign)
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 1})
        self.assertFalse(CartItem.objects.exists())

    def test_simple_zero_cannot_purchase(self):
        simple = Product.objects.create(name='Zero simple', category=self.product.category, base_price=200, selling_price=0, stock_quantity=10)
        self.client.post(reverse('shop:add_to_cart', args=[simple.pk]), {'quantity': 1})
        self.assertFalse(CartItem.objects.exists())

    def test_explicit_hold_and_inactive_parent_rejected(self):
        CatalogReviewEvent.objects.create(product=self.product, decision='held', evidence='Needs owner review')
        self.post(self.valid)
        self.assertFalse(CartItem.objects.exists())
        CatalogReviewEvent.objects.create(product=self.product, decision='approved', evidence='Test approval')
        self.assertTrue(purchase_state(self.product, self.valid).allowed)
        self.assertFalse(purchase_state(self.product, self.zero).allowed)
        self.product.is_active = False
        self.assertFalse(purchase_state(self.product, self.valid).allowed)

    def test_family_hold_and_sql_match(self):
        member = Product.objects.create(name='Family child', category=self.product.category, base_price=200, variant_family=self.product)
        pack = ProductVariant.objects.create(product=member, name='5 KG', selling_price=150, stock_quantity=10)
        CatalogReviewEvent.objects.create(product=self.product, decision='held', evidence='Hold family')
        self.assertFalse(purchase_state(member, pack).allowed)
        self.assertIsNone(Product.objects.annotate(offer=catalog_price_expression()).get(pk=self.product.pk).offer)

    def test_existing_cart_ajax_and_checkout_revalidated(self):
        self.post(self.valid)
        item = CartItem.objects.get()
        token = self.client.get(reverse('shop:checkout')).context['checkout_token']
        ProductVariant.objects.filter(pk=self.valid.pk).update(selling_price=0)
        response = self.client.post(reverse('shop:update_cart_item', args=[item.pk]), {'quantity': 2}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)
        self.assertContains(self.client.get(reverse('shop:checkout')), 'Price unavailable')
        self.assertContains(self.client.post(reverse('shop:checkout'), {**CHECKOUT_DATA, 'checkout_token': token}), 'Price unavailable')
        self.assertFalse(Order.objects.exists())

    def test_service_atomic_rejection_preserves_all_lines_and_ledger(self):
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=self.product, product_variant=self.valid, quantity=1)
        CartItem.objects.create(cart=cart, product=self.product, product_variant=self.zero, quantity=1)
        token = review_token(cart, list(cart_items(cart)))
        before = list(ProductVariant.objects.values_list('pk', 'selling_price', 'stock_quantity'))
        with self.assertRaisesMessage(CheckoutError, 'Price unavailable'):
            place_order(cart, AnonymousUser(), token, CHECKOUT_DATA)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.assertFalse(InventoryMovement.objects.exists())
        self.assertEqual(cart.items.count(), 2)
        self.assertEqual(before, list(ProductVariant.objects.values_list('pk', 'selling_price', 'stock_quantity')))

    def test_checkout_revalidates_each_changed_catalog_state(self):
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=self.product, product_variant=self.valid, quantity=1)
        token = review_token(cart, list(cart_items(cart)))
        for changes in ({'is_active': False}, {'selling_price': -1}, {'stock_quantity': 0}):
            ProductVariant.objects.filter(pk=self.valid.pk).update(is_active=True, selling_price=180, stock_quantity=10)
            ProductVariant.objects.filter(pk=self.valid.pk).update(**changes)
            with self.subTest(changes=changes), self.assertRaises(CheckoutError):
                place_order(cart, AnonymousUser(), token, CHECKOUT_DATA)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(InventoryMovement.objects.exists())

    def test_invalid_cart_cannot_consume_coupon(self):
        from shop.models import Coupon
        coupon = Coupon.objects.create(code='SAFETY10', name='Safety fixture', kind='percent', value=10, is_active=True)
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=self.product, product_variant=self.valid, quantity=1)
        token = review_token(cart, list(cart_items(cart)), coupon.code)
        ProductVariant.objects.filter(pk=self.valid.pk).update(selling_price=0)
        with self.assertRaises(CheckoutError):
            place_order(cart, AnonymousUser(), token, {**CHECKOUT_DATA, 'coupon_code': coupon.code})
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 0)
        self.assertFalse(Order.objects.exists())

    def test_reorder_skips_exact_invalid_pack_and_uses_current_price(self):
        order = Order.objects.create(user=self.user, subtotal=10, total=10)
        for pack in (self.zero, self.valid):
            OrderItem.objects.create(order=order, product=self.product, product_variant=pack, product_name=self.product.name, variant_name=pack.name, quantity=1, unit_price=5)
        added, skipped = buy_again(self.user, order.pk)
        self.assertEqual(added, 1)
        self.assertEqual(len(skipped), 1)
        item = CartItem.objects.get()
        self.assertEqual(item.product_variant_id, self.valid.pk)
        self.assertEqual(item.product_variant.current_price, Decimal('180'))

    def test_login_merge_rejects_invalid_guest_cart_atomically(self):
        guest = Cart.objects.create()
        CartItem.objects.create(cart=guest, product=self.product, product_variant=self.zero, quantity=1)
        with self.assertRaises(CartMergeError):
            merge_guest_cart(SimpleNamespace(session={SESSION_CART_KEY: str(guest.pk)}), self.user)
        self.assertEqual(guest.items.count(), 1)
        self.assertFalse(Cart.objects.filter(user=self.user).exists())

    def test_merchandising_excludes_zero_and_all_invalid_is_unavailable(self):
        self.assertEqual(card_offer(self.product)['price'], Decimal('180'))
        options = variant_options(self.product, [self.valid, self.zero])
        self.assertFalse(options[1]['available'])
        self.assertFalse(options[1]['best_value'])
        self.assertEqual(options[1]['saving'], 0)
        self.assertEqual(Product.objects.annotate(offer=catalog_price_expression()).get(pk=self.product.pk).offer, 180)
        ProductVariant.objects.filter(product=self.product).update(selling_price=0)
        self.assertIsNone(card_offer(self.product)['price'])
        self.assertContains(self.client.get(reverse('shop:product_detail', args=[self.product.slug])), 'Currently unavailable')

    def test_family_with_empty_sibling_never_falls_back_to_base_price(self):
        member = Product.objects.create(name='Empty sibling', category=self.product.category, base_price=300, variant_family=self.product)
        self.assertEqual(purchase_state(member).code, 'variant_required')
        ProductVariant.objects.filter(product=self.product).update(selling_price=0)
        self.assertIsNone(Product.objects.annotate(offer=catalog_price_expression()).get(pk=self.product.pk).offer)

    def test_crm_filters_and_reason_require_authorization(self):
        url = reverse('crm:inventory')
        self.assertNotEqual(self.client.get(url, {'safety': 'zero'}).status_code, 200)
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        self.assertContains(self.client.get(url, {'safety': 'zero'}), self.product.name)
        response = self.client.get(url, {'safety': 'blocked'})
        self.assertNotContains(response, self.product.name)
        ProductVariant.objects.filter(product=self.product).update(selling_price=0)
        self.assertContains(self.client.get(url, {'safety': 'blocked'}), self.product.name)

    def test_legacy_purchase_entry_points_delegate_to_current_views(self):
        from shop import views, views_new
        for name in ('add_to_cart', 'cart_detail', 'update_cart_item', 'remove_from_cart', 'checkout'):
            self.assertIs(getattr(views_new, name), getattr(views, name))

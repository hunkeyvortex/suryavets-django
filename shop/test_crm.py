from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db.models import F
from django.test import Client, TestCase
from django.urls import reverse

from shop.models import Cart, CartItem, Category, CRMActivity, InventoryMovement, Order, Product, ProductVariant
from shop.services.crm import CRMError, adjustment_token, adjust_inventory, transition_order
from shop.test_checkout import CHECKOUT_DATA


class CRMTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_crm_roles', verbosity=0)
        cls.manager = get_user_model().objects.create_user('manager', password='Fixture-password-42!', is_staff=True)
        cls.manager.groups.add(Group.objects.get(name='Surya CRM Manager'))
        cls.viewer = get_user_model().objects.create_user('viewer', is_staff=True)
        cls.viewer.groups.add(Group.objects.get(name='Surya CRM Viewer'))
        cls.buyer = get_user_model().objects.create_user('buyer')
        cls.category = Category.objects.create(name='Test category')

    def setUp(self):
        self.product = Product.objects.create(name='CRM test product', category=self.category, base_price=100, stock_quantity=10)

    def checkout(self, product=None, variant=None):
        payload = {'quantity': 2}
        if variant:
            payload['variant_id'] = variant.pk
        response = self.client.post(reverse('shop:add_to_cart', args=[(product or self.product).pk]), payload)
        self.assertEqual(response.status_code, 302)
        token = self.client.get(reverse('shop:checkout')).context['checkout_token']
        self.client.post(reverse('shop:checkout'), {**CHECKOUT_DATA, 'checkout_token': token})
        return Order.objects.latest('created_at')

    def test_customer_and_staff_without_permission_cannot_read_crm(self):
        for name in ['dashboard', 'orders', 'inventory', 'customers', 'reports']:
            self.assertEqual(self.client.get(reverse('crm:' + name)).status_code, 302)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse('crm:dashboard')).status_code, 403)
        self.buyer.is_staff = True
        self.buyer.save()
        self.assertEqual(self.client.get(reverse('crm:dashboard')).status_code, 403)

    def test_all_pages_render_and_private_headers(self):
        order = self.checkout()
        self.client.force_login(self.manager)
        key = signing.dumps(order.email.lower(), salt='surya.crm.customer')
        urls = [reverse('crm:' + name) for name in ['dashboard', 'orders', 'inventory', 'customers', 'reports']]
        urls += [reverse('crm:order_detail', args=[order.pk]), reverse('crm:inventory_detail', args=[self.product.pk]), reverse('crm:customer_detail', args=[key])]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn('private', response['Cache-Control'])
                self.assertIn('no-store', response['Cache-Control'])
                self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')

    def test_checkout_records_deductions_and_cancel_restocks_once(self):
        order = self.checkout()
        self.assertTrue(order.inventory_recorded)
        movement = order.stock_movements.get()
        self.assertEqual((movement.delta, movement.quantity_before, movement.quantity_after), (-2, 10, 8))
        transition_order(self.manager, order.pk, 'pending', 'cancelled', 'Customer requested cancellation')
        transition_order(self.manager, order.pk, 'pending', 'cancelled', 'Repeated submit')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(order.stock_movements.count(), 2)
        self.assertEqual(InventoryMovement.objects.get(kind='cancellation').reversal_of, movement)
        self.assertEqual(order.crm_activity.count(), 1)

    def test_variant_cancellation_uses_original_deduction(self):
        variant = ProductVariant.objects.create(product=self.product, name='Small pack', stock_quantity=5)
        order = self.checkout(variant=variant)
        Product.objects.filter(pk=self.product.pk).update(track_inventory=False)
        transition_order(self.manager, order.pk, 'pending', 'cancelled', 'Wrong pack ordered')
        variant.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual(variant.stock_quantity, 5)
        self.assertEqual(self.product.stock_quantity, 5)

    def test_untracked_product_is_not_invented_on_cancel(self):
        self.product.track_inventory = False
        self.product.save()
        order = self.checkout()
        self.assertFalse(order.stock_deducted)
        transition_order(self.manager, order.pk, 'pending', 'cancelled', 'Customer changed mind')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertFalse(order.stock_movements.exists())

    def test_paid_and_legacy_orders_cannot_auto_cancel(self):
        order = self.checkout()
        Order.objects.filter(pk=order.pk).update(payment_status='paid')
        with self.assertRaises(CRMError):
            transition_order(self.manager, order.pk, 'pending', 'cancelled', 'Requested refund')
        Order.objects.filter(pk=order.pk).update(payment_status='pending', inventory_recorded=False)
        with self.assertRaises(CRMError):
            transition_order(self.manager, order.pk, 'pending', 'cancelled', 'Legacy record')
        order.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(self.product.stock_quantity, 8)

    def test_status_flow_stale_updates_and_payment_guard(self):
        order = self.checkout()
        transition_order(self.manager, order.pk, 'pending', 'processing', 'Preparing shipment')
        with self.assertRaises(CRMError):
            transition_order(self.manager, order.pk, 'pending', 'cancelled', 'Stale page')
        transition_order(self.manager, order.pk, 'processing', 'shipped', 'Handed to courier')
        with self.assertRaises(CRMError):
            transition_order(self.manager, order.pk, 'shipped', 'cancelled', 'Already dispatched')
        transition_order(self.manager, order.pk, 'shipped', 'delivered', 'Delivery confirmed')
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'pending')
        Order.objects.filter(pk=order.pk).update(status='pending', payment_method='manual')
        with self.assertRaises(CRMError):
            transition_order(self.manager, order.pk, 'pending', 'processing', 'Payment not received')

    def test_adjustment_is_audited_and_idempotent(self):
        token = adjustment_token(self.manager, self.product)
        movement = adjust_inventory(self.manager, self.product.pk, None, 3, 'Received supplier stock', token)
        repeated = adjust_inventory(self.manager, self.product.pk, None, 3, 'Repeated request', token)
        self.assertEqual(movement.pk, repeated.pk)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 13)
        self.assertEqual((movement.quantity_before, movement.quantity_after), (10, 13))

    def test_adjustment_refuses_stale_negative_tampered_and_foreign_tokens(self):
        token = adjustment_token(self.manager, self.product)
        with self.assertRaises(CRMError):
            adjust_inventory(self.manager, self.product.pk, None, -11, 'Stock correction', token)
        with self.assertRaises(CRMError):
            adjust_inventory(self.manager, self.product.pk, None, 1, 'Stock correction', 'bad-token')
        with self.assertRaises(CRMError):
            adjust_inventory(self.manager, self.product.pk, None, 1, 'Stock correction', adjustment_token(self.viewer, self.product))
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=F('stock_quantity') - 1)
        with self.assertRaises(CRMError):
            adjust_inventory(self.manager, self.product.pk, None, 1, 'Stock correction', token)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_variant_adjustment_updates_parent_and_rejects_parent_adjustment(self):
        variant = ProductVariant.objects.create(product=self.product, name='Pack', stock_quantity=4)
        adjust_inventory(self.manager, self.product.pk, variant.pk, 2, 'Supplier delivery', adjustment_token(self.manager, self.product, variant))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 6)
        with self.assertRaises(CRMError):
            adjust_inventory(self.manager, self.product.pk, None, 2, 'Wrong level', adjustment_token(self.manager, self.product))

    def test_viewer_cannot_write_and_mutations_require_post_csrf(self):
        order = self.checkout()
        self.client.force_login(self.viewer)
        for url in [reverse('crm:order_status', args=[order.pk]), reverse('crm:order_note', args=[order.pk]), reverse('crm:inventory_detail', args=[self.product.pk])]:
            self.assertEqual(self.client.post(url, {}).status_code, 403)
        with self.assertRaises(PermissionDenied):
            transition_order(self.viewer, order.pk, 'pending', 'cancelled', 'No permission')
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse('crm:order_status', args=[order.pk])).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.manager)
        self.assertEqual(protected.post(reverse('crm:order_status', args=[order.pk]), {}).status_code, 403)

    def test_internal_notes_escaped_and_not_on_receipt(self):
        order = self.checkout()
        guest = Client()
        guest.cookies = self.client.cookies.copy()
        self.client = Client()
        self.client.force_login(self.manager)
        self.client.post(reverse('crm:order_note', args=[order.pk]), {'text': '<script>alert(1)</script> STAFF ONLY'})
        response = self.client.get(reverse('crm:order_detail', args=[order.pk]))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertEqual(CRMActivity.objects.filter(order=order).count(), 1)
        receipt = guest.get(reverse('shop:order_confirmation', args=[order.pk]))
        self.assertEqual(receipt.status_code, 200)
        self.assertNotContains(receipt, 'STAFF ONLY')

    def test_search_filters_pagination_and_guest_contacts(self):
        order = self.checkout()
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse('crm:orders'), {'q': order.order_number}), order.order_number)
        self.assertNotContains(self.client.get(reverse('crm:orders'), {'status': 'delivered'}), order.order_number)
        self.assertContains(self.client.get(reverse('crm:inventory'), {'q': 'CRM test'}), self.product.name)
        self.assertContains(self.client.get(reverse('crm:customers')), CHECKOUT_DATA['email'])
        self.assertEqual(self.client.get(reverse('crm:customers'), {'page': 999}).status_code, 200)
        self.assertEqual(self.client.get(reverse('crm:customer_detail', args=['tampered'])).status_code, 404)

    def test_staff_login_rejects_customers_and_external_redirect(self):
        response = self.client.post(reverse('crm:login') + '?next=https://example.invalid/', {'username': 'manager', 'password': 'Fixture-password-42!'})
        self.assertEqual(response.url, reverse('crm:dashboard'))
        self.assertEqual(self.client.get(reverse('crm:logout')).status_code, 405)

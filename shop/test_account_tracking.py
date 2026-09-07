import io
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.management import call_command, CommandError
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from shop.models import (Order, OrderItem, Product, ProductVariant, Category, PetCategory, CustomerPet,
                         CustomerAddress, WishlistItem, SupportRequest, OrderStatusHistory, OrderNotification, CartItem)
from shop.services.crm import transition_order, CRMError
from shop.services.order_tracking import update_review, record_event
from shop.services.reorder import buy_again


class AccountTrackingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_crm_roles', stdout=io.StringIO())
        cls.user = get_user_model().objects.create_user('account-owner', email='owner@example.com', password='Fixture-care-921!')
        cls.other = get_user_model().objects.create_user('other-owner', email='other@example.com')
        cls.manager = get_user_model().objects.create_user('tracking-manager', is_staff=True)
        cls.manager.groups.add(Group.objects.get(name='Surya CRM Manager'))
        cls.operations = get_user_model().objects.create_user('operations', is_staff=True)
        cls.operations.groups.add(Group.objects.get(name='Surya CRM Operations'))
        cls.viewer = get_user_model().objects.create_user('tracking-viewer', is_staff=True)
        cls.viewer.groups.add(Group.objects.get(name='Surya CRM Viewer'))

    def setUp(self):
        self.client.force_login(self.user)
        self.product = Product.objects.create(name='Current product name', category=Category.objects.create(name='Dog'), base_price=400, stock_quantity=10)
        self.variant = ProductVariant.objects.create(product=self.product, name='5 KG', sku='EXACT-5', selling_price=300, price_override=400, stock_quantity=10)
        self.order = Order.objects.create(user=self.user, email=self.user.email, phone='9876543210', shipping_name='Parent',
            shipping_address_line_1='1 Test Road', shipping_city='Delhi', shipping_state='Delhi', shipping_postal_code='110001',
            subtotal=200, total=200, payment_method='cash_on_delivery')
        self.line = OrderItem.objects.create(order=self.order, product=self.product, product_variant=self.variant,
            product_name='Historical name', variant_name='5 KG', sku='EXACT-5', unit_price=200, quantity=1)
        record_event(self.order, 'pending')

    def url(self, name, *args):
        return reverse('shop:' + name, args=args)

    def advance(self):
        for before, after in [('pending', 'confirmed'), ('confirmed', 'processing'), ('processing', 'packed'), ('packed', 'shipped'), ('shipped', 'out_for_delivery'), ('out_for_delivery', 'delivered')]:
            transition_order(self.manager, self.order.pk, before, after, 'STAFF SECRET', courier='Test Courier', tracking_number='AWB123', tracking_url='https://example.com/track', customer_note='Your order has progressed.')

    def test_all_account_pages_require_authentication_and_no_cache(self):
        for name in ['profile', 'orders', 'pets', 'wishlist', 'addresses', 'profile_edit', 'security', 'support']:
            response = self.client.get(self.url(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')
            self.assertEqual(Client().get(self.url(name)).status_code, 302)

    def test_dashboard_uses_tiles_without_duplicate_navigation(self):
        response = self.client.get(self.url('profile'))
        self.assertNotContains(response, 'class="customer-nav"')
        self.assertContains(response, 'customer-layout--overview')
        self.assertContains(response, 'class="account-tiles"')
        self.assertContains(response, 'Log out', count=1)
        self.assertContains(self.client.get(self.url('orders')), 'class="customer-nav"')

    def test_owned_order_and_number_route_preserve_historical_variant(self):
        for name, identifier in [('order_detail', self.order.pk), ('order_number', self.order.order_number)]:
            response = self.client.get(self.url(name, identifier))
            self.assertContains(response, 'Historical name')
            self.assertContains(response, '5 KG')
            self.assertContains(response, '200.00')
            self.client.force_login(self.other)
            self.assertEqual(self.client.get(self.url(name, identifier)).status_code, 404)
            self.client.force_login(self.user)

    def test_status_updates_share_history_and_hide_internal_notes(self):
        initial = self.order.events.first().timestamp
        self.advance()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'delivered')
        self.assertEqual(self.order.payment_status, 'pending')
        self.assertEqual(self.order.events.count(), 7)
        self.assertEqual(self.order.events.first().timestamp, initial)
        self.assertEqual(self.order.events.last().changed_by, self.manager)
        page = self.client.get(self.url('order_detail', self.order.pk))
        self.assertContains(page, 'Delivered'); self.assertContains(page, 'AWB123')
        self.assertContains(page, 'Your order has progressed.')
        self.assertNotContains(page, 'STAFF SECRET')
        with self.assertRaises(CRMError):
            transition_order(self.manager, self.order.pk, 'delivered', 'packed', 'Cannot reverse')

    def test_duplicate_and_stale_events_are_not_recorded(self):
        transition_order(self.manager, self.order.pk, 'pending', 'confirmed', 'Reviewed order')
        transition_order(self.manager, self.order.pk, 'pending', 'confirmed', 'Duplicate submit')
        self.assertEqual(self.order.events.count(), 2)
        self.assertEqual(OrderNotification.objects.filter(event__order=self.order).count(), 2)
        with self.assertRaises(CRMError):
            transition_order(self.manager, self.order.pk, 'pending', 'cancelled', 'Stale request')

    def test_crm_authorization_and_shipping_validation(self):
        for actor in [self.user, self.viewer]:
            with self.assertRaises(PermissionDenied):
                transition_order(actor, self.order.pk, 'pending', 'confirmed', 'No authority')
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('crm:order_status', args=[self.order.pk]), {}).status_code, 403)
        Order.objects.filter(pk=self.order.pk).update(status='packed')
        for kwargs in [{}, {'courier': 'Test', 'tracking_number': 'AWB', 'tracking_url': 'javascript:alert(1)'}]:
            with self.assertRaises(CRMError):
                transition_order(self.manager, self.order.pk, 'packed', 'shipped', 'Sending package', **kwargs)
        self.order.refresh_from_db(); self.assertEqual(self.order.status, 'packed')

    def test_buy_again_current_price_and_exact_pack(self):
        added, skipped = buy_again(self.user, self.order.pk)
        self.assertEqual(added, 1); self.assertEqual(skipped, [])
        item = CartItem.objects.get()
        self.assertEqual(item.product_variant_id, self.variant.pk)
        self.assertEqual(item.total_price, Decimal('300'))
        self.line.refresh_from_db(); self.assertEqual(self.line.unit_price, Decimal('200'))

    def test_reorder_never_substitutes_missing_pack_or_exceeds_stock(self):
        self.variant.is_active = False; self.variant.save()
        added, skipped = buy_again(self.user, self.order.pk)
        self.assertEqual(added, 0); self.assertTrue(skipped); self.assertFalse(CartItem.objects.exists())
        self.line.product_variant = None; self.line.save()
        added, skipped = buy_again(self.user, self.order.pk)
        self.assertEqual(added, 0)
        with self.assertRaises(PermissionDenied): buy_again(self.other, self.order.pk)

    def test_reorder_post_and_csrf(self):
        url = self.url('reorder', self.order.pk)
        self.assertEqual(self.client.get(url).status_code, 405)
        protected = Client(enforce_csrf_checks=True); protected.force_login(self.user)
        self.assertEqual(protected.post(url).status_code, 403)
        self.client.force_login(self.other); self.assertEqual(self.client.post(url).status_code, 404)

    def test_cancellation_rules_and_payment_independence(self):
        self.client.post(self.url('cancel_order', self.order.pk))
        self.order.refresh_from_db(); self.assertEqual(self.order.status, 'cancelled'); self.assertEqual(self.order.payment_status, 'pending')
        count = self.order.events.count()
        self.client.post(self.url('cancel_order', self.order.pk))
        self.assertEqual(self.order.events.count(), count)
        Order.objects.filter(pk=self.order.pk).update(status='processing')
        self.client.post(self.url('cancel_order', self.order.pk))
        self.order.refresh_from_db(); self.assertEqual(self.order.status, 'processing')
        Order.objects.filter(pk=self.order.pk).update(status='pending', payment_status='paid')
        self.client.post(self.url('cancel_order', self.order.pk))
        self.order.refresh_from_db(); self.assertEqual(self.order.status, 'pending')

    def test_return_request_review_and_payment_permissions(self):
        self.client.post(self.url('request_return', self.order.pk), {'reason': 'Not suitable'})
        self.order.refresh_from_db(); self.assertEqual(self.order.return_status, '')
        Order.objects.filter(pk=self.order.pk).update(status='delivered')
        self.client.post(self.url('request_return', self.order.pk), {'reason': 'Please review eligibility'})
        update_review(self.manager, self.order.pk, 'return', 'requested', 'approved', 'Policy checked')
        update_review(self.manager, self.order.pk, 'return', 'approved', 'received', 'Goods inspected')
        self.order.refresh_from_db(); self.assertEqual(self.order.return_status, 'received'); self.assertEqual(self.order.payment_status, 'pending')
        with self.assertRaises(PermissionDenied): update_review(self.operations, self.order.pk, 'payment', 'pending', 'paid', 'Verified', 'REF123')
        update_review(self.manager, self.order.pk, 'payment', 'pending', 'paid', 'Externally verified', 'REF123')
        self.order.refresh_from_db(); self.assertEqual(self.order.status, 'delivered')

    def test_address_ownership_default_and_order_snapshot_preserved(self):
        address = CustomerAddress.objects.create(user=self.user, full_name='Parent', phone='9876543210', address_line_1='Old', city='Delhi', state='Delhi', postal_code='110001')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url('address_edit', address.pk)).status_code, 404)
        self.assertEqual(self.client.post(self.url('address_action', address.pk, 'delete')).status_code, 404)
        self.client.force_login(self.user)
        self.client.post(self.url('address_action', address.pk, 'default'))
        address.refresh_from_db(); self.assertTrue(address.is_default_shipping)
        self.client.post(self.url('address_action', address.pk, 'delete'))
        self.order.refresh_from_db(); self.assertEqual(self.order.shipping_address_line_1, '1 Test Road')

    def test_pet_and_wishlist_ownership(self):
        pet = CustomerPet.objects.create(user=self.user, name='Bruno', pet_type=PetCategory.objects.create(name='Dog'))
        saved = WishlistItem.objects.create(user=self.user, product=self.product)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url('pet_edit', pet.pk)).status_code, 404)
        self.assertEqual(self.client.post(self.url('pet_delete', pet.pk)).status_code, 404)
        self.assertEqual(self.client.post(self.url('wishlist_delete', saved.pk)).status_code, 404)
        self.assertNotContains(self.client.get(self.url('pets')), 'Bruno')
        self.client.force_login(self.user)
        self.client.post(self.url('wishlist_save', self.product.pk)); self.assertEqual(self.user.wishlist.count(), 1)

    def test_support_order_ownership_and_customer_reply(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url('support'), {'order': self.order.pk, 'category': 'order', 'subject': 'Help', 'message': 'Question'})
        self.assertEqual(response.status_code, 200); self.assertFalse(SupportRequest.objects.exists())
        ticket = SupportRequest.objects.create(user=self.user, order=self.order, category='order', subject='Delivery help', message='Private customer question')
        self.assertNotContains(self.client.get(self.url('support')), 'Private customer question')
        self.client.force_login(self.manager)
        self.client.post(reverse('crm:support_detail', args=[ticket.pk]), {'response': 'We are reviewing this.', 'state': 'open'})
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url('support')), 'We are reviewing this.')

    def test_profile_does_not_accept_email_or_permissions_changes(self):
        self.client.post(self.url('profile_edit'), {'first_name': 'New name', 'last_name': '', 'phone': '9999999999', 'email': 'attacker@example.com', 'is_staff': 'on'})
        self.user.refresh_from_db(); self.assertEqual(self.user.email, 'owner@example.com'); self.assertFalse(self.user.is_staff)
        self.assertEqual(self.user.first_name, 'New name')

    def test_address_create_and_checkout_selection_are_owned(self):
        payload = {'label': 'Home', 'full_name': 'My chosen name', 'phone': '9876543210', 'address_line_1': '2 New Street',
                   'address_line_2': 'Near the park', 'city': 'Delhi', 'state': 'Delhi', 'postal_code': '110001', 'country': 'India', 'is_default_shipping': 'on', 'user': self.other.pk}
        self.assertEqual(self.client.post(self.url('addresses'), payload).status_code, 302)
        address = self.user.addresses.get(); self.assertEqual(address.user_id, self.user.pk)
        self.client.post(self.url('add_to_cart', self.product.pk), {'variant_id': self.variant.pk})
        response = self.client.get(self.url('checkout'), {'address': address.pk})
        self.assertEqual(response.context['form'].initial['shipping_name'], 'My chosen name')
        self.assertEqual(self.client.get(self.url('checkout'), {'address': 'invalid'}).status_code, 404)
        self.client.force_login(self.other)
        self.client.post(self.url('add_to_cart', self.product.pk), {'variant_id': self.variant.pk})
        self.assertEqual(self.client.get(self.url('checkout'), {'address': address.pk}).status_code, 404)

    def test_pet_form_owner_and_invalid_birth_date(self):
        pet_type = PetCategory.objects.create(name='Cat')
        payload = {'name': 'Milo', 'pet_type': pet_type.pk, 'breed': '', 'gender': '', 'weight': '4.2', 'user': self.other.pk}
        self.assertEqual(self.client.post(self.url('pets'), payload).status_code, 302)
        self.assertEqual(self.user.pets.get().name, 'Milo')
        self.assertFalse(self.other.pets.exists())
        payload['date_of_birth'] = '2999-01-01'
        self.assertEqual(self.client.post(self.url('pets'), payload).status_code, 200)
        self.assertEqual(self.user.pets.count(), 1)

    def test_reorder_checks_quantity_already_in_cart(self):
        self.variant.stock_quantity = 1; self.variant.save()
        self.assertEqual(buy_again(self.user, self.order.pk)[0], 1)
        self.assertEqual(buy_again(self.user, self.order.pk)[0], 0)
        self.assertEqual(CartItem.objects.get().quantity, 1)

    def test_password_change_preserves_this_session(self):
        response = self.client.post(self.url('security'), {'old_password': 'Fixture-care-921!',
            'new_password1': 'Changed-care-478!', 'new_password2': 'Changed-care-478!'})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db(); self.assertTrue(self.user.check_password('Changed-care-478!'))
        self.assertEqual(self.client.get(self.url('profile')).status_code, 200)

    @override_settings(ORDER_EMAIL_ENABLED=False)
    def test_notifications_disabled_by_default(self):
        with self.assertRaises(CommandError): call_command('send_order_notifications')

    @override_settings(ORDER_EMAIL_ENABLED=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_notification_worker_sends_event_once_without_internal_notes(self):
        from django.core import mail
        transition_order(self.manager, self.order.pk, 'pending', 'confirmed', 'STAFF SECRET')
        call_command('send_order_notifications', stdout=io.StringIO())
        call_command('send_order_notifications', stdout=io.StringIO())
        self.assertEqual(len(mail.outbox), 2)
        self.assertNotIn('STAFF SECRET', ''.join(m.body for m in mail.outbox))

import hashlib
import hmac
import io
import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from shop.models import CartItem, Order, OrderItem, OrderNotification, PaymentAttempt, Product, ProductVariant, Category, InventoryMovement
from shop.services.payments import initialize, verify_captured, PaymentError, enabled
from shop.services.notifications import deliver_pending
from shop.test_checkout import CHECKOUT_DATA

TEST_CONFIG = dict(RAZORPAY_ENABLED=True, RAZORPAY_KEY_ID='rzp_test_fixture', RAZORPAY_KEY_SECRET='fixture-secret',
    RAZORPAY_WEBHOOK_SECRET='fixture-webhook', ORDER_EMAIL_ENABLED=True, ORDER_EMAIL_AUTO_SEND=True,
    ORDER_NOTIFICATION_EMAIL='admin@example.com', PUBLIC_SITE_URL='https://store.example.com',
    MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}})


@override_settings(**TEST_CONFIG)
class PurchaseFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('purchase-buyer', email='buyer@example.com')
        self.staff = get_user_model().objects.create_superuser('purchase-admin', email='staff@example.com')
        self.client.force_login(self.user)
        self.product = Product.objects.create(name='Verified food', category=Category.objects.create(name='Dog'), base_price='3500')
        self.small = ProductVariant.objects.create(product=self.product, name='1.5 KG', selling_price='1050', stock_quantity=10)
        self.pack = ProductVariant.objects.create(product=self.product, name='5 KG', sku='EXACT-5KG', selling_price='2950', stock_quantity=3)
        self.add_url = reverse('shop:add_to_cart', args=[self.product.pk])
        self.client.post(self.add_url, {'variant_id': self.pack.pk, 'quantity': 1})
        self.token = self.client.get(reverse('shop:checkout')).context['checkout_token']

    def checkout(self, method='online'):
        return self.client.post(reverse('shop:checkout'), {**CHECKOUT_DATA, 'payment_method': method,
            'checkout_token': self.token, 'total': '0.01', 'payment_status': 'paid'})

    def prepare(self):
        self.checkout()
        self.order = Order.objects.get()
        self.attempt = PaymentAttempt.objects.get()
        self.payment_url = reverse('shop:payment', args=[self.order.pk])
        with patch('shop.services.payments.api', return_value={'id':'order_fixture', 'amount':295000, 'currency':'INR', 'receipt':self.order.order_number}):
            self.client.post(self.payment_url, {'action':'initialize'})
        self.attempt.refresh_from_db()

    def callback(self, signature=None):
        signature = signature or hmac.new(b'fixture-secret', b'order_fixture|pay_fixture', hashlib.sha256).hexdigest()
        return self.client.post(self.payment_url, {'action':'verify','razorpay_order_id':'order_fixture',
            'razorpay_payment_id':'pay_fixture','razorpay_signature':signature})

    def gateway(self, path, payload=None):
        if path == 'payments/pay_fixture':
            return {'id':'pay_fixture','order_id':'order_fixture','status':'captured','captured':True,'amount':295000,'currency':'INR'}
        return {'id':'order_fixture','status':'paid','amount':295000,'amount_paid':295000,'currency':'INR'}

    def test_verified_payment_sends_admin_only_until_staff_confirmation(self):
        self.prepare()
        self.assertEqual(self.order.status, 'awaiting_payment')
        self.assertEqual(OrderNotification.objects.count(), 0)
        with patch('shop.services.payments.api', side_effect=self.gateway), self.captureOnCommitCallbacks(execute=True):
            response = self.callback()
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid'); self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.order.total, 2950)
        line = OrderItem.objects.get()
        self.assertEqual(line.product_variant_id, self.pack.pk); self.assertEqual(line.variant_name, '5 KG')
        self.pack.refresh_from_db(); self.small.refresh_from_db()
        self.assertEqual(self.pack.stock_quantity, 2); self.assertEqual(self.small.stock_quantity, 10)
        self.assertEqual(InventoryMovement.objects.filter(variant=self.pack).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual({m.to[0] for m in mail.outbox}, {'admin@example.com'})
        for message in mail.outbox:
            self.assertTrue(message.alternatives)
            self.assertIn('5 KG', message.body); self.assertIn('2950', message.body)
            self.assertIn('1 Test Street', message.body)
            self.assertNotIn('fixture-secret', message.body)
        self.assertContains(self.client.get(response.url), 'Payment confirmed')
        self.assertContains(self.client.get(reverse('shop:orders')), self.order.order_number)
        staff = Client(); staff.force_login(self.staff)
        self.assertContains(staff.get(reverse('crm:order_detail', args=[self.order.pk])), self.order.order_number)
        with patch('shop.services.payments.api', side_effect=self.gateway), self.captureOnCommitCallbacks(execute=True):
            self.callback(); self.checkout(); self.client.get(response.url)
        deliver_pending()
        self.assertEqual(Order.objects.count(), 1); self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.order.events.filter(kind='order', status='pending').count(), 1)
        ProductVariant.objects.filter(pk=self.pack.pk).update(selling_price='4000')
        self.assertEqual(OrderItem.objects.get().unit_price, 2950)

    def test_normal_add_redirects_to_cart_and_buy_now_to_checkout(self):
        response = self.client.post(self.add_url, {'variant_id':self.small.pk,'next':'/categories/'})
        self.assertRedirects(response, reverse('shop:cart'))
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 2)
        response = self.client.post(self.add_url, {'variant_id':self.small.pk,'intent':'buy_now'})
        self.assertRedirects(response, reverse('shop:checkout'))

    def test_get_and_cross_customer_payment_access_are_denied(self):
        self.prepare()
        self.assertEqual(self.client.get(self.add_url).status_code, 405)
        stranger = Client(); stranger.force_login(get_user_model().objects.create_user('stranger'))
        self.assertEqual(stranger.get(self.payment_url).status_code, 404)
        self.assertEqual(stranger.post(self.payment_url, {'action':'initialize'}).status_code, 404)
        csrf_client = Client(enforce_csrf_checks=True); csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.payment_url, {'action':'initialize'}).status_code, 403)

    def test_forged_signature_does_not_fetch_gateway_or_send_email(self):
        self.prepare()
        with patch('shop.services.payments.api') as api:
            response = self.callback('forged')
        api.assert_not_called(); self.assertContains(response, 'verification failed')
        self.order.refresh_from_db(); self.assertEqual(self.order.payment_status, 'pending')
        self.assertEqual(OrderNotification.objects.count(), 0)

    def test_uncaptured_failed_wrong_amount_wrong_order_cannot_confirm(self):
        self.prepare()
        for changes in [{'status':'failed','captured':False}, {'status':'authorized','captured':False}, {'amount':1}, {'currency':'USD'}, {'order_id':'order_other'}]:
            data = self.gateway('payments/pay_fixture'); data.update(changes)
            with patch('shop.services.payments.api', side_effect=[data,self.gateway('orders/order_fixture')]):
                self.callback()
            self.order.refresh_from_db(); self.assertEqual(self.order.payment_status, 'pending')
        self.assertEqual(OrderNotification.objects.count(), 0)

    def test_create_timeout_is_not_retried_automatically(self):
        self.checkout(); order = Order.objects.get()
        with patch('shop.services.payments.api', side_effect=PaymentError('timeout')) as api:
            with self.assertRaises(PaymentError): initialize(order)
            with self.assertRaises(PaymentError): initialize(order)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(PaymentAttempt.objects.get().state, 'uncertain')

    def test_duplicate_initialize_reuses_one_gateway_order(self):
        self.prepare()
        with patch('shop.services.payments.api') as api:
            result = initialize(self.order)
        api.assert_not_called(); self.assertEqual(result.gateway_order_id, 'order_fixture')

    def test_signed_webhook_and_callback_do_not_duplicate_processing(self):
        self.prepare()
        body = json.dumps({'event':'payment.captured','payload':{'payment':{'entity':{'order_id':'order_fixture','id':'pay_fixture'}}}}).encode()
        url = reverse('shop:razorpay_webhook')
        self.assertEqual(self.client.post(url, body, content_type='application/json').status_code, 400)
        signature = hmac.new(b'fixture-webhook', body, hashlib.sha256).hexdigest()
        with patch('shop.services.payments.api', side_effect=self.gateway), self.captureOnCommitCallbacks(execute=True):
            for _ in range(2):
                self.assertEqual(self.client.post(url, body, content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE=signature).status_code, 200)
            self.callback()
        self.assertEqual(len(mail.outbox), 1); self.assertEqual(Order.objects.count(), 1)

    def test_cod_email_failure_keeps_order_and_does_not_blindly_resend(self):
        with patch('shop.services.notifications.EmailMultiAlternatives.send', side_effect=RuntimeError('SMTP SECRET')), self.captureOnCommitCallbacks(execute=True):
            response = self.checkout('cash_on_delivery')
        order = Order.objects.get()
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(OrderNotification.objects.filter(state='failed').count(), 1)
        self.assertNotContains(self.client.get(response.url), 'SMTP SECRET')
        deliver_pending(); self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn('SMTP SECRET', ''.join(OrderNotification.objects.values_list('error',flat=True)))

    @override_settings(RAZORPAY_KEY_ID='rzp_live_not_allowed')
    def test_live_keys_cannot_enable_development_payments(self):
        self.assertFalse(enabled())
        self.checkout(); self.assertEqual(Order.objects.count(), 0)

    def test_out_of_stock_cannot_checkout(self):
        ProductVariant.objects.filter(pk=self.pack.pk).update(stock_quantity=0)
        self.checkout(); self.assertEqual(Order.objects.count(), 0)

    def test_admin_notes_are_not_in_notifications(self):
        from shop.services.order_tracking import record_event
        self.checkout('cash_on_delivery'); order = Order.objects.get()
        record_event(order, 'confirmed', internal_note='PRIVATE CRM NOTE', customer_note='Your order is confirmed.')
        deliver_pending()
        self.assertNotIn('PRIVATE CRM NOTE', ''.join(m.body + m.alternatives[0].content for m in mail.outbox))

    def test_uncertain_create_reconciliation_checks_receipt_and_amount(self):
        from django.core.management.base import CommandError
        self.checkout(); order = Order.objects.get()
        PaymentAttempt.objects.update(state='uncertain')
        with patch('shop.management.commands.reconcile_test_payment.api', return_value={'id':'order_reconciled','receipt':'wrong','amount':295000,'currency':'INR'}):
            with self.assertRaises(CommandError):
                call_command('reconcile_test_payment', order.order_number, gateway_order_id='order_reconciled', stdout=io.StringIO())
        self.assertEqual(PaymentAttempt.objects.get().state, 'uncertain')
        with patch('shop.management.commands.reconcile_test_payment.api', return_value={'id':'order_reconciled','receipt':order.order_number,'amount':295000,'currency':'INR'}):
            call_command('reconcile_test_payment', order.order_number, gateway_order_id='order_reconciled', stdout=io.StringIO())
        self.assertEqual(PaymentAttempt.objects.get().state, 'ready')
        order.refresh_from_db(); self.assertEqual(order.payment_status, 'pending')

    def test_rolled_back_checkout_never_sends_confirmation(self):
        from django.db import transaction
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self.checkout('cash_on_delivery')
                    raise RuntimeError('Rollback fixture')
            except RuntimeError:
                pass
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderNotification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

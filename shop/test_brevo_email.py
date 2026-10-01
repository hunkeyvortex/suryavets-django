"""Brevo contract/outbox tests: transport is always mocked, even with local keys set."""
import io
import json
import os
import ssl
import subprocess
from datetime import timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest import skipUnless
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from shop.mail_backends import DeliveryError, post_email, NoRedirect
from shop.models import Order, OrderItem, OrderNotification
from shop.services.order_tracking import record_event
from shop.services.notifications import deliver_pending, deliver_event_safely

CONFIG = dict(ORDER_EMAIL_ENABLED=True, ORDER_EMAIL_AUTO_SEND=False,
    ORDER_NOTIFICATION_EMAIL='admin@example.com', PUBLIC_SITE_URL='https://store.example.com',
    DEFAULT_FROM_NAME='SuryaVets', DEFAULT_FROM_EMAIL='orders@example.com',
    BREVO_API_KEY='fixture-key-never-real', BREVO_SANDBOX=False, BREVO_TIMEOUT=15,
    MAILERS={'default': {'BACKEND': 'shop.mail_backends.BrevoEmailBackend'}})


@override_settings(**CONFIG)
class BrevoOutboxTests(TestCase):
    def setUp(self):
        # Patch the lowest HTTP opener, so no test can accidentally call Brevo.
        self.transport = patch('shop.mail_backends.build_opener').start()
        self.addCleanup(patch.stopall)
        response = self.transport.return_value.open.return_value.__enter__.return_value
        response.status = 201
        response.read.return_value = b'{"messageId":"<test-message@brevo.invalid>"}'
        self.user = get_user_model().objects.create_user('email-buyer', email='buyer@example.com')
        self.order = Order.objects.create(user=self.user, email=self.user.email, phone='9999999999',
            shipping_name='Test Buyer', shipping_address_line_1='1 Test Street', shipping_city='Mumbai',
            shipping_state='Maharashtra', shipping_postal_code='400001', subtotal='2950', total='2950',
            payment_method='cash_on_delivery', notes='PRIVATE ORDER NOTE')
        OrderItem.objects.create(order=self.order, product_name='Purchased food', variant_name='5 KG',
            sku='EXACT-5KG', quantity=1, unit_price='2950')
        self.event = record_event(self.order, 'pending', internal_note='PRIVATE STAFF NOTE')

    def payloads(self):
        return [json.loads(call.args[0].data) for call in self.transport.return_value.open.call_args_list]

    def test_two_recipients_exact_snapshot_and_private_absolute_links(self):
        self.assertEqual(OrderNotification.objects.count(), 2)
        deliver_pending()
        messages = {p['to'][0]['email']: p for p in self.payloads()}
        self.assertEqual(set(messages), {'buyer@example.com', 'admin@example.com'})
        customer, admin = messages['buyer@example.com'], messages['admin@example.com']
        self.assertEqual(customer['subject'], f'SuryaVets Order Confirmation – #{self.order.order_number}')
        self.assertIn('₹2,950.00', admin['subject'])
        for message in messages.values():
            for content in [message['textContent'], message['htmlContent']]:
                for value in ['5 KG', 'EXACT-5KG', '2950', '1 Test Street', self.order.order_number, 'Pending']:
                    self.assertIn(value, content)
                for secret in ['fixture-key-never-real', 'PRIVATE STAFF NOTE', 'PRIVATE ORDER NOTE']:
                    self.assertNotIn(secret, content)
            self.assertEqual(message['sender'], {'name':'SuryaVets', 'email':'orders@example.com'})
        self.assertIn('https://store.example.com' + reverse('shop:order_number', args=[self.order.order_number]) + '#tracking', customer['htmlContent'])
        self.assertNotIn('/crm/', customer['htmlContent'])
        self.assertIn('https://store.example.com' + reverse('crm:order_detail', args=[self.order.pk]), admin['htmlContent'])
        self.assertEqual(OrderNotification.objects.filter(state='sent', provider_message_id='<test-message@brevo.invalid>').count(), 2)
        self.assertFalse(OrderNotification.objects.filter(sent_at__isnull=True).exists())
        self.order.refresh_from_db(); self.assertEqual(self.order.payment_status, 'pending')

    @override_settings(ORDER_EMAIL_AUTO_SEND=True)
    def test_repeated_event_processing_never_resends(self):
        for _ in range(3):
            deliver_event_safely(self.event.pk)
            deliver_pending()
        self.assertEqual(len(self.payloads()), 2)
        self.assertEqual(OrderNotification.objects.count(), 2)
        self.assertEqual(set(OrderNotification.objects.values_list('attempts', flat=True)), {1})

    @override_settings(BREVO_SANDBOX=True)
    def test_sandbox_preview_cannot_be_replayed_as_live(self):
        deliver_pending()
        self.assertTrue(all(p['headers']['X-Sib-Sandbox'] == 'drop' for p in self.payloads()))
        self.assertEqual(OrderNotification.objects.filter(state='preview', sent_at__isnull=True).count(), 2)
        with override_settings(BREVO_SANDBOX=False):
            deliver_pending()
            with self.assertRaises(CommandError):
                call_command('send_order_notifications', retry_failed=OrderNotification.objects.first().pk)
        self.assertEqual(len(self.payloads()), 2)

    def test_confirmed_rejection_safe_scoped_retry_and_stable_key(self):
        self.transport.return_value.open.side_effect = HTTPError('https://api.brevo.com', 401, 'RAW SECRET', {}, None)
        with self.assertLogs('shop.services.notifications', level='WARNING') as logs:
            deliver_pending()
        self.assertNotIn('RAW SECRET', str(logs.output)); self.assertNotIn(CONFIG['BREVO_API_KEY'], str(logs.output))
        row = OrderNotification.objects.get(audience='customer')
        self.assertEqual(row.state, 'failed'); self.assertTrue(row.retryable)
        first_key = self.payloads()[0]['headers']['idempotencyKey']
        self.transport.return_value.open.side_effect = None
        call_command('send_order_notifications', retry_failed=row.pk, stdout=io.StringIO())
        row.refresh_from_db(); self.assertEqual(row.state, 'sent'); self.assertEqual(row.attempts, 2)
        self.assertEqual(self.payloads()[-1]['headers']['idempotencyKey'], first_key)
        self.assertEqual(OrderNotification.objects.get(audience='admin').state, 'failed')
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())

    def test_rate_limit_backoff_and_attempt_limit(self):
        row = OrderNotification.objects.get(audience='customer')
        self.transport.return_value.open.side_effect = HTTPError('https://api.brevo.com', 429, '', {'Retry-After':'120'}, None)
        for attempt in range(1, 6):
            deliver_pending(notification_id=row.pk)
            row.refresh_from_db()
            self.assertEqual(row.attempts, attempt)
            if attempt < 5:
                self.assertGreater(row.next_attempt_at, timezone.now())
                deliver_pending(notification_id=row.pk)
                self.assertEqual(self.transport.return_value.open.call_count, attempt)
                OrderNotification.objects.filter(pk=row.pk).update(next_attempt_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(row.state, 'failed')
        with self.assertRaises(CommandError): call_command('send_order_notifications', retry_failed=row.pk)
        deliver_pending(notification_id=row.pk)
        self.assertEqual(self.transport.return_value.open.call_count, 5)

    def test_ambiguous_failure_preserves_order_and_requires_review(self):
        row = OrderNotification.objects.get(audience='customer')
        for failure in [TimeoutError('SECRET'), HTTPError('',500,'SECRET',{},None), HTTPError('',400,'duplicate_parameter',{},None)]:
            OrderNotification.objects.filter(pk=row.pk).update(state='pending', retryable=True)
            self.transport.return_value.open.side_effect = failure
            deliver_pending(notification_id=row.pk)
            row.refresh_from_db(); self.assertEqual(row.state, 'failed'); self.assertFalse(row.retryable)
            with self.assertRaises(CommandError): call_command('send_order_notifications', retry_failed=row.pk)
            self.assertNotIn('SECRET', row.error)
        self.order.refresh_from_db(); self.assertEqual(self.order.status, 'pending'); self.assertEqual(self.order.payment_status, 'pending')

    def test_generic_failure_clears_previous_retry_permission(self):
        row = OrderNotification.objects.get(audience='customer')
        OrderNotification.objects.filter(pk=row.pk).update(retryable=True)
        with patch('shop.services.notifications.render_to_string', side_effect=RuntimeError('SECRET')):
            deliver_pending(notification_id=row.pk)
        row.refresh_from_db(); self.assertFalse(row.retryable); self.assertIsNone(row.next_attempt_at)

    @override_settings(ORDER_EMAIL_ENABLED=False)
    def test_disabled_delivery_and_test_command_do_not_call_network(self):
        deliver_pending()
        with self.assertRaises(CommandError): call_command('test_transactional_email', to='owner@example.com')
        self.transport.assert_not_called()

    def test_diagnostic_requires_explicit_live_permission(self):
        with self.assertRaises(CommandError): call_command('test_transactional_email', to='owner@example.com')
        self.transport.assert_not_called()
        call_command('test_transactional_email', to='owner@example.com', allow_live=True, stdout=io.StringIO())
        self.assertEqual(self.payloads()[0]['to'][0]['email'], 'owner@example.com')
        self.assertTrue(self.payloads()[0]['subject'].startswith('[TEST]'))
        self.assertEqual(Order.objects.count(), 1)

    @override_settings(BREVO_SANDBOX=True)
    def test_diagnostic_sandbox_reports_no_delivery(self):
        output = io.StringIO()
        call_command('test_transactional_email', to='owner@example.com', stdout=output)
        self.assertIn('NO email delivered', output.getvalue())

    def test_missing_admin_address_waits_without_emailing_wrong_recipient(self):
        OrderNotification.objects.filter(audience='admin').update(recipient='')
        with override_settings(ORDER_NOTIFICATION_EMAIL=''):
            deliver_pending()
        self.assertEqual(len(self.payloads()), 1)
        self.assertEqual(OrderNotification.objects.get(audience='admin').state, 'pending')

    @skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Enable browser runtime for HTML email visual tests.')
    def test_email_mobile_and_desktop_layout(self):
        deliver_pending()
        if os.environ.get('SURYA_BROWSER_ARTIFACTS'):
            Path(os.environ['SURYA_BROWSER_ARTIFACTS']).mkdir(parents=True, exist_ok=True)
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('email_browser_test.cjs'))],
            input=json.dumps([p['htmlContent'] for p in self.payloads()]), capture_output=True, text=True, timeout=50)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@override_settings(**CONFIG)
class BrevoTransportTests(SimpleTestCase):
    @patch('shop.mail_backends.build_opener')
    def test_fixed_https_api_key_header_timeout_and_response_validation(self, opener):
        response = opener.return_value.open.return_value.__enter__.return_value
        response.status = 201; response.read.return_value = b'{"messageId":"accepted-id"}'
        self.assertEqual(post_email({'subject':'test'}), 'accepted-id')
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.brevo.com/v3/smtp/email')
        self.assertEqual(request.get_header('Api-key'), CONFIG['BREVO_API_KEY'])
        self.assertNotIn(CONFIG['BREVO_API_KEY'].encode(), request.data)
        self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], 15)
        self.assertIsInstance(opener.call_args.args[0], NoRedirect)
        tls_context = opener.call_args.args[1]._context
        self.assertTrue(tls_context.check_hostname)
        self.assertEqual(tls_context.verify_mode, ssl.CERT_REQUIRED)
        for body in [b'{}', b'[]', b'{"messageId":""}', b'not-json']:
            response.read.return_value = body
            with self.assertRaises(DeliveryError): post_email({})

    @override_settings(BREVO_API_KEY='')
    @patch('shop.mail_backends.build_opener')
    def test_missing_key_is_retryable_without_network(self, opener):
        with self.assertRaises(DeliveryError) as error: post_email({})
        self.assertTrue(error.exception.retryable); opener.assert_not_called()

    def test_no_redirect_for_credentials(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid'))

    @patch('shop.mail_backends.build_opener')
    def test_certificate_rejection_is_sanitized_and_not_bypassed(self, opener):
        opener.return_value.open.side_effect = URLError(ssl.SSLCertVerificationError('private TLS diagnostics'))
        with self.assertRaises(DeliveryError) as error:
            post_email({})
        self.assertEqual(str(error.exception), 'brevo_tls_verification_failed')
        self.assertTrue(error.exception.retryable)
        self.assertEqual(opener.return_value.open.call_count, 1)

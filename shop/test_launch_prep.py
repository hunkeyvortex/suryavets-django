import json
from io import StringIO
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, Client, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from shop.models import Category, Product, ProductVariant, ContactSubmission, NewsletterSubscription

class LaunchPrepTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Dog', reference_path='/collections/dog')
        self.product = Product.objects.create(name='Known food', category=self.category, base_price=100)
        self.variant = ProductVariant.objects.create(product=self.product, name='1 KG', stock_quantity=10)

    def test_contact_validation_persistence_privacy_and_limit(self):
        self.assertEqual(self.client.post('/contact/', {}).status_code, 400)
        data = {'name':'Owner', 'email':'owner@example.com', 'subject':'Question', 'message':'Private message'}
        response = self.client.post('/contact/', data)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('Private', response.url)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        for _ in range(4):
            response = self.client.post('/contact/', data)
        self.assertEqual(response.status_code, 429)

    def test_contact_csrf_and_honeypot(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/contact/', {}).status_code, 403)
        self.client.post('/contact/', {'name':'Bot','email':'bot@example.com','subject':'x','message':'x','website':'spam'})
        self.assertFalse(ContactSubmission.objects.exists())

    def test_newsletter_consent_duplicates_optout(self):
        self.assertEqual(self.client.post('/newsletter/', {'email':'a@example.com'}).status_code, 400)
        for email in ['A@example.com','a@example.com']:
            self.assertTrue(self.client.post('/newsletter/', {'email':email,'consent':'on'}).json()['success'])
        self.assertEqual(NewsletterSubscription.objects.count(), 1)
        NewsletterSubscription.objects.update(is_active=False)
        self.client.post('/newsletter/', {'email':'a@example.com','consent':'on'})
        self.assertFalse(NewsletterSubscription.objects.get().is_active)
        self.assertEqual(self.client.get('/newsletter/').status_code, 405)

    @override_settings(PASSWORD_RESET_EMAIL_ENABLED=True, PUBLIC_SITE_URL='https://preview.example.com', MAILERS={'default':{'BACKEND':'django.core.mail.backends.locmem.EmailBackend'}})
    def test_reset_email_and_single_use_token(self):
        user = User.objects.create_user('customer', email='customer@example.com', password='OldStrongPassword938!')
        known = self.client.post('/password-reset/', {'email':user.email})
        unknown = self.client.post('/password-reset/', {'email':'unknown@example.com'})
        self.assertEqual(known.url, unknown.url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('https://preview.example.com/reset/', mail.outbox[0].body)
        self.assertTrue(mail.outbox[0].alternatives)
        token = default_token_generator.make_token(user)
        url = '/reset/'+urlsafe_base64_encode(force_bytes(user.pk))+'/'+token+'/'
        response = self.client.get(url)
        result = self.client.post(response.url, {'new_password1':'NewStrongPassword654!', 'new_password2':'NewStrongPassword654!'})
        self.assertEqual(result.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewStrongPassword654!'))
        self.assertFalse(default_token_generator.check_token(user, token))

    def test_reset_disabled_and_throttled_generic(self):
        for _ in range(8):
            self.assertRedirects(self.client.post('/password-reset/', {'email':'nobody@example.com'}), '/password-reset/done/')

    @override_settings(SITE_NOINDEX=False, PUBLIC_SITE_URL='https://preview.example.com')
    def test_seo_metadata_and_private_headers(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, 'application/ld+json')
        self.assertContains(response, 'https://preview.example.com/product/')
        self.assertContains(response, '"priceCurrency": "INR"')
        self.assertContains(response, 'BreadcrumbList')
        self.assertContains(self.client.get('/sitemap.xml'), self.product.get_absolute_url())
        self.assertNotIn('Disallow: /\n', self.client.get('/robots.txt').content.decode())
        self.assertEqual(self.client.get('/account/')['X-Robots-Tag'], 'noindex, nofollow')
        header = self.client.get('/crm/')['Cache-Control']
        self.assertIn('private', header)
        self.assertIn('no-store', header)

    def test_staging_health_and_unknown_legacy(self):
        self.assertContains(self.client.get('/robots.txt'), 'Disallow: /')
        self.assertEqual(self.client.get('/health/').json(), {'status':'ok'})
        self.assertEqual(self.client.get('/products/not-known').status_code, 404)

    def test_legacy_exact_and_external_rejected(self):
        with TemporaryDirectory() as tmp, override_settings(BASE_DIR=Path(tmp)):
            folder = Path(tmp)/'catalog_review'
            folder.mkdir()
            (folder/'seo_redirects.json').write_text(json.dumps({'/products/known':self.product.get_absolute_url(), '/products/evil':'https://evil.example/'}))
            self.assertRedirects(self.client.get('/products/known'), self.product.get_absolute_url(), status_code=301)
            self.assertEqual(self.client.get('/products/evil').status_code, 404)
            self.assertEqual(self.client.get('/products/known?variant=123').status_code, 404)

    @override_settings(DEBUG=False, ANALYTICS_EVENTS_ENABLED=True)
    def test_meaningful_404(self):
        self.assertContains(self.client.get('/nothing-here/'), "find that page", status_code=404)

    def test_outbox_dry_run_never_calls_sender(self):
        with patch('shop.management.commands.send_order_notifications.deliver_pending') as send:
            call_command('send_order_notifications', dry_run=True, stdout=StringIO())
            send.assert_not_called()

    def test_login_throttle_and_forged_ip_header(self):
        for i in range(21):
            response = self.client.post('/login/', {'username':'nobody@example.com','password':'wrong'}, HTTP_X_FORWARDED_FOR=f'10.0.0.{i}')
        self.assertEqual(response.status_code, 429)

    def test_health_database_failure_is_sanitized(self):
        with patch('shop.seo.connection.cursor', side_effect=RuntimeError('secret-database-url')):
            response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'secret', response.content)

    def test_metadata_escapes_json_script_payload(self):
        self.product.name = '</script><script>alert(1)</script>'
        self.product.save()
        response = self.client.get(self.product.get_absolute_url())
        self.assertNotContains(response, '</script><script>alert(1)</script>')

    @override_settings(ANALYTICS_EVENTS_ENABLED=True)
    def test_events_no_pii_and_add_only_on_success(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, 'view_item')
        self.client.post(f'/product/{self.product.pk}/add/', {'variant_id':self.variant.pk, 'quantity':1})
        self.assertEqual(self.client.session.get('commerce_event', {}).get('event'), 'add_to_cart')
        response = self.client.get('/cart/')
        self.assertContains(response, 'add_to_cart')
        self.assertNotIn('commerce_event', self.client.session)

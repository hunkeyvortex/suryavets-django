from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from shop.models import Cart, CartItem, Category, Product


class CustomerAccountTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('petparent', email='parent@example.com', password='Testing-care-482!')
        self.product = Product.objects.create(name='Account fixture', category=Category.objects.create(name='Dog'), base_price=100, stock_quantity=100)

    def test_new_pages_and_password_controls(self):
        for route, template in [('login', 'auth_login.html'), ('register', 'auth_register.html')]:
            response = self.client.get(reverse('shop:' + route))
            self.assertTemplateUsed(response, template)
            self.assertContains(response, 'data-password-toggle')
            self.assertContains(response, 'autocomplete="email"')
            self.assertNotContains(response, 'name="username"')
            self.assertIn('no-store', response['Cache-Control'])

    def test_login_safe_redirect_and_post_only_logout(self):
        response = self.client.post(reverse('shop:login'), {'email': 'parent@example.com', 'password': 'Testing-care-482!', 'next': 'https://example.invalid/'})
        self.assertEqual(response.url, reverse('shop:profile'))
        self.assertEqual(self.client.get(reverse('shop:logout')).status_code, 405)
        self.client.post(reverse('shop:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_keeps_next_and_merges_baskets_once(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=3)
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 2})
        response = self.client.post(reverse('shop:login'), {'email': 'parent@example.com', 'password': 'Testing-care-482!', 'next': '/checkout/'})
        self.assertEqual(response.url, '/checkout/')
        self.assertEqual(cart.items.get().quantity, 5)
        self.client.post(reverse('shop:logout'))
        self.client.post(reverse('shop:login'), {'email': 'parent@example.com', 'password': 'Testing-care-482!'})
        self.assertEqual(cart.items.get().quantity, 5)

    def test_registration_merges_guest_cart_but_never_grants_staff_access(self):
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 2})
        response = self.client.post(reverse('shop:register'), {'email': 'NEW@gmail.com',
            'password1': 'Testing-care-482!', 'password2': 'Testing-care-482!', 'next': '/checkout/', 'is_staff': 'on'})
        self.assertEqual(response.url, '/checkout/')
        user = get_user_model().objects.get(email='new@gmail.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.cart.items.get().quantity, 2)
        self.assertEqual(self.client.get(reverse('crm:dashboard')).status_code, 403)

    def test_validation_errors_preserve_email_and_do_not_echo_password(self):
        response = self.client.post(reverse('shop:login'), {'email': 'parent@example.com', 'password': 'wrong-password'})
        self.assertContains(response, 'value="parent@example.com"')
        self.assertNotContains(response, 'value="wrong-password"')
        self.assertContains(response, 'auth-error')
        response = self.client.post(reverse('shop:register'), {'email': 'PARENT@example.com', 'password1': '123', 'password2': '456'})
        self.assertContains(response, 'An account already uses this email address.')
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_authentication_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('shop:login'), {}).status_code, 403)
        self.assertEqual(client.post(reverse('shop:register'), {}).status_code, 403)

    def test_auth_redirect_does_not_loop_back_to_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('shop:login'), {'next': '/login/'})
        self.assertEqual(response.url, reverse('shop:profile'))

    def test_email_login_case_insensitive_for_existing_username_account(self):
        response = self.client.post(reverse('shop:login'), {'email': ' PARENT@EXAMPLE.COM ', 'password': 'Testing-care-482!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'petparent')

    def test_username_is_not_accepted_as_customer_login(self):
        response = self.client.post(reverse('shop:login'), {'username': 'petparent', 'password': 'Testing-care-482!'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_inactive_unknown_and_duplicate_emails_fail_with_generic_error(self):
        self.user.is_active = False
        self.user.save()
        for email in ['parent@example.com', 'missing@example.com']:
            response = self.client.post(reverse('shop:login'), {'email': email, 'password': 'Testing-care-482!'})
            self.assertContains(response, 'The email address or password is incorrect.')
            self.assertNotIn('_auth_user_id', self.client.session)
        self.user.is_active = True
        self.user.save()
        get_user_model().objects.create_user('another-parent', email='PARENT@example.com', password='Another-password-42!')
        response = self.client.post(reverse('shop:login'), {'email': 'parent@example.com', 'password': 'Testing-care-482!'})
        self.assertContains(response, 'The email address or password is incorrect.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_parallel_validated_signup_forms_cannot_create_duplicate_email(self):
        from django.db import IntegrityError, transaction
        from shop.forms import RegistrationForm
        data = {'email': 'new@gmail.com', 'password1': 'Unique-care-482!', 'password2': 'Unique-care-482!'}
        first, second = RegistrationForm(data), RegistrationForm(data)
        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)
        first.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            second.save()
        self.assertEqual(get_user_model().objects.filter(email='new@gmail.com').count(), 1)

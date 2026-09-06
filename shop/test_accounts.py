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
            self.assertContains(response, 'autocomplete="username"')
            self.assertIn('no-store', response['Cache-Control'])

    def test_login_safe_redirect_and_post_only_logout(self):
        response = self.client.post(reverse('shop:login'), {'username': 'petparent', 'password': 'Testing-care-482!', 'next': 'https://example.invalid/'})
        self.assertEqual(response.url, reverse('shop:profile'))
        self.assertEqual(self.client.get(reverse('shop:logout')).status_code, 405)
        self.client.post(reverse('shop:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_keeps_next_and_merges_baskets_once(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=3)
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 2})
        response = self.client.post(reverse('shop:login'), {'username': 'petparent', 'password': 'Testing-care-482!', 'next': '/checkout/'})
        self.assertEqual(response.url, '/checkout/')
        self.assertEqual(cart.items.get().quantity, 5)
        self.client.post(reverse('shop:logout'))
        self.client.post(reverse('shop:login'), {'username': 'petparent', 'password': 'Testing-care-482!'})
        self.assertEqual(cart.items.get().quantity, 5)

    def test_registration_merges_guest_cart_but_never_grants_staff_access(self):
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 2})
        response = self.client.post(reverse('shop:register'), {'username': 'newparent', 'email': 'new@example.com',
            'password1': 'Testing-care-482!', 'password2': 'Testing-care-482!', 'next': '/checkout/', 'is_staff': 'on'})
        self.assertEqual(response.url, '/checkout/')
        user = get_user_model().objects.get(username='newparent')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.cart.items.get().quantity, 2)
        self.assertEqual(self.client.get(reverse('crm:dashboard')).status_code, 403)

    def test_validation_errors_preserve_username_and_do_not_echo_password(self):
        response = self.client.post(reverse('shop:login'), {'username': 'petparent', 'password': 'wrong-password'})
        self.assertContains(response, 'value="petparent"')
        self.assertNotContains(response, 'value="wrong-password"')
        self.assertContains(response, 'auth-error')
        response = self.client.post(reverse('shop:register'), {'username': 'newparent', 'email': 'PARENT@example.com', 'password1': '123', 'password2': '456'})
        self.assertContains(response, 'An account already uses this email address.')
        self.assertFalse(get_user_model().objects.filter(username='newparent').exists())

    def test_authentication_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('shop:login'), {}).status_code, 403)
        self.assertEqual(client.post(reverse('shop:register'), {}).status_code, 403)

    def test_auth_redirect_does_not_loop_back_to_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('shop:login'), {'next': '/login/'})
        self.assertEqual(response.url, reverse('shop:profile'))

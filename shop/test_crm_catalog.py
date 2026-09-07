from io import BytesIO
from tempfile import TemporaryDirectory
from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Category, Product, ProductVariant, CRMActivity, Order
from .test_checkout import CHECKOUT_DATA


class CatalogEditorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_crm_roles', verbosity=0)
        cls.manager = get_user_model().objects.create_user('catalog-manager', is_staff=True)
        cls.manager.groups.add(Group.objects.get(name='Surya CRM Manager'))
        cls.viewer = get_user_model().objects.create_user('catalog-viewer', is_staff=True)
        cls.viewer.groups.add(Group.objects.get(name='Surya CRM Viewer'))
        cls.category = Category.objects.create(name='Dog')

    def setUp(self):
        self.product = Product.objects.create(name='Care essentials', category=self.category, base_price=100, selling_price=90, stock_quantity=10)
        self.client.force_login(self.manager)

    def payload(self, **overrides):
        return {'name': 'Care essentials', 'slug': 'care-essentials', 'category': self.category.pk,
                'base_price': '100', 'selling_price': '90', 'version': self.product.updated_at.isoformat(), **overrides}

    def test_manager_can_create_with_zero_stock_then_edit_without_stock_overwrite(self):
        response = self.client.post(reverse('crm:product_create'), self.payload(name='New supplement', slug='new-supplement', stock_quantity='500', track_inventory='false'))
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(slug='new-supplement')
        self.assertEqual(product.stock_quantity, 0)
        self.assertTrue(product.track_inventory)
        response = self.client.post(reverse('crm:product_edit', args=[self.product.pk]), self.payload(name='Updated care', selling_price='80', stock_quantity='999', slug='changed-handle'))
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(self.product.slug, 'care-essentials')
        self.assertEqual(self.product.current_price, 80)
        self.assertEqual(CRMActivity.objects.count(), 2)

    def test_duplicate_handle_and_invalid_price_do_not_create_products(self):
        for data in [self.payload(), self.payload(slug='new', selling_price='110'), self.payload(slug='new', base_price='-1')]:
            response = self.client.post(reverse('crm:product_create'), data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(Product.objects.count(), 1)

    def test_stale_editor_cannot_overwrite_newer_changes(self):
        payload = self.payload()
        self.product.name = 'Changed elsewhere'; self.product.save()
        response = self.client.post(reverse('crm:product_edit', args=[self.product.pk]), payload)
        self.assertContains(response, 'Reload before saving')
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Changed elsewhere')

    def test_archive_restore_preserves_orders_stock_and_requires_confirmation(self):
        from django.test import Client
        buyer = Client()
        buyer.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 1})
        token = buyer.get(reverse('shop:checkout')).context['checkout_token']
        buyer.post(reverse('shop:checkout'), {**CHECKOUT_DATA, 'checkout_token': token})
        order = Order.objects.get()
        self.product.refresh_from_db()
        archive = reverse('crm:product_archive', args=[self.product.pk])
        self.client.get(archive)
        self.product.refresh_from_db(); self.assertTrue(self.product.is_active)
        data = {'version': self.product.updated_at.isoformat(), 'reason': 'Temporarily discontinued'}
        self.assertEqual(self.client.post(archive, data).status_code, 302)
        self.product.refresh_from_db(); self.assertFalse(self.product.is_active)
        self.assertEqual(self.product.stock_quantity, 9)
        self.assertEqual(order.items.get().product_id, self.product.pk)
        self.assertEqual(order.items.get().unit_price, 90)
        self.assertEqual(self.client.get(reverse('shop:product_detail', args=[self.product.slug])).status_code, 404)
        self.assertEqual(self.client.post(archive, data).status_code, 200)  # duplicate stale POST cannot restore
        self.product.refresh_from_db(); self.assertFalse(self.product.is_active)
        data['version'] = self.product.updated_at.isoformat()
        self.assertEqual(self.client.post(archive, data).status_code, 302)
        self.product.refresh_from_db(); self.assertTrue(self.product.is_active)

    def test_viewer_cannot_mutate_catalog(self):
        self.client.force_login(self.viewer)
        inventory = self.client.get(reverse('crm:inventory'))
        self.assertNotContains(inventory, reverse('crm:product_create'))
        for route in [reverse('crm:product_create'), reverse('crm:product_edit', args=[self.product.pk]), reverse('crm:product_archive', args=[self.product.pk])]:
            self.assertEqual(self.client.get(route).status_code, 403)
            self.assertEqual(self.client.post(route, self.payload()).status_code, 403)

    def test_variant_price_edit_preserves_stock_and_checks_parent(self):
        pack = ProductVariant.objects.create(product=self.product, name='Small pack', price_override=100, selling_price=90, stock_quantity=8)
        response = self.client.post(reverse('crm:variant_edit', args=[self.product.pk, pack.pk]), {
            'name': 'Small pack', 'price_override': '100', 'selling_price': '75', 'version': pack.updated_at.isoformat(), 'stock_quantity': '999'})
        self.assertEqual(response.status_code, 302)
        pack.refresh_from_db(); self.assertEqual(pack.current_price, 75); self.assertEqual(pack.stock_quantity, 8)
        other = Product.objects.create(name='Other', category=self.category, base_price=1)
        self.assertEqual(self.client.get(reverse('crm:variant_edit', args=[other.pk, pack.pk])).status_code, 404)

    def test_image_upload_uses_media_storage_and_keeps_previous_image(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            for index in range(2):
                buffer = BytesIO(); Image.new('RGB', (12, 12), 'green').save(buffer, format='PNG')
                self.product.refresh_from_db()
                data = self.payload(image=SimpleUploadedFile(f'photo-{index}.png', buffer.getvalue(), content_type='image/png'), image_alt='Product box')
                response = self.client.post(reverse('crm:product_edit', args=[self.product.pk]), data)
                self.assertEqual(response.status_code, 302)
            self.assertEqual(self.product.images.count(), 2)
            self.assertEqual(self.product.images.filter(is_primary=True).count(), 1)
            photo = self.product.images.first()
            self.assertTrue(photo.image.storage.exists(photo.image.name))
            self.assertEqual(photo.alt_text, 'Product box')

    def test_invalid_upload_does_not_change_product(self):
        data = self.payload(name='Should not save', image=SimpleUploadedFile('bad.png', b'not an image', content_type='image/png'))
        response = self.client.post(reverse('crm:product_edit', args=[self.product.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('image', response.context['form'].errors)
        self.product.refresh_from_db(); self.assertEqual(self.product.name, 'Care essentials')

    def test_archived_filter_and_forms_render(self):
        self.product.is_active = False; self.product.save()
        response = self.client.get(reverse('crm:inventory'), {'visibility': 'archived'})
        self.assertContains(response, 'Care essentials')
        self.assertContains(response, 'Restore')
        for route in [reverse('crm:product_create'), reverse('crm:product_edit', args=[self.product.pk]), reverse('crm:product_archive', args=[self.product.pk])]:
            self.assertEqual(self.client.get(route).status_code, 200)

"""Real review workflow tests; storefront restrictions are deliberately not enabled."""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from shop.models import Category, Product, ProductVariant, ProductImage, CatalogReviewEvent, InventoryMovement, Order
from shop.services.catalog_approval import decide, review_token, status, issues, snapshot


class CatalogApprovalTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user('reviewer', is_staff=True)
        self.staff.user_permissions.add(*Permission.objects.filter(content_type__app_label='shop', codename__in=['access_crm', 'approve_catalog']))
        self.product = Product.objects.create(name='Exact food pack', category=Category.objects.create(name='Dogs'),
            sku='FOOD', base_price=Decimal('100.00'), selling_price=Decimal('90.00'), stock_quantity=10)
        self.photo = ProductImage.objects.create(product=self.product, source_url='https://example.com/exact-food.jpg')
        self.pack = ProductVariant.objects.create(product=self.product, name='3 KG', sku='FOOD-3KG', stock_quantity=10, image=self.photo)
        self.url = reverse('crm:catalog_review', args=[self.product.pk])
        self.client.force_login(self.staff)

    def approve(self, **changes):
        data = dict(token=review_token(self.staff, self.product), decision='approved',
            evidence='Supplier price list and warehouse count, 25 September 2026, Mumbai.',
            identity=True, prices=True, inventory=True)
        data.update(changes)
        return decide(self.staff, self.product.pk, **data)

    def test_default_needs_review_not_automatic_approval(self):
        self.assertEqual(status(self.product), 'Needs review')
        self.assertEqual(issues(self.product), [])

    def test_decision_records_actor_and_snapshot_without_catalog_mutation(self):
        before = snapshot(self.product, stock=True)
        event = self.approve()
        self.product.refresh_from_db()
        self.assertEqual(status(self.product), 'Reviewed')
        self.assertEqual(before, snapshot(self.product, stock=True))
        self.assertEqual(event.actor, self.staff)
        self.assertEqual(event.snapshot['packs'][0]['sku'], 'FOOD-3KG')
        self.assertTrue(event.snapshot['attestations']['inventory'])
        self.assertEqual(InventoryMovement.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)

    def test_review_only_keeps_existing_storefront_and_cart_behavior(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('shop:product_detail', args=[self.product.slug])).status_code, 200)
        response = self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'variant_id': self.pack.pk})
        self.assertEqual(response.status_code, 302)
        from shop.models import CartItem
        self.assertEqual(CartItem.objects.get().product_variant, self.pack)

    def test_staff_without_explicit_permission_cannot_approve(self):
        other = get_user_model().objects.create_user('operations', is_staff=True)
        other.user_permissions.add(Permission.objects.get(codename='access_crm'))
        with self.assertRaises(PermissionDenied):
            decide(other, self.product.pk, '', 'approved', 'An unapproved review attempt')
        self.client.force_login(other)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {}).status_code, 403)

    def test_customer_with_permission_still_requires_staff(self):
        self.staff.is_staff = False
        self.staff.save()
        with self.assertRaises(PermissionDenied):
            self.approve()

    def test_anonymous_redirect_and_private_headers(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertContains(response, 'Purchase safety is enforced')
        self.assertIn('private', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('noindex', response['X-Robots-Tag'])

    def test_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(client.post(self.url, {}).status_code, 403)

    def test_zero_price_blocks_review(self):
        self.pack.selling_price = 0
        self.pack.save()
        with self.assertRaisesMessage(ValidationError, 'positive selling price'):
            self.approve()
        self.assertFalse(CatalogReviewEvent.objects.exists())

    def test_price_above_mrp_blocks_review(self):
        self.pack.selling_price = 101
        self.pack.save()
        with self.assertRaisesMessage(ValidationError, 'not exceeding MRP'):
            self.approve()

    def test_missing_sku_blocks_review(self):
        self.pack.sku = ''
        self.pack.save()
        with self.assertRaisesMessage(ValidationError, 'exact SKU'):
            self.approve()

    def test_missing_image_blocks_review(self):
        self.photo.delete()
        with self.assertRaisesMessage(ValidationError, 'exact-product image'):
            self.approve()

    def test_missing_local_file_blocks_review(self):
        self.photo.image = 'products/does-not-exist-review-test.webp'
        self.photo.save()
        with self.assertRaisesMessage(ValidationError, 'could not be verified'):
            self.approve()

    def test_multivariant_requires_each_exact_image(self):
        ProductVariant.objects.create(product=self.product, name='5 KG', sku='FOOD-5KG', stock_quantity=2)
        with self.assertRaisesMessage(ValidationError, 'assign each pack image'):
            self.approve()

    def test_zero_stock_can_be_reviewed_without_inventing_stock(self):
        self.pack.stock_quantity = 0
        self.pack.save()
        self.approve()
        self.pack.refresh_from_db()
        self.assertEqual(self.pack.stock_quantity, 0)

    def test_all_attestations_and_source_required(self):
        for field in ['identity', 'prices', 'inventory']:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.approve(**{field: False})
        with self.assertRaises(ValidationError):
            self.approve(evidence='ok')

    def test_invalid_form_does_not_approve(self):
        response = self.client.post(self.url, {'token': review_token(self.staff, self.product), 'decision': 'approved',
            'evidence': 'Dated warehouse and supplier source reference'})
        self.assertContains(response, 'Complete all three checks')
        self.assertFalse(CatalogReviewEvent.objects.exists())

    def test_valid_post_and_replay(self):
        data = {'token': review_token(self.staff, self.product), 'decision': 'approved', 'identity': 'on',
                'prices': 'on', 'inventory': 'on', 'evidence': 'Dated source and warehouse count, Mumbai 2026-09-25'}
        self.assertRedirects(self.client.post(self.url, data), self.url)
        self.assertContains(self.client.post(self.url, data), 'Reload and verify')
        self.assertEqual(CatalogReviewEvent.objects.count(), 1)

    def test_stale_price_or_stock_token_rejected(self):
        for field, value in [('stock_quantity', 9), ('selling_price', Decimal('85.00'))]:
            token = review_token(self.staff, self.product)
            ProductVariant.objects.filter(pk=self.pack.pk).update(**{field: value})
            with self.assertRaisesMessage(ValidationError, 'changed'):
                self.approve(token=token)

    def test_token_cannot_be_used_by_another_reviewer(self):
        token = review_token(self.staff, self.product)
        other = get_user_model().objects.create_superuser('other-reviewer', password='test-only')
        with self.assertRaises(ValidationError):
            decide(other, self.product.pk, token, 'held', 'Wrong actor cannot reuse this review')

    def test_bulk_catalog_edit_makes_review_stale(self):
        self.approve()
        ProductVariant.objects.filter(pk=self.pack.pk).update(selling_price=Decimal('80'))
        self.product.refresh_from_db()
        self.assertEqual(status(self.product), 'Changed — review again')

    def test_image_change_makes_review_stale(self):
        self.approve()
        ProductImage.all_objects.filter(pk=self.photo.pk).update(is_active=False)
        self.product.refresh_from_db()
        self.assertEqual(status(self.product), 'Changed — review again')

    def test_normal_stock_movement_does_not_change_approved_identity(self):
        self.approve()
        ProductVariant.objects.filter(pk=self.pack.pk).update(stock_quantity=9)
        self.product.refresh_from_db()
        self.assertEqual(status(self.product), 'Reviewed')

    def test_hold_preserves_previous_event(self):
        first = self.approve()
        self.product.refresh_from_db()
        self.approve(decision='held')
        self.product.refresh_from_db()
        self.assertEqual(status(self.product), 'Needs review')
        self.assertEqual(CatalogReviewEvent.objects.count(), 2)
        first.refresh_from_db()
        self.assertEqual(first.decision, 'approved')

    def test_simple_product_review(self):
        self.pack.delete()
        self.approve()
        self.product.refresh_from_db()
        self.assertEqual(status(self.product), 'Reviewed')

    def test_inventory_filters_and_review_link(self):
        response = self.client.get(reverse('crm:inventory'), {'review': 'pending'})
        self.assertContains(response, self.url)
        self.approve()
        response = self.client.get(reverse('crm:inventory'), {'review': 'recorded'})
        self.assertContains(response, 'Reviewed')
        response = self.client.get(reverse('crm:inventory'), {'review': 'pending'})
        self.assertNotContains(response, self.product.name)

    def test_review_notes_never_appear_on_storefront(self):
        self.approve(evidence='INTERNAL-ONLY-REVIEW-REFERENCE 2026-09-25')
        self.client.logout()
        response = self.client.get(reverse('shop:product_detail', args=[self.product.slug]))
        self.assertNotContains(response, 'INTERNAL-ONLY')

    def test_review_events_read_only_in_admin(self):
        from django.contrib import admin
        from django.test import RequestFactory
        event_admin = admin.site._registry[CatalogReviewEvent]
        request = RequestFactory().get('/')
        request.user = self.staff
        self.assertFalse(event_admin.has_add_permission(request))
        self.assertFalse(event_admin.has_change_permission(request))
        self.assertFalse(event_admin.has_delete_permission(request))

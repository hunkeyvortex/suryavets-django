from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Permission
from shop.models import Category, Product, ProductVariant, ProductImage, CatalogReviewEvent
from shop.services.homepage import homepage_context
from shop.services.merchandising import eligibility
from shop.catalog_views import _product_queryset


class MerchandisingTests(TestCase):
    def setUp(self):
        self.mock = patch('shop.services.merchandising.snapshot', return_value={'generated_at': 'test', 'by_product': {}})
        self.evidence = self.mock.start()
        self.addCleanup(self.mock.stop)
        self.category = Category.objects.create(name='Dog')
        self.product = self.make('Good pack')

    def make(self, name, **kwargs):
        product = Product.objects.create(name=name, category=self.category, base_price=100,
            is_bestseller=True, merchandising_active=True, **kwargs)
        ProductVariant.objects.create(product=product, name='1 KG', stock_quantity=10)
        ProductImage.objects.create(product=product, source_url='https://example.com/exact.jpg')
        return product

    def listed(self):
        return homepage_context()['top_products']

    def test_imported_flags_cannot_publish(self):
        Product.objects.update(merchandising_active=False)
        Product.objects.bulk_create([Product(name=f'Imported {i}', slug=f'imported-{i}', category=self.category,
            base_price=100, is_bestseller=True, is_featured=True) for i in range(1001)])
        self.assertEqual(self.listed(), [])

    @override_settings(HOMEPAGE_MERCHANDISING_LIMIT=2)
    def test_rank_and_configured_limit(self):
        first = self.make('Rank first', merchandising_rank=1)
        second = self.make('Rank second', merchandising_rank=2)
        self.assertEqual(self.listed(), [first, second])

    def test_inactive_zero_price_and_hold_excluded(self):
        inactive = self.make('Inactive', is_active=False)
        zero = self.make('Zero')
        zero.variants.update(selling_price=0)
        blocked = self.make('Blocked')
        CatalogReviewEvent.objects.create(product=blocked, decision='held', evidence='Review required')
        self.assertEqual(self.listed(), [self.product])

    def test_family_once_with_valid_sibling(self):
        self.product.variants.update(selling_price=0)
        child = self.make('Sibling', variant_family=self.product)
        self.assertEqual(self.listed(), [self.product])

    def test_p0_on_family_member_blocks_family(self):
        child = self.make('Sibling', variant_family=self.product)
        self.evidence.return_value = {'generated_at': 'test', 'by_product': {str(child.pk): [{'Priority': 'P0'}]}}
        self.assertEqual(self.listed(), [])

    def test_missing_image_and_missing_evidence_fail_closed(self):
        self.product.images.all().delete()
        self.assertEqual(self.listed(), [])
        self.evidence.return_value = {'generated_at': '', 'by_product': {}}
        self.make('Another')
        self.assertEqual(self.listed(), [])

    def test_no_mutation_on_render(self):
        before = list(Product.objects.values())
        variants = list(ProductVariant.objects.values())
        self.client.get('/')
        self.assertEqual(before, list(Product.objects.values()))
        self.assertEqual(variants, list(ProductVariant.objects.values()))

    def test_later_import_preserves_active_manual_labels(self):
        from shop.management.commands.import_shopify_products import Command
        self.product.is_bestseller = False
        self.product.is_featured = True
        self.product.save()
        row = {'Handle': self.product.slug, 'Title': self.product.name, 'Tags': 'best-seller',
            'Variant Price': '100', 'Option1 Value': '1 KG', 'Variant Inventory Qty': '10'}
        Command()._import_group(self.product.slug, [row], {}, False)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_bestseller)
        self.assertTrue(self.product.is_featured)
        self.assertTrue(self.product.merchandising_active)

    def test_broken_local_image_excluded(self):
        self.product.images.update(image='missing-pack-file.webp', source_url='')
        self.assertEqual(self.listed(), [])

    def test_crm_permissions_and_safe_bulk_fields(self):
        url = '/crm/merchandising/'
        self.assertEqual(self.client.get(url).status_code, 302)
        staff = User.objects.create_user('staff', is_staff=True)
        staff.user_permissions.add(*Permission.objects.filter(codename__in=['access_crm', 'view_product']))
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code, 200)
        payload = {'products': [str(self.product.pk)], 'merchandising_active': 'on', 'is_featured': 'on',
            'is_new_arrival': 'on', 'is_promotional': 'on', 'merchandising_rank': 3, 'stock_quantity': 999, 'base_price': 0}
        self.assertEqual(self.client.post(url, payload).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename='change_product'))
        stock = self.product.stock_quantity
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.base_price, 100)
        self.assertEqual(self.product.stock_quantity, stock)
        self.assertTrue(self.product.is_new_arrival and self.product.is_promotional and self.product.is_featured)
        self.assertFalse(self.product.is_bestseller)
        self.assertEqual(self.product.merchandising_rank, 3)
        self.assertEqual(homepage_context()['home_best_title'], 'Featured picks')

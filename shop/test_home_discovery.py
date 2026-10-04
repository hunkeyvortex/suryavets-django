from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from unittest.mock import patch
from .models import Brand, Category, Product, ProductVariant, ProductImage
from .services.homepage import homepage_context


class HomeDiscoveryTests(TestCase):
    def setUp(self):
        self.evidence = patch('shop.services.merchandising.snapshot', return_value={'generated_at': 'test', 'by_product': {}})
        self.evidence.start()
        self.addCleanup(self.evidence.stop)
        self.dog = Category.objects.create(name='Dog', slug='dog')
        self.food = Category.objects.create(name='Dog Food', slug='food-for-dogs', parent=self.dog)
        self.wet = Category.objects.create(name='Wet Food', parent=self.food)
        self.cat = Category.objects.create(name='Cat', slug='cat')
        self.cat_food = Category.objects.create(name='Cat Food', slug='food-for-cats', parent=self.cat)
        self.brand = Brand.objects.create(name='Test brand')
        self.product = Product.objects.create(name='Daily food', category=self.wet, brand=self.brand,
            base_price=100, is_bestseller=True, stock_quantity=10, merchandising_active=True)
        ProductImage.objects.create(product=self.product, source_url='https://example.com/pack.jpg')
        self.pack = ProductVariant.objects.create(product=self.product, name='3 KG', selling_price=90, stock_quantity=10)

    def test_sections_are_database_driven_and_preserve_purchase_controls(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['top_products'], [self.product])
        self.assertContains(response, 'Top Selling Products')
        self.assertContains(response, 'Mealtime favourites')
        self.assertContains(response, 'Shop by need')
        self.assertContains(response, 'Shop by brand')
        self.assertContains(response, '3 KG')
        self.assertContains(response, 'data-card-add')
        self.assertContains(response, 'name="quantity" value="1"')
        self.assertNotContains(response, 'data-card-step')

    def test_collection_membership_and_descendants_do_not_duplicate_food_cards(self):
        self.product.collections.add(self.food, self.wet)
        other = Product.objects.create(name='Cat food', category=self.cat_food, base_price=200)
        other.merchandising_active = True
        other.save()
        ProductVariant.objects.create(product=other, name='1 KG', stock_quantity=10)
        ProductImage.objects.create(product=other, source_url='https://example.com/cat.jpg')
        context = homepage_context()
        self.assertEqual(context['home_food_tabs'][0]['products'], [self.product])
        self.assertEqual(context['home_food_tabs'][1]['products'], [other])

    def test_hidden_products_and_family_children_never_become_extra_cards(self):
        Product.objects.create(name='Hidden', category=self.food, base_price=1, is_bestseller=True, is_active=False)
        Product.objects.create(name='Family child', category=self.food, base_price=1, is_bestseller=True, variant_family=self.product)
        self.assertEqual(homepage_context()['top_products'], [self.product])

    def test_inactive_ancestor_hides_food_tab_and_need_link(self):
        self.dog.is_active = False
        self.dog.save()
        context = homepage_context()
        self.assertEqual(context['home_food_tabs'], [])
        self.assertNotIn(self.food, [item['category'] for item in context['home_needs']])

    def test_featured_fallback_is_not_mislabelled_as_best_selling(self):
        self.product.is_bestseller = False
        self.product.is_featured = True
        self.product.save()
        context = homepage_context()
        self.assertEqual(context['home_best_title'], 'Featured picks')
        self.assertEqual(context['top_products'], [self.product])

    def test_brand_counts_ignore_hidden_products_and_linked_children(self):
        Product.objects.create(name='Hidden', category=self.food, brand=self.brand, base_price=1, is_active=False)
        Product.objects.create(name='Child', category=self.food, brand=self.brand, base_price=1, variant_family=self.product)
        brand = list(homepage_context()['home_brands'])[0]
        self.assertEqual(brand.product_count, 1)
        self.assertContains(self.client.get('/'), f'?brand={self.brand.slug}')

    def test_uncategorized_not_promoted_as_pet(self):
        Category.objects.create(name='Uncategorized', slug='uncategorized')
        self.assertNotIn('uncategorized', [c.slug for c in homepage_context()['categories']])

    def test_queries_and_product_counts_stay_bounded(self):
        for number in range(20):
            p = Product.objects.create(name=f'Extra {number}', category=self.food, base_price=100, is_bestseller=True, merchandising_active=True)
            ProductImage.objects.create(product=p, source_url='https://example.com/pack.jpg')
            ProductVariant.objects.create(product=p, name='Pack', stock_quantity=10)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/')
        self.assertEqual(len(response.context['top_products']), 8)
        self.assertEqual(len(response.context['home_food_tabs'][0]['products']), 4)
        self.assertLess(len(queries), 65)

    def test_home_prefers_real_selected_pack_images_without_changing_catalog(self):
        pictured = Product.objects.create(name='Photographed food', category=self.food, base_price=100, is_bestseller=True, merchandising_active=True, merchandising_rank=1)
        ProductImage.objects.create(product=pictured, source_url='https://example.com/actual-product.jpg')
        ProductVariant.objects.create(product=pictured, name='1 KG', stock_quantity=10)
        context = homepage_context()
        self.assertEqual(context['top_products'][0], pictured)
        self.assertIn(self.product, context['top_products'])
        self.assertEqual(Product.objects.count(), 2)

    def test_empty_catalog_and_mobile_destinations_are_safe(self):
        Product.objects.all().delete()
        response = self.client.get('/')
        self.assertNotContains(response, 'id="best-sellers"')
        self.assertContains(response, 'aria-label="Mobile navigation"')
        self.assertContains(response, 'data-category-sheet-open')
        for route in ('profile', 'wishlist'):
            self.assertEqual(self.client.get(reverse(f'shop:{route}')).status_code, 302)

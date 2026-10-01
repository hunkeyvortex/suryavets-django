"""Catalog query regressions: bounded work, exact prices and unique listings."""
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .catalog_views import _apply_catalog_controls, _product_queryset
from .models import Category, PetCategory, Product, ProductVariant
from .services.pricing import catalog_price_expression
from .services.product_cards import product_card


class CatalogQueryRegressionTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Dogs', slug='dogs')
        self.root = self.product('Family', base_price='500')
        self.pack = ProductVariant.objects.create(product=self.root, name='1 kg',
            sku='ROOT-PACK-UNIQUE', selling_price='180', stock_quantity=2)
        self.member = self.product('Family large', variant_family=self.root)
        self.large = ProductVariant.objects.create(product=self.member, name='2 kg',
            sku='MEMBER-PACK-UNIQUE', selling_price='300', stock_quantity=2)
        self.simple = self.product('Simple', selling_price='220')
        self.list_url = reverse('shop:category_list')

    def product(self, name, **fields):
        return Product.objects.create(name=name, category=self.category,
            **{'base_price': '250', 'stock_quantity': 3, **fields})

    def controlled(self, **params):
        return _apply_catalog_controls(RequestFactory().get('/', params), _product_queryset())[0]

    def ids(self, **params):
        return list(self.controlled(**params).values_list('pk', flat=True))

    def test_default_browsing_and_search_do_not_build_price_subqueries(self):
        with patch('shop.catalog_views.catalog_price_expression', side_effect=AssertionError('Unnecessary price scan')):
            for url, params in ((self.list_url, {}), (self.list_url, {'sort': 'newest'}),
                                (reverse('shop:search'), {'q': 'Family'}),
                                (reverse('shop:category_detail', args=['dogs']), {})):
                with self.subTest(url=url, params=params):
                    self.assertEqual(self.client.get(url, params).status_code, 200)

    def test_page_counts_catalog_only_once(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.list_url)
        self.assertEqual(response.context['total_count'], 2)
        counts = [q['sql'] for q in queries if 'COUNT(*) AS "__count"' in q['sql'] and 'shop_product' in q['sql']]
        self.assertEqual(len(counts), 1, counts)

    def test_unused_featured_context_does_not_fetch_products(self):
        from shop.context_processors import get_featured_products
        with self.assertNumQueries(0):
            context = get_featured_products(RequestFactory().get('/search/?q=Family'))
        self.assertIn('featured_products', context)

    def test_price_sorting_does_not_project_price_into_count(self):
        queryset = self.controlled(sort='price_low')
        self.assertNotIn('catalog_price', queryset.query.annotation_select)
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(queryset.count(), 2)
        self.assertNotIn('shop_productvariant', queries[0]['sql'])

    def test_collection_primary_and_multiple_descendants_do_not_duplicate(self):
        child = Category.objects.create(name='Food', parent=self.category)
        self.root.collections.add(self.category, child)
        response = self.client.get(reverse('shop:category_detail', args=['dogs']))
        self.assertEqual(response.context['total_count'], 2)
        self.assertEqual(len({p.pk for p in response.context['products']}), 2)

    def test_search_matches_root_and_member_variant_skus_once(self):
        for query in ('ROOT-PACK-UNIQUE', 'MEMBER-PACK-UNIQUE', 'Family'):
            with self.subTest(query=query):
                response = self.client.get(reverse('shop:search'), {'q': query})
                self.assertEqual(list(response.context['products']), [self.root])
                self.assertEqual(response.context['total_count'], 1)

    def test_pet_filter_has_unique_results(self):
        pet = PetCategory.objects.create(name='Dog', slug='dog')
        self.root.pet_categories.add(pet)
        self.assertEqual(self.ids(pet='dog'), [self.root.pk])

    def test_price_filter_and_order_match_available_family_pack(self):
        self.pack.stock_quantity = 0
        self.pack.save()
        self.assertEqual(self.ids(sort='price_low'), [self.simple.pk, self.root.pk])
        self.assertEqual(self.ids(sort='price_high'), [self.root.pk, self.simple.pk])
        self.assertEqual(self.ids(min_price='299.99', max_price='300'), [self.root.pk])
        self.assertEqual(self.ids(max_price='200'), [])

    def test_all_out_of_stock_has_no_purchasable_price(self):
        ProductVariant.objects.update(stock_quantity=0)
        self.assertEqual(self.ids(max_price='180', availability='out_of_stock'), [])
        self.assertEqual(self.ids(availability='out_of_stock'), [self.root.pk])
        self.assertEqual(self.ids(availability='in_stock'), [self.simple.pk])

    def test_inactive_member_and_inactive_packs_are_excluded_from_offers(self):
        self.member.is_active = False
        self.member.save()
        self.large.selling_price = Decimal('1')
        self.large.save()
        ProductVariant.objects.create(product=self.root, name='Disabled', selling_price='0.50', is_active=False)
        self.assertEqual(self.ids(max_price='180'), [self.root.pk])
        self.assertEqual(self.ids(max_price='179.99'), [])
        self.pack.stock_quantity = 0
        self.pack.save()
        self.assertEqual(self.ids(availability='out_of_stock'), [self.root.pk])

    def test_disabled_packs_do_not_fall_back_to_base_stock(self):
        ProductVariant.objects.update(is_active=False)
        self.assertEqual(self.ids(availability='out_of_stock'), [self.root.pk])
        self.assertEqual(self.ids(availability='in_stock'), [self.simple.pk])

    def test_untracked_simple_product_remains_available(self):
        self.simple.track_inventory = False
        self.simple.stock_quantity = 0
        self.simple.save()
        self.assertIn(self.simple.pk, self.ids(availability='in_stock'))

    def test_legacy_paise_and_zero_exact_price_match_cards(self):
        self.pack.selling_price = None
        self.pack.price_override = Decimal('115')
        self.pack.discount_percentage = 17
        self.pack.save()
        for expected in (Decimal('95.45'), Decimal('300')):
            if expected == Decimal('300'):
                self.pack.selling_price = Decimal('0')
                self.pack.save()
            product = _product_queryset().annotate(offer=catalog_price_expression()).get(pk=self.root.pk)
            self.assertEqual(product.offer, expected)
            self.assertEqual(product_card(product)['selected']['price'], expected)
            self.assertEqual(self.ids(min_price=str(expected), max_price=str(expected)), [self.root.pk])

    def test_invalid_prices_are_ignored_without_price_scan(self):
        for value in ('NaN', 'Infinity', '-1', 'bad'):
            with self.subTest(value=value), patch('shop.catalog_views.catalog_price_expression', side_effect=AssertionError):
                self.assertEqual(len(self.ids(min_price=value, max_price=value)), 2)

    def test_pagination_has_stable_tiebreaker_and_no_overlap(self):
        for n in range(14):
            self.product(f'Tied {n}')
        Product.objects.update(created_at=self.root.created_at)
        first = self.client.get(self.list_url)
        second = self.client.get(self.list_url, {'page': 2})
        first_ids = [p.pk for p in first.context['products']]
        second_ids = [p.pk for p in second.context['products']]
        self.assertFalse(set(first_ids) & set(second_ids))
        self.assertEqual(first_ids + second_ids, sorted(first_ids + second_ids))
        self.assertEqual(len(first_ids + second_ids), 16)

    def test_card_rendering_uses_prefetch_without_per_product_queries(self):
        for n in range(10):
            product = self.product(f'Packed {n}')
            ProductVariant.objects.create(product=product, name='Pack', selling_price='100', stock_quantity=1)
        products = list(_product_queryset())
        with self.assertNumQueries(0):
            for product in products:
                product_card(product)

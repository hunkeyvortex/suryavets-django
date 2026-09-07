from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from .models import Product, ProductVariant, ProductImage, Category, CartItem
from .services.product_cards import product_card
from .catalog_views import _product_queryset


class ProductCardTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Verified food', category=Category.objects.create(name='Dog'), base_price=Decimal('200'), stock_quantity=10)
        self.small = ProductVariant.objects.create(product=self.product, name='3 kg', price_override=200, selling_price=180, stock_quantity=10)
        self.large = ProductVariant.objects.create(product=self.product, name='6 kg', price_override=400, selling_price=320, stock_quantity=4)

    def test_only_verified_active_packs_are_rendered(self):
        ProductVariant.objects.create(product=self.product, name='Not published', is_active=False)
        response = self.client.get(reverse('shop:category_list'))
        self.assertContains(response, '3 kg'); self.assertContains(response, '6 kg')
        self.assertNotContains(response, '12 kg'); self.assertNotContains(response, 'Not published')
        self.assertContains(response, 'name="variant_id"')
        self.assertContains(response, 'data-card-add')
        self.assertContains(response, '<input type="hidden" name="quantity" value="1">')
        self.assertNotContains(response, 'data-card-step')
        self.assertNotContains(response, 'sv-card__stepper')

    def test_selection_savings_stock_and_query_reuse(self):
        product = _product_queryset().get(pk=self.product.pk)
        with self.assertNumQueries(0):
            card = product_card(product)
        self.assertEqual(card['selected']['variant'], self.small)
        self.assertEqual(card['selected']['saving'], 20)
        self.assertEqual(card['selected']['discount'], 10)
        self.small.stock_quantity = 0; self.small.save()
        self.assertEqual(product_card(self.product)['selected']['variant'], self.large)

    def test_linked_pack_uses_own_photo_price_and_stock(self):
        source = Product.objects.create(name='Large source', category=self.product.category, base_price=600, variant_family=self.product)
        pack = ProductVariant.objects.create(product=source, name='10 kg', selling_price=500, price_override=600, stock_quantity=2)
        photo = ProductImage.objects.create(product=source, source_url='https://example.com/exact-large.webp')
        option = next(o for o in product_card(self.product)['choices'] if o['variant'] == pack)
        self.assertEqual(option['image'], photo.display_url)
        self.assertEqual(option['price'], 500); self.assertEqual(option['max_quantity'], 2)
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'variant_id': pack.pk, 'quantity': 2, 'price': '0.01'})
        item = CartItem.objects.get(); self.assertEqual(item.product_id, source.pk); self.assertEqual(item.total_price, 1000)

    def test_missing_pack_photo_never_uses_another_pack_photo(self):
        ProductImage.objects.create(product=self.product, source_url='https://example.com/unknown-pack.webp')
        self.assertEqual(product_card(self.product)['selected']['image'], '')
        photo = ProductImage.objects.create(product=self.product, source_url='https://example.com/small.webp')
        self.small.image = photo; self.small.save()
        self.assertEqual(product_card(self.product)['selected']['image'], photo.display_url)

    def test_all_disabled_packs_and_simple_products(self):
        self.product.variants.update(is_active=False)
        card = product_card(self.product)
        self.assertEqual(card['choices'], []); self.assertFalse(card['selected']['available'])
        simple = Product.objects.create(name='No packs', category=self.product.category, base_price=Decimal('100'), stock_quantity=3)
        card = product_card(simple)
        self.assertEqual(card['choices'], []); self.assertTrue(card['selected']['available'])
        self.assertEqual(card['selected']['max_quantity'], 3)

    def test_more_sizes_and_safe_anonymous_wishlist_link(self):
        for n in range(4):
            ProductVariant.objects.create(product=self.product, name=f'Extra verified {n}', stock_quantity=10)
        response = self.client.get(reverse('shop:category_list'))
        self.assertContains(response, 'More sizes (3)')
        self.assertContains(response, 'Sign in to save')
        self.assertNotContains(response, '/account/wishlist/save/')

import csv
import io
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from shop.management.commands.import_shopify_products import Command as Importer
from shop.models import Cart, CartItem, Category, Order, OrderItem, Product, ProductImage, ProductVariant
from shop.services.pricing import export_prices


class ExactPricingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Dog')
        self.product = Product.objects.create(name='Exact price test', slug='exact-price-test', category=self.category,
            base_price=Decimal('115.00'), discount_percentage=17, stock_quantity=10)
        self.row = {'Handle': self.product.slug, 'Title': self.product.name, 'Tags': 'dog',
            'Variant Price': '95.00', 'Variant Compare At Price': '115.00', 'Variant SKU': 'PACK-1',
            'Option1 Value': '30ML', 'Variant Inventory Tracker': 'shopify', 'Variant Inventory Qty': '10',
            'Image Src': 'https://cdn.shopify.com/test.jpg'}
        self.variant = ProductVariant.objects.create(product=self.product, name='30ML', sku='PACK-1',
            price_override=Decimal('115'), discount_percentage=17, stock_quantity=10)

    def repair(self, rows=None, apply=False):
        output = io.StringIO()
        with patch.object(Importer, '_product_groups', return_value=[(self.product.slug, rows or [self.row])]):
            call_command('restore_shopify_prices', 'unused.csv', apply=apply, stdout=output)
        return output.getvalue()

    def test_exact_prices_override_percentage_and_legacy_rounds_to_paise(self):
        self.assertEqual(self.product.current_price, Decimal('95.45'))
        self.product.selling_price = Decimal('95.00')
        self.variant.selling_price = Decimal('95.00')
        self.assertEqual(self.product.current_price, Decimal('95.00'))
        self.assertEqual(self.variant.current_price, Decimal('95.00'))
        self.assertTrue(self.product.is_on_sale)
        self.assertEqual(self.product.display_discount_percentage, 17)
        self.product.selling_price = Decimal('0.00')
        self.assertEqual(self.product.current_price, Decimal('0.00'))

    def test_zero_variant_override_is_not_replaced_by_parent_price(self):
        self.variant.price_override = Decimal('0.00')
        self.variant.discount_percentage = 0
        self.assertEqual(self.variant.original_price, Decimal('0.00'))
        self.assertEqual(self.variant.current_price, Decimal('0.00'))

    def test_invalid_or_missing_export_prices_are_rejected(self):
        for value in ('', 'NaN', 'Infinity', '-1', '1.234', '100000000', 'not a price'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                export_prices({**self.row, 'Variant Price': value})
        self.assertEqual(export_prices({**self.row, 'Variant Price': '0'})[1], Decimal('0'))
        self.assertEqual(export_prices({**self.row, 'Variant Compare At Price': ''})[:2], (Decimal('95'), Decimal('95')))

    def test_repair_is_read_only_by_default(self):
        self.assertIn('product_display_prices_corrected=1', self.repair())
        self.product.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertIsNone(self.product.selling_price)
        self.assertIsNone(self.variant.selling_price)

    def test_price_repair_preserves_cart_order_stock_and_image_references(self):
        cart_item = CartItem.objects.create(cart=Cart.objects.create(), product=self.product,
            product_variant=self.variant, quantity=2)
        order = Order.objects.create(email='test@example.com', subtotal='190.90', total='190.90')
        order_item = OrderItem.objects.create(order=order, product=self.product, product_variant=self.variant,
            product_name=self.product.name, unit_price='95.45', quantity=2)
        picture = ProductImage.objects.create(product=self.product, image='products/existing.jpg', source_url=self.row['Image Src'])
        self.repair(apply=True)
        self.product.refresh_from_db(); self.variant.refresh_from_db(); cart_item.refresh_from_db(); order_item.refresh_from_db(); picture.refresh_from_db()
        self.assertEqual(self.product.current_price, Decimal('95.00'))
        self.assertEqual(self.variant.current_price, Decimal('95.00'))
        self.assertEqual(cart_item.total_price, Decimal('190.00'))
        self.assertEqual(order_item.unit_price, Decimal('95.45'))
        self.assertEqual(order_item.product_variant_id, self.variant.pk)
        self.assertEqual(self.variant.stock_quantity, 10)
        self.assertEqual(picture.image.name, 'products/existing.jpg')
        self.assertIn('product_display_prices_corrected=0', self.repair(apply=True))

    def test_repair_aborts_on_ambiguous_or_missing_variant_identity(self):
        for row in ({**self.row, 'Variant SKU': 'CHANGED'}, {**self.row, 'Option1 Value': 'UNKNOWN'}):
            with self.assertRaises(CommandError):
                self.repair([row], apply=True)
            self.product.refresh_from_db()
            self.assertIsNone(self.product.selling_price)

    def test_importer_preserves_variant_and_downloaded_image_on_reimport(self):
        picture = ProductImage.objects.create(product=self.product, image='products/retained.jpg', source_url=self.row['Image Src'])
        cart_item = CartItem.objects.create(cart=Cart.objects.create(), product=self.product, product_variant=self.variant)
        for _ in range(2):
            Importer()._import_group(self.product.slug, [self.row], {}, False)
        self.variant.refresh_from_db(); picture.refresh_from_db(); cart_item.refresh_from_db()
        self.assertEqual(self.variant.current_price, Decimal('95.00'))
        self.assertEqual(cart_item.product_variant_id, self.variant.pk)
        self.assertEqual(picture.image.name, 'products/retained.jpg')
        self.assertEqual(self.product.images.count(), 1)
        self.assertEqual(self.product.variants.count(), 1)

    def test_split_zip_exports_merge_handles_and_deduplicate_variant_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            sources = []
            for number in (1, 2):
                stream = io.StringIO()
                writer = csv.DictWriter(stream, fieldnames=list(self.row)); writer.writeheader(); writer.writerow(self.row)
                source = Path(folder) / f'export-{number}.zip'
                with zipfile.ZipFile(source, 'w') as archive:
                    archive.writestr('products.csv', stream.getvalue())
                sources.append(str(source))
            importer = Importer()
            groups = list(importer._product_groups(sources))
            self.assertEqual(len(groups), 1)
            self.assertEqual(len(importer._priced_rows(*groups[0])), 1)
        with self.assertRaises(CommandError):
            Importer()._priced_rows(self.product.slug, [self.row, {**self.row, 'Variant Price': '96'}])

    def test_filters_and_sorting_use_displayed_selling_price_not_compare_at(self):
        self.product.selling_price = Decimal('95.00'); self.product.save()
        other = Product.objects.create(name='Second price', category=self.category, base_price='100.00', selling_price='100.00')
        response = self.client.get(reverse('shop:category_list'), {'max_price': '96', 'sort': 'price_low'})
        self.assertEqual(list(response.context['products']), [self.product])
        response = self.client.get(reverse('shop:category_list'), {'sort': 'price_low'})
        self.assertEqual(list(response.context['products']), [self.product, other])
        response = self.client.get(reverse('shop:category_list'), {'sort': 'price_high'})
        self.assertEqual(list(response.context['products']), [other, self.product])

    def test_legacy_price_filters_match_model_rounding(self):
        response = self.client.get(reverse('shop:category_list'), {'min_price': '95.45', 'max_price': '95.45'})
        self.assertEqual(list(response.context['products']), [self.product])

    def test_multiple_packs_require_an_explicit_choice(self):
        ProductVariant.objects.create(product=self.product, name='60ML', price_override='200', selling_price='180', stock_quantity=3)
        response = self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]), {'quantity': 1})
        self.assertRedirects(response, reverse('shop:product_detail', args=[self.product.slug]))
        self.assertFalse(CartItem.objects.exists())
        self.assertContains(self.client.get(reverse('shop:category_list')), 'Choose options')

    def test_selected_variant_is_priced_on_server_and_snapshotted_at_checkout(self):
        self.variant.selling_price = Decimal('95.00'); self.variant.save()
        self.client.post(reverse('shop:add_to_cart', args=[self.product.pk]),
            {'variant_id': self.variant.pk, 'quantity': 2, 'price': '0.01'})
        self.assertEqual(CartItem.objects.get().total_price, Decimal('190.00'))
        response = self.client.post(reverse('shop:checkout'), {
            'email': 'guest@example.com', 'phone': '9999999999', 'shipping_name': 'Guest Customer',
            'shipping_address_line_1': '1 Test Street', 'shipping_city': 'Mumbai',
            'shipping_state': 'Maharashtra', 'shipping_postal_code': '400001',
            'billing_same_as_shipping': 'on', 'payment_method': 'cash_on_delivery', 'terms': 'on',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OrderItem.objects.get().unit_price, Decimal('95.00'))
        self.assertEqual(Order.objects.get().subtotal, Decimal('190.00'))

    def test_product_page_starts_with_an_available_variant_and_its_exact_price(self):
        self.variant.stock_quantity = 0; self.variant.save()
        available = ProductVariant.objects.create(product=self.product, name='60ML', price_override='200', selling_price='180', stock_quantity=3)
        response = self.client.get(reverse('shop:product_detail', args=[self.product.slug]))
        self.assertEqual(response.context['selected_variant'], available)
        self.assertEqual(response.context['display_price'], Decimal('180'))
        self.assertContains(response, 'data-price="180.00"')

    def test_product_card_renders_real_prices_without_placeholder_rating(self):
        self.product.base_price = Decimal('2070'); self.product.selling_price = Decimal('1863'); self.product.save()
        response = self.client.get(reverse('shop:category_list'))
        self.assertContains(response, '₹1,863.00')
        self.assertContains(response, '₹2,070.00')
        self.assertContains(response, '10% OFF')
        self.assertNotContains(response, 'No rating yet')

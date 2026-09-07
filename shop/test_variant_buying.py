from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Category, Product, ProductVariant, ProductImage, CartItem, OrderItem
from .services.variants import variant_options, card_offer
from .management.commands.import_shopify_products import Command as Importer
from .test_checkout import CHECKOUT_DATA


class VariantBuyingTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Verified food', category=Category.objects.create(name='Dog'), base_price=1200, stock_quantity=0)
        self.small = self.pack('1.5 kg', '1.5', 'kg', '1050', 0)
        self.medium = self.pack('4 kg', '4', 'kg', '2500', 1)
        self.large = self.pack('5 kg', '5', 'kg', '2950', 2)

    def pack(self, name, quantity, unit, price, order, **extra):
        return ProductVariant.objects.create(product=self.product, name=name, quantity=Decimal(quantity), unit=unit,
            price_override=Decimal(price)+100, selling_price=Decimal(price), stock_quantity=20,
            display_order=order, comparison_group='same chicken recipe', sku=f'PACK-{order}', **extra)

    def options(self):
        return variant_options(self.product, self.product.variants.all())

    def test_exact_savings_and_best_value(self):
        options = self.options()
        self.assertEqual([o['unit_price'] for o in options], [Decimal(700), Decimal(625), Decimal(590)])
        self.assertEqual([o['value_saving'] for o in options], [0, 300, 550])
        self.assertEqual([o['best_value'] for o in options], [False, False, True])
        self.medium.selling_price = 2000; self.medium.save()
        self.assertTrue(self.options()[1]['best_value'])  # not the largest pack

    def test_units_groups_unverified_and_unavailable_are_not_miscompared(self):
        self.small.quantity = 1500; self.small.unit = 'g'; self.small.save()
        self.assertEqual(self.options()[0]['unit_price'], 700)
        self.large.unit = 'ml'; self.large.save()
        self.assertFalse(self.options()[2]['best_value'])
        self.medium.comparison_group = ''; self.medium.save()
        self.assertFalse(any(o['best_value'] for o in self.options()))
        self.large.unit = 'kg'; self.large.stock_quantity = 0; self.large.save()
        self.assertFalse(self.options()[2]['best_value'])
        self.small.quantity = None; self.small.unit = ''; self.small.save()
        self.assertIsNone(self.options()[0]['unit_price'])

    def test_volume_and_ties(self):
        self.small.quantity = 500; self.small.unit = 'ml'; self.small.selling_price = 500; self.small.save()
        self.medium.quantity = 1; self.medium.unit = 'L'; self.medium.selling_price = 1000; self.medium.save()
        self.assertEqual(self.options()[0]['unit_price'], 1000)
        self.assertFalse(self.options()[0]['best_value'])
        self.assertFalse(self.options()[1]['best_value'])

    def test_model_rejects_invalid_quantity_image_and_price(self):
        other = Product.objects.create(name='Other', category=self.product.category, base_price=1)
        photo = ProductImage.objects.create(product=other, source_url='https://example.com/photo.webp')
        for values in [{'quantity': 0}, {'quantity': None}, {'image': photo}, {'selling_price': 999999}, {'attributes': ['bad']}]:
            pack = ProductVariant.objects.get(pk=self.small.pk)
            for key, value in values.items(): setattr(pack, key, value)
            with self.assertRaises(ValidationError): pack.full_clean()

    def test_cart_separates_sizes_quantity_and_order_snapshot(self):
        add = reverse('shop:add_to_cart', args=[self.product.pk])
        self.client.post(add, {'variant_id': self.small.pk, 'quantity': 1, 'price': '0.01'})
        self.client.post(add, {'variant_id': self.large.pk, 'quantity': 2})
        self.assertEqual(CartItem.objects.count(), 2)
        large_line = CartItem.objects.get(product_variant=self.large)
        self.client.post(reverse('shop:update_cart_item', args=[large_line.pk]), {'quantity': 3})
        large_line.refresh_from_db(); self.assertEqual(large_line.quantity, 3)
        self.assertEqual(large_line.total_price, 8850)
        token = self.client.get(reverse('shop:checkout')).context['checkout_token']
        response = self.client.post(reverse('shop:checkout'), {**CHECKOUT_DATA, 'checkout_token': token})
        self.assertEqual(response.status_code, 302)
        purchased = OrderItem.objects.get(product_variant=self.large)
        self.large.name = 'Changed name'; self.large.selling_price = 100; self.large.save()
        purchased.refresh_from_db()
        self.assertEqual((purchased.variant_name, purchased.unit_price, purchased.sku), ('5 kg', Decimal(2950), 'PACK-2'))

    def test_invalid_foreign_disabled_and_missing_variants_cannot_be_added(self):
        add = reverse('shop:add_to_cart', args=[self.product.pk])
        self.client.post(add, {'quantity': 1})
        self.client.post(add, {'variant_id': 'garbage'})
        self.large.stock_quantity = 0; self.large.save()
        self.client.post(add, {'variant_id': self.large.pk})
        other = Product.objects.create(name='Other', category=self.product.category, base_price=1)
        self.assertEqual(self.client.post(reverse('shop:add_to_cart', args=[other.pk]), {'variant_id': self.small.pk}).status_code, 404)
        self.product.variants.update(is_active=False)
        self.product.stock_quantity=100; self.product.save()
        self.client.post(add, {})
        self.assertFalse(CartItem.objects.exists())
        self.assertFalse(self.product.is_in_stock)

    def test_cards_and_filter_use_same_available_variant_price(self):
        self.small.stock_quantity=0; self.small.save()
        self.assertEqual(card_offer(self.product)['price'], 2500)
        response = self.client.get(reverse('shop:category_list'), {'min_price':'2400', 'max_price':'2600'})
        self.assertContains(response, 'From ')
        self.assertContains(response, '₹2,500.00')
        self.assertContains(response, 'Choose size')

    def test_crm_create_edit_image_archive_restore_and_permissions(self):
        staff = get_user_model().objects.create_superuser('test-staff', 'staff@example.com', 'test-only-password')
        self.client.force_login(staff)
        self.product.refresh_from_db()
        data = {'version':self.product.updated_at.isoformat(), 'name':'10 kg', 'sku':'PACK-10',
                'price_override':'7000', 'selling_price':'5900', 'quantity':'10', 'unit':'kg', 'is_active':'on', 'display_order':'3'}
        self.assertEqual(self.client.post(reverse('crm:variant_create', args=[self.product.pk]), data).status_code, 302)
        created=ProductVariant.objects.get(name='10 kg'); self.assertEqual(created.stock_quantity,0)
        self.assertEqual(self.client.post(reverse('crm:variant_create', args=[self.product.pk]), data).status_code, 200)  # stale
        photo=ProductImage.objects.create(product=self.product,source_url='https://example.com/exact.webp')
        self.large.image=photo; self.large.save()
        self.product.refresh_from_db()
        url=reverse('crm:image_edit',args=[self.product.pk,photo.pk])
        self.assertEqual(self.client.post(url,{'version':self.product.updated_at.isoformat(),'order':1,'reason':'Wrong pack'}).status_code,302)
        self.assertFalse(ProductImage.objects.filter(pk=photo.pk).exists())
        self.large.refresh_from_db(); self.assertIsNone(self.large.image_id)
        self.product.refresh_from_db()
        self.assertEqual(self.client.post(url,{'version':self.product.updated_at.isoformat(),'order':1,'is_active':'on'}).status_code,302)
        self.assertTrue(ProductImage.objects.filter(pk=photo.pk).exists())
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code,302)

    def test_import_exact_variant_images_options_and_order_is_idempotent(self):
        rows=[{'Title':'Export item','Handle':'export-item','Published':'true','Variant Price':'200','Variant Compare At Price':'250',
               'Variant Inventory Tracker':'shopify','Variant Inventory Qty':'3','Option1 Name':'Size','Option1 Value':'500 g',
               'Variant SKU':'IMPORT-1','Image Src':'https://cdn.shopify.com/s/files/1/front.jpg?v=1','Image Position':'2',
               'Variant Image':'https://cdn.shopify.com/s/files/1/back.jpg'},
              {'Handle':'export-item','Variant Price':'300','Variant SKU':'IMPORT-2','Option1 Name':'Size','Option1 Value':'1 kg',
               'Image Src':'https://cdn.shopify.com/s/files/1/back.jpg','Image Position':'1'}]
        importer=Importer()
        importer._import_group('export-item', rows, {}, False)
        importer._import_group('export-item', rows, {}, False)
        product=Product.objects.get(slug='export-item')
        self.assertEqual(product.variants.count(),2); self.assertEqual(product.images.count(),2)
        pack=product.variants.get(sku='IMPORT-1')
        self.assertEqual(pack.image,product.images.first())
        self.assertEqual(pack.attributes,{'Size':'500 g'})
        self.assertIsNone(pack.quantity)  # not shipping weight or guessed formulation

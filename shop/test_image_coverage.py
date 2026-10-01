import json
from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from shop.models import Category, Product, ProductVariant, ProductImage
from shop.services.catalog_quality import fingerprint
from shop.services.product_cards import product_card


class ImageCoverageTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Dogs')
        self.product = Product.objects.create(name='Food', category=category, base_price=100, stock_quantity=10)
        self.variant = ProductVariant.objects.create(product=self.product, name='1KG', selling_price=100, stock_quantity=10)

    def test_dry_run_preserves_all_catalog_fields(self):
        before = fingerprint()
        with TemporaryDirectory() as folder:
            target = str(Path(folder)/'coverage.json')
            call_command('audit_image_coverage', dry_run=True, output=target, stdout=StringIO())
            report = json.loads(Path(target).read_text())
            self.assertEqual(report['summary']['recovered'], 0)
            self.assertEqual(report['summary']['products_without_images'], 1)
            self.assertEqual(len(report['rows'][0]), len(report['headers']))
        self.assertEqual(before, fingerprint())

    def test_placeholder_has_no_fabricated_image(self):
        self.assertEqual(product_card(self.product)['selected']['image'], '')
        response = self.client.get('/categories/')
        self.assertContains(response, 'Image coming soon')
        self.assertNotContains(response, 'src=""')

    def test_missing_pack_never_borrows_unrelated_image(self):
        other = Product.objects.create(name='Other food', category=self.product.category, base_price=200)
        photo = ProductImage.objects.create(product=other, source_url='https://example.test/other.jpg')
        self.variant.image = photo
        self.variant.save()
        self.assertEqual(product_card(self.product)['selected']['image'], '')

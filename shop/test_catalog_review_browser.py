import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .models import Category, Product, ProductVariant, ProductImage, CatalogReviewEvent


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set browser runtime for review UI verification.')
class CatalogReviewBrowserTests(StaticLiveServerTestCase):
    def test_review_workflow_and_mobile_layout(self):
        get_user_model().objects.create_superuser('review-fixture', 'fixture@example.com', 'Review-fixture-482!')
        product = Product.objects.create(name='Verified food review fixture', category=Category.objects.create(name='Dog'),
            sku='REVIEW', base_price=100, selling_price=90, stock_quantity=10)
        photo = ProductImage.objects.create(product=product, source_url='https://example.com/review-fixture.jpg')
        ProductVariant.objects.create(product=product, name='3 KG', sku='REVIEW-3KG', stock_quantity=10, image=photo)
        result = subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('catalog_review_browser_test.cjs')),
            self.live_server_url, str(product.pk)], capture_output=True, text=True, timeout=150)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(CatalogReviewEvent.objects.count(), 2)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 10)
        self.assertEqual(product.catalog_approved_digest, '')
        self.assertTrue(product.is_active)

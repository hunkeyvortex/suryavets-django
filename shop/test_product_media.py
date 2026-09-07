import csv
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from shop.models import Category, Product, ProductImage
from shop.services.product_media import allowed_image_url, download_image, nutrition_sections, SafeRedirect


class ProductMediaTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Food fixture', category=Category.objects.create(name='Dog'), base_price=100, selling_price=90, stock_quantity=14)

    def test_explicit_nutrition_sections_do_not_invent_values(self):
        sections = nutrition_sections('<p>Ingredients:</p><p>Chicken, rice.</p><p>Guaranteed Analysis:<br>Crude protein: 22%</p><p>Feeding:</p><p>Ask your vet.</p>')
        self.assertIn('Chicken, rice.', sections['ingredients'])
        self.assertIn('Crude protein: 22%', sections['nutrition_information'])
        self.assertNotIn('Ask your vet', sections['nutrition_information'])
        self.assertEqual(nutrition_sections('<p>A healthy daily food.</p>'), {'ingredients':'', 'nutrition_information':''})

    def test_nutrition_draft_is_hidden_until_reviewed(self):
        self.product.nutrition_information = 'Crude protein: 22%'
        self.product.nutrition_source = 'https://example.com/exact-label'
        self.product.save()
        url = reverse('shop:product_detail', args=[self.product.slug])
        self.assertNotContains(self.client.get(url), 'Crude protein: 22%')
        self.product.nutrition_reviewed = True; self.product.save()
        self.assertContains(self.client.get(url), 'Crude protein: 22%')

    def test_sources_add_only_missing_information_and_never_stock_or_prices(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp)/'export.csv'; report=Path(tmp)/'report.csv'
            with source.open('w', newline='', encoding='utf-8') as out:
                writer=csv.DictWriter(out, fieldnames=['Handle','Title','Variant Price','Body (HTML)','Image Src','Image Position'])
                writer.writeheader(); writer.writerow({'Handle':self.product.slug,'Title':self.product.name,'Variant Price':'1',
                    'Body (HTML)':'<p>Ingredients:</p><p>Chicken.</p>', 'Image Src':'https://cdn.shopify.com/s/files/test/photo.png', 'Image Position':'1'})
            call_command('audit_product_media', sources=[str(source)], report=str(report))
            self.assertFalse(self.product.images.exists())
            call_command('audit_product_media', sources=[str(source)], report=str(report), apply=True)
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock_quantity, 14); self.assertEqual(self.product.current_price, 90)
            self.assertFalse(self.product.nutrition_reviewed)
            self.assertIn('Chicken.', self.product.ingredients)
            self.product.ingredients='Staff correction'; self.product.save()
            call_command('audit_product_media', sources=[str(source)], report=str(report), apply=True)
            self.product.refresh_from_db(); self.assertEqual(self.product.ingredients, 'Staff correction')
            self.assertEqual(self.product.images.count(),1)
            with report.open(encoding='utf-8-sig') as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row['Broken Image'], 'UNCHECKED')
            self.assertEqual(row['Image Count'], '1')

    def test_empty_and_failed_checks_are_not_claimed_verified(self):
        with TemporaryDirectory() as tmp:
            report=Path(tmp)/'report.csv'
            call_command('audit_product_media', report=str(report))
            with report.open(encoding='utf-8-sig') as stream: row=next(csv.DictReader(stream))
            self.assertEqual(row['Action Required'], 'IMAGE REQUIRED')
            ProductImage.objects.create(product=self.product, source_url='https://cdn.shopify.com/s/files/test/photo.png', check_error='URLError: TLS failed')
            call_command('audit_product_media', report=str(report))
            with report.open(encoding='utf-8-sig') as stream: row=next(csv.DictReader(stream))
            self.assertEqual(row['Broken Image'], 'CHECK FAILED')

    def test_downloader_restricts_hosts_and_optimizes_verified_image_bytes(self):
        for url in ['http://cdn.shopify.com/s/files/a.png','https://localhost/a.png','https://cdn.shopify.com.evil.test/s/files/a.png']:
            self.assertFalse(allowed_image_url(url))
            with self.assertRaises(ValueError): download_image(url)
        with self.assertRaises(ValueError):
            SafeRedirect().redirect_request(None,None,302,'',{},'http://127.0.0.1/private')
        raw=io.BytesIO(); Image.new('RGB',(2000,1000),'white').save(raw,'PNG')
        with patch('shop.services.product_media.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.return_value=raw.getvalue()
            full,thumb=download_image('https://cdn.shopify.com/s/files/test/photo.png')
        self.assertEqual(Image.open(io.BytesIO(full)).size,(1400,700))
        self.assertEqual(Image.open(io.BytesIO(thumb)).size,(360,180))

    def test_download_is_repeatable_and_preserves_original_reference(self):
        url='https://cdn.shopify.com/s/files/test/photo.png'
        record=ProductImage.objects.create(product=self.product,source_url=url)
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            report=Path(tmp)/'report.csv'
            with patch('shop.management.commands.audit_product_media.download_image', return_value=(b'full', b'thumb')) as download:
                call_command('audit_product_media', report=str(report), apply=True, download=True)
                call_command('audit_product_media', report=str(report), apply=True, download=True)
                self.assertEqual(download.call_count,1)
            record.refresh_from_db(); self.assertEqual(record.source_url,url)
            self.assertTrue(record.image.storage.exists(record.image.name))
            self.assertIn('thumbnails',record.thumbnail_url)

    def test_crm_filters_distinguish_missing_and_nutrition_drafts(self):
        from django.contrib.auth import get_user_model
        user=get_user_model().objects.create_superuser('media-manager','fixture@example.com','Fixture-pass-198!')
        self.client.force_login(user)
        other=Product.objects.create(name='With a photo',category=self.product.category,base_price=1)
        ProductImage.objects.create(product=other,source_url='https://cdn.shopify.com/s/files/test/photo.png')
        response=self.client.get(reverse('crm:inventory'),{'media':'missing'})
        self.assertContains(response,'Food fixture'); self.assertNotContains(response,'With a photo')
        self.product.ingredients='Draft text'; self.product.save()
        response=self.client.get(reverse('crm:inventory'),{'media':'nutrition'})
        self.assertContains(response,'Food fixture'); self.assertNotContains(response,'With a photo')

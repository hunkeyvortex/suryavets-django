import csv
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from shop.models import Product, ProductVariant, ProductImage, Category
from shop.services.image_recovery import build_index
from shop.services.pack_images import pack_photos, family_photo
from shop.services.product_cards import product_card
from shop.services.catalog_quality import fingerprint


class TrustedImageRecoveryTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.temp.name); self.media.enable(); self.addCleanup(self.media.disable)
        self.category = Category.objects.create(name='Dog')
        self.product = Product.objects.create(name='Exact food', slug='exact-food', category=self.category, base_price=100, stock_quantity=8)
        self.variant = ProductVariant.objects.create(product=self.product, name='1KG', sku='EXACT-1', selling_price=90, stock_quantity=7)
        image = Image.new('RGB', (32, 32), 'white'); buffer = io.BytesIO(); image.save(buffer, format='PNG'); self.picture = buffer.getvalue()
        self.source = Path(self.temp.name)/'source.csv'
        self.folder = Path(self.temp.name)/'report'
        with self.source.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['Handle','Title','Vendor','Variant SKU','Option1 Value','Image Src','Variant Image'])
            writer.writeheader(); writer.writerow({'Handle':self.product.slug, 'Title':self.product.name, 'Variant SKU':self.variant.sku,
                'Option1 Value':'1KG', 'Variant Image':'https://cdn.shopify.com/s/files/1/0001/files/exact.png'})

    def run_command(self, apply=False):
        call_command('recover_product_images', sources=[str(self.source)], output_dir=str(self.folder),
            apply=apply, validated_plan=str(self.folder/'image_recovery_index.json') if apply else None, stdout=io.StringIO())

    def photo(self, product=None):
        return ProductImage.objects.create(product=product or self.product, image=ContentFile(self.picture, name='pack.png'))

    def test_high_exact_recovery_logged_and_business_fields_preserved(self):
        original = list(ProductVariant.objects.values())
        before = fingerprint(); self.run_command(); self.assertEqual(fingerprint(), before)
        with patch('shop.management.commands.recover_product_images.download_image', return_value=(self.picture,self.picture)):
            self.run_command(True)
        self.variant.refresh_from_db(); self.assertIsNotNone(self.variant.image_id)
        after = list(ProductVariant.objects.values()); after[0]['image_id'] = original[0]['image_id']
        self.assertEqual(original, after)
        self.assertTrue(list(self.folder.glob('image-recovery-backup-*.json')))
        self.assertIn('HIGH exact recovery', (self.folder/'image_recovery_applied.csv').read_text(encoding='utf-8-sig'))
        self.run_command()
        self.run_command(True)
        self.assertIn('HIGH exact recovery', (self.folder/'image_recovery_applied.csv').read_text(encoding='utf-8-sig'))

    def test_low_confidence_never_applied(self):
        self.variant.sku = 'DIFFERENT'; self.variant.save()
        self.run_command(); before = fingerprint()
        with patch('shop.management.commands.recover_product_images.download_image') as download:
            self.run_command(True); download.assert_not_called()
        self.assertEqual(fingerprint(), before)

    def test_existing_verified_image_not_overwritten(self):
        photo = self.photo(); self.variant.image = photo; self.variant.save()
        self.run_command()
        with patch('shop.management.commands.recover_product_images.download_image') as download:
            self.run_command(True); download.assert_not_called()
        self.variant.refresh_from_db(); self.assertEqual(self.variant.image_id, photo.pk)

    def test_stale_plan_rejected(self):
        self.run_command(); self.variant.name='2KG'; self.variant.save()
        with self.assertRaises(CommandError): self.run_command(True)

    def test_family_fallback_never_becomes_exact_pack(self):
        sibling=Product.objects.create(name='Exact food large', category=self.category, base_price=500, variant_family=self.product)
        reference=self.photo(sibling); reference.family_reference_for=self.product; reference.family_reference_note='Reviewed generic artwork'; reference.save()
        self.assertEqual(family_photo(self.product),reference)
        self.assertEqual(pack_photos(self.variant),[])
        card=product_card(self.product); self.assertTrue(card['selected']['family_reference'])
        exact=self.photo(); self.variant.image=exact; self.variant.save()
        self.assertEqual(pack_photos(self.variant)[0],exact)
        self.assertFalse(product_card(self.product)['selected']['family_reference'])

    def test_unrelated_family_does_not_leak(self):
        other=Product.objects.create(name='Unrelated', category=self.category, base_price=500)
        photo=self.photo(other); photo.family_reference_for=other; photo.family_reference_note='Reviewed'; photo.save()
        self.assertIsNone(family_photo(self.product))
        self.assertEqual(product_card(self.product)['selected']['image'],'')

    def test_invalid_file_recorded_then_resolver_uses_placeholder(self):
        photo=ProductImage.objects.create(product=self.product,image='products/missing.png')
        self.variant.image=photo;self.variant.save()
        self.run_command();self.run_command(True)
        photo.refresh_from_db();self.assertTrue(photo.check_error);self.assertEqual(photo.display_url,'')
        self.assertEqual(pack_photos(self.variant),[])

    def test_card_performs_no_storage_probes(self):
        photo=self.photo(); self.variant.image=photo; self.variant.save()
        with patch.object(photo.image.storage,'exists',side_effect=AssertionError('Request-time file scan')):
            self.assertTrue(product_card(self.product)['selected']['image'])

    def test_invalid_pack_mapping_is_not_replaced_by_source(self):
        other=Product.objects.create(name='Other', category=self.category, base_price=1)
        self.variant.image=self.photo(other);self.variant.save()
        self.run_command()
        report=json.loads((self.folder/'image_recovery_index.json').read_text())
        self.assertEqual(report['plans'],[])

    def test_prefetched_cards_add_no_queries(self):
        from shop.catalog_views import _product_queryset
        for index in range(8):
            product=Product.objects.create(name=f'Extra {index}',category=self.category,base_price=10,stock_quantity=5)
            ProductVariant.objects.create(product=product,name='1KG',selling_price=10,stock_quantity=5)
        products=list(_product_queryset())
        with self.assertNumQueries(0):
            for product in products: product_card(product)

    def test_family_approval_requires_matching_family_and_evidence(self):
        from shop.crm_catalog_forms import ImageEditorForm
        photo=self.photo()
        data={'version':self.product.updated_at.isoformat(),'alt_text':'','order':0,'is_active':True,
              'family_reference_for':str(self.product.pk),'family_reference_note':'','reason':''}
        form=ImageEditorForm(data,instance=photo);self.assertFalse(form.is_valid())
        data.update(family_reference_note='Reviewed generic formulation artwork',reason='Safe generic reference')
        self.assertTrue(ImageEditorForm(data,instance=photo).is_valid())

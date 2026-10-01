import csv
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from shop.models import Category, Product, ProductVariant, ProductImage, CartItem
from shop.services.catalog_quality import fingerprint, select_only
from shop.services.pack_identity import build_identity_report, measurements
from shop.services.pack_families import candidates
from shop.services.variants import variant_options
from shop.services.product_cards import product_card


class PackIdentityTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Dog')
        self.root = Product.objects.create(name='Verified food', slug='verified-food-1kg', category=self.category, base_price=200, stock_quantity=10)
        self.member = Product.objects.create(name='Verified food', slug='verified-food-5kg', category=self.category, base_price=600, variant_family=self.root, stock_quantity=7)
        self.small = ProductVariant.objects.create(product=self.root, name='1KG', sku='ONE', selling_price=180, stock_quantity=10, quantity=1, unit='kg', comparison_group='same food')
        self.large = ProductVariant.objects.create(product=self.member, name='5KG', sku='FIVE', selling_price=540, stock_quantity=7, quantity=5, unit='kg', comparison_group='same food')
        self.photo = ProductImage.objects.create(product=self.member, source_url='https://example.test/food-5kg.jpg', alt_text='5 KG exact pack')
        self.large.image = self.photo
        self.large.save()
        self.url = reverse('shop:product_detail', args=[self.root.slug])

    def report(self, paths=()):
        with connection.execute_wrapper(select_only):
            return build_identity_report(paths)

    def test_similar_names_never_authorize_merge(self):
        other = Product.objects.create(name='Verified food salmon', slug='salmon-1kg', category=self.category, base_price=200)
        ProductVariant.objects.create(product=other, name='1KG', selling_price=180, stock_quantity=10)
        self.assertFalse(list(candidates([self.root, other])))
        before = fingerprint()
        self.report()
        self.assertEqual(before, fingerprint())
        other.refresh_from_db()
        self.assertIsNone(other.variant_family_id)

    def test_verified_siblings_remain_one_card_and_preserve_exact_choice(self):
        response = self.client.get(reverse('shop:category_list'))
        self.assertEqual(list(response.context['products']), [self.root])
        response = self.client.get(self.url, {'variant': self.large.pk})
        self.assertEqual(response.context['selected_variant'].pk, self.large.pk)
        self.assertEqual(response.context['display_price'], 540)
        self.assertEqual(response.context['selected_option']['saving'], 60)
        self.assertEqual(response.context['gallery_primary'], self.photo)
        self.assertEqual(response.context['selected_variant'].stock_quantity, 7)
        self.client.post(reverse('shop:add_to_cart', args=[self.root.pk]), {'variant_id': self.large.pk, 'quantity': 1})
        item = CartItem.objects.get()
        self.assertEqual(item.product_variant_id, self.large.pk)
        self.assertEqual(item.product_id, self.member.pk)

    def test_invalid_query_does_not_choose_another_pack(self):
        for query in ({'variant': 'invalid'}, {'variant': 999999}, {'variant': [self.small.pk, self.large.pk]}, {'variant': ''}):
            response = self.client.get(self.url, query)
            self.assertIsNone(response.context['selected_variant'])
            self.assertFalse(response.context['buying_in_stock'])
            self.assertContains(response, 'No size has been substituted')

    def test_unavailable_explicit_pack_stays_selected_not_substituted(self):
        ProductVariant.objects.filter(pk=self.large.pk).update(selling_price=0)
        response = self.client.get(self.url, {'variant': self.large.pk})
        self.assertEqual(response.context['selected_variant'].pk, self.large.pk)
        self.assertFalse(response.context['buying_in_stock'])
        response = self.client.get(reverse('shop:product_detail', args=[self.member.slug]))
        self.assertEqual(response.context['selected_variant'].pk, self.large.pk)
        self.assertFalse(response.context['buying_in_stock'])

    def test_inactive_member_pack_does_not_fall_back_to_root(self):
        ProductVariant.objects.filter(pk=self.large.pk).update(is_active=False)
        response = self.client.get(reverse('shop:product_detail', args=[self.member.slug]))
        self.assertIsNone(response.context['selected_variant'])
        self.assertFalse(response.context['buying_in_stock'])

    def test_foreign_pack_image_never_leaks_to_card_or_detail(self):
        ProductVariant.objects.filter(pk=self.small.pk).update(image=self.photo)
        options = variant_options(self.root, [ProductVariant.objects.get(pk=self.small.pk)])
        self.assertTrue(options[0]['image_missing'])
        self.assertEqual(options[0]['image_url'], '')
        self.assertEqual(product_card(self.root)['selected']['image'], '')
        from shop.models import Cart
        item = CartItem(cart=Cart(), product=self.root, product_variant=ProductVariant.objects.get(pk=self.small.pk))
        self.assertIsNone(item.display_image)
        rows, _, _ = self.report()
        row = next(r for r in rows if r['Variant ID'] == self.small.pk)
        self.assertIn('WRONG_IMAGE_OWNERSHIP', row['Conflict Type'])
        self.assertEqual(row['Priority'], 'P0')

    def test_unassigned_multipack_image_does_not_fall_back(self):
        ProductImage.objects.create(product=self.root, source_url='https://example.test/one-kg.jpg')
        extra = ProductVariant.objects.create(product=self.root, name='2KG', selling_price=300, stock_quantity=10)
        self.assertTrue(all(o['image_missing'] for o in variant_options(self.root, [self.small, extra])))

    def test_mixed_units_not_comparable_and_reported(self):
        self.large.name = '5L'; self.large.unit = 'L'; self.large.save()
        self.assertFalse(any(o['best_value'] for o in variant_options(self.root, [self.small, self.large])))
        rows, _, _ = self.report()
        self.assertTrue(all('FAMILY_INCOMPATIBLE_UNITS' in r['Conflict Type'] for r in rows))

    def test_wrong_formulation_group_is_flagged_not_changed(self):
        self.member.name = 'Verified renal diet'; self.member.save()
        before = fingerprint()
        rows, counts, _ = self.report()
        self.assertEqual(counts['wrong_grouping_families'], 1)
        self.assertIn('WRONG_GROUPING_CANDIDATE', rows[0]['Conflict Type'])
        self.assertEqual(before, fingerprint())

    def test_disjoint_species_in_existing_family_requires_review(self):
        from shop.models import PetCategory
        self.root.pet_categories.add(PetCategory.objects.create(name='Dog'))
        self.member.pet_categories.add(PetCategory.objects.create(name='Cat'))
        _, counts, _ = self.report()
        self.assertEqual(counts['wrong_grouping_families'], 1)

    def test_visual_observation_requires_matching_file_hash(self):
        import hashlib
        with TemporaryDirectory() as folder, self.settings(MEDIA_ROOT=folder):
            photo_path = Path(folder) / 'fixture.bin'
            photo_path.write_bytes(b'isolated test image identity')
            photo = ProductImage.objects.create(product=self.root, image='fixture.bin', source_url='https://example.test/wrong-2kg.jpg')
            self.small.image = photo; self.small.save()
            evidence = Path(folder) / 'observations.json'
            observation = {'image_id': photo.pk, 'sha256': hashlib.sha256(photo_path.read_bytes()).hexdigest(), 'visible_pack': '1kg', 'observed_text': 'Fixture label 1 kg', 'reviewed_at': 'test'}
            evidence.write_text(json.dumps({'observations': [observation]}))
            rows, _, _ = build_identity_report(image_observations=evidence)
            row = next(r for r in rows if r['Variant ID'] == self.small.pk)
            self.assertNotIn('IMAGE_PACK_MISMATCH_CANDIDATE', row['Conflict Type'])
            self.assertIn('Visible pack amount matches', row['Image Review'])
            photo_path.write_bytes(b'changed fixture')
            rows, _, _ = build_identity_report(image_observations=evidence)
            row = next(r for r in rows if r['Variant ID'] == self.small.pk)
            self.assertIn('IMAGE_PACK_MISMATCH_CANDIDATE', row['Conflict Type'])
            self.assertIn('stale', row['Visual Image Observation'])

    def test_title_slug_and_sku_conflicts_are_reported_without_fix(self):
        self.root.name = 'Food 80GM'; self.root.slug = 'food-1-2kg'; self.root.save()
        self.small.name = '70GM'; self.small.sku = 'SAME'; self.small.save()
        self.large.sku = 'SAME'; self.large.save()
        before = fingerprint()
        rows, _, _ = self.report()
        row = next(r for r in rows if r['Variant ID'] == self.small.pk)
        for code in ('TITLE_VARIANT_MISMATCH', 'SLUG_VARIANT_MISMATCH', 'SKU_CONFLICTING_PACKS'):
            self.assertIn(code, row['Conflict Type'])
        self.assertEqual(before, fingerprint())

    def test_dosage_not_misrepresented_as_pack_size(self):
        self.assertEqual(measurements('200MG/5ML'), set())
        self.assertEqual(measurements('medicine-200mg-5ml.jpg'), set())

    def test_different_unknown_labels_are_not_confirmed_sku_size_conflicts(self):
        self.small.name = '5BOL'; self.small.sku = 'SAME'; self.small.save()
        self.large.name = '5BOLUS'; self.large.sku = 'SAME'; self.large.save()
        rows, _, _ = self.report()
        self.assertTrue(all('SKU_LABEL_REVIEW' in r['Conflict Type'] for r in rows))
        self.assertFalse(any('SKU_CONFLICTING_PACKS' in r['Conflict Type'] for r in rows))

    def test_source_provenance_handle_conflict_and_report_integrity(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / 'source.csv'
            with source.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=['Handle', 'Title', 'Vendor', 'Variant SKU', 'Option1 Value', 'Variant Price'])
                writer.writeheader()
                for title in ('Verified food', 'Different diet'):
                    writer.writerow({'Handle': self.root.slug, 'Title': title, 'Vendor': 'Brand', 'Variant SKU': 'ONE', 'Option1 Value': '1KG', 'Variant Price': 180})
            before = fingerprint()
            call_command('audit_pack_identity', sources=[str(source)], output_dir=folder, stdout=io.StringIO())
            manifest = json.loads((Path(folder) / 'pack_identity_manifest.json').read_text())
            self.assertTrue(manifest['business_data_unchanged'])
            self.assertEqual(manifest['before'], manifest['after'])
            self.assertEqual(before, fingerprint())
            with (Path(folder) / 'variant_pack_review.csv').open(encoding='utf-8-sig') as stream:
                rows = list(csv.DictReader(stream))
            row = next(r for r in rows if r['Variant ID'] == str(self.small.pk))
            self.assertIn('HANDLE_MULTIPLE_IDENTITIES', row['Conflict Type'])
            self.assertIn('source.csv: CSV record 2', row['Evidence Source'])
            call_command('audit_pack_identity', sources=[str(source)], output_dir=folder, archive_existing=True, stdout=io.StringIO())
            self.assertTrue(list(Path(folder).glob('identity-history-*/variant_pack_review.csv')))

    def test_crm_snapshot_filter_keeps_permissions(self):
        from django.contrib.auth import get_user_model
        row = {'Product ID': str(self.root.pk), 'Priority': 'P0', 'Conflict Type': 'TEST', 'SKU': 'ONE'}
        evidence = {'generated_at': 'test snapshot', 'by_product': {str(self.root.pk): [row]}}
        url = reverse('crm:inventory')
        self.assertNotEqual(self.client.get(url, {'identity': 'P0'}).status_code, 200)
        staff = get_user_model().objects.create_superuser('identity-reviewer', 'review@example.test', 'test-password')
        self.client.force_login(staff)
        with patch('shop.services.pack_review_snapshot.snapshot', return_value=evidence):
            response = self.client.get(url, {'identity': 'P0'})
        self.assertEqual(list(response.context['page']), [self.root])
        self.assertContains(response, 'test snapshot')

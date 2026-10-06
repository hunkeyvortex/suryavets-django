import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from shop.models import Category, Product, ProductImage
from shop.management.commands import migrate_media_to_cloudinary as command


@override_settings(STORAGES={'default': {'BACKEND': command.BACKEND}})
class CloudinaryMigrationTests(TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / 'categories').mkdir()
        (self.root / 'categories/cat.png').write_bytes(b'owned-test-image')
        self.category = Category.objects.create(name='Cat', image='categories/cat.png')
        self.assets = set()
        self.storage = Mock()
        self.storage._prepend_prefix.side_effect = lambda name: name if name.startswith('media/') else 'media/' + name
        self.storage.exists.side_effect = lambda name: name in self.assets
        self.uploader = Mock()
        def save(name, content):
            self.assertEqual(content.read(), b'owned-test-image')
            self.assets.add(name)
            return name
        self.uploader.save.side_effect = save
        self.stack = patch.object(command, 'storages', {'default': self.storage})
        self.stack.start()
        self.addCleanup(self.stack.stop)
        self.factory = patch.object(command, 'migration_storage', return_value=self.uploader)
        self.factory.start()
        self.addCleanup(self.factory.stop)

    def run_command(self, dry=False):
        output = StringIO()
        call_command('migrate_media_to_cloudinary', dry_run=dry, media_root=str(self.root), stdout=output)
        return json.loads(output.getvalue().splitlines()[-1])

    def test_dry_run_does_not_upload_or_update(self):
        result = self.run_command(True)
        self.assertEqual(result['would_upload'], 1)
        self.uploader.save.assert_not_called()
        self.category.refresh_from_db()
        self.assertEqual(self.category.image.name, 'categories/cat.png')

    def test_apply_and_rerun_are_idempotent_and_preserve_shared_paths(self):
        other = Category.objects.create(name='Another category', image=self.category.image.name)
        result = self.run_command()
        self.assertEqual(result['uploaded'], 1)
        self.assertEqual(result['updated_references'], 2)
        self.category.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(other.image.name, self.category.image.name)
        result = self.run_command()
        self.assertEqual(result['already_cloud_hosted'], 2)
        self.assertEqual(self.uploader.save.call_count, 1)

    def test_retry_reuses_asset_uploaded_before_database_update(self):
        target = 'media/' + command.target_name(self.category.image.name, self.root / self.category.image.name)
        self.assets.add(target)
        self.assertEqual(self.run_command()['uploaded'], 0)
        self.category.refresh_from_db()
        self.assertEqual(self.category.image.name, target)

    def test_inactive_image_and_thumbnail_are_migrated_without_reactivating(self):
        product = Product.objects.create(name='Archived artwork product', category=self.category, base_price=123)
        photo = ProductImage.all_objects.create(
            product=product, image='categories/cat.png', thumbnail='categories/cat.png', is_active=False,
        )
        self.assertFalse(ProductImage.objects.filter(pk=photo.pk).exists())

        dry = self.run_command(True)
        self.assertEqual(dry['total_references'], 3)
        self.assertEqual(dry['would_upload'], 1)
        self.uploader.save.assert_not_called()
        photo.refresh_from_db()
        self.assertEqual(photo.image.name, 'categories/cat.png')
        self.assertEqual(photo.thumbnail.name, 'categories/cat.png')

        applied = self.run_command()
        self.assertEqual(applied['updated_references'], 3)
        self.assertEqual(applied['uploaded'], 1)
        photo.refresh_from_db()
        self.category.refresh_from_db()
        self.assertEqual(photo.image.name, self.category.image.name)
        self.assertEqual(photo.thumbnail.name, self.category.image.name)
        self.assertFalse(photo.is_active)
        product.refresh_from_db()
        self.assertEqual(product.base_price, 123)
        self.assertEqual(self.run_command()['already_cloud_hosted'], 3)
        self.assertEqual(self.uploader.save.call_count, 1)

    def test_missing_file_unchanged(self):
        self.category.image = 'missing.png'; self.category.save()
        self.assertEqual(self.run_command()['missing_local'], 1)
        self.category.refresh_from_db()
        self.assertEqual(self.category.image.name, 'missing.png')

    def test_existing_remote_reference_unchanged(self):
        self.assets.add('categories/cat.png')
        self.assertEqual(self.run_command()['already_cloud_hosted'], 1)
        self.uploader.save.assert_not_called()

    def test_traversal_rejected(self):
        self.category.image = '../private.png'; self.category.save()
        with self.assertRaises(CommandError): self.run_command()
        self.uploader.save.assert_not_called()

    def test_failure_does_not_reassign_field(self):
        self.uploader.save.side_effect = RuntimeError('provider error')
        with self.assertRaises(CommandError): self.run_command()
        self.category.refresh_from_db()
        self.assertEqual(self.category.image.name, 'categories/cat.png')

    def test_external_source_url_is_not_a_local_reference(self):
        product = Product.objects.create(name='Existing product', category=self.category, base_price=123)
        photo = ProductImage.objects.create(product=product, source_url='https://example.invalid/owned.jpg')
        self.assertEqual(self.run_command(True)['total_references'], 1)
        photo.refresh_from_db(); product.refresh_from_db()
        self.assertEqual(photo.source_url, 'https://example.invalid/owned.jpg')
        self.assertEqual(product.base_price, 123)

    def test_thumbnail_destination_fits_existing_field_without_migration(self):
        target = 'media/' + command.target_name('products/thumbnails/example.webp', self.root / 'categories/cat.png')
        self.assertLessEqual(len(target), ProductImage._meta.get_field('thumbnail').max_length)

    @patch.dict('os.environ', {'CLOUDINARY_CLOUD_NAME': 'dummy', 'CLOUDINARY_API_KEY': 'dummy', 'CLOUDINARY_API_SECRET': 'dummy'})
    @override_settings(CLOUDINARY_STORAGE={
        'CLOUD_NAME': 'dummy', 'API_KEY': 'dummy', 'API_SECRET': 'dummy', 'SECURE': True,
    })
    def test_upload_adapter_uses_deterministic_nonoverwriting_public_id(self):
        self.factory.stop()
        from django.core.files.base import ContentFile
        name = 'surya-migrated/categories/exact-hash'
        with patch('cloudinary.uploader.upload', side_effect=lambda content, **kw: {'public_id': kw['public_id']}) as upload:
            saved = command.migration_storage().save(name, ContentFile(b'owned-image'))
        self.assertEqual(saved, 'media/' + name)
        self.assertEqual(upload.call_args.kwargs['public_id'], 'media/' + name)
        self.assertFalse(upload.call_args.kwargs['overwrite'])
        self.assertFalse(upload.call_args.kwargs['unique_filename'])

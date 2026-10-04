"""Isolated storage configuration checks: no real credentials, uploads or database writes."""
import os
from importlib.util import find_spec
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLOUDINARY = 'cloudinary_storage.storage.MediaCloudinaryStorage'


class MediaSettingsTests(unittest.TestCase):
    def run_settings(self, overrides=None, assertions='', succeeds=True):
        # Do not inherit production credentials or connection settings.
        env = {key: os.environ[key] for key in (
            'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'USERPROFILE',
        ) if key in os.environ}
        env.update({
            'DJANGO_SETTINGS_MODULE': 'suryavets.settings',
            'PYTHONDONTWRITEBYTECODE': '1',
            'DEBUG': 'False',
            'DJANGO_SECRET_KEY': 'dummy-test-key-not-a-real-secret-' * 3,
            'DJANGO_ALLOWED_HOSTS': 'example.invalid',
            'DATABASE_URL': 'postgresql://dummy:dummy@127.0.0.1:1/dummy',
            'PUBLIC_SITE_URL': 'https://example.invalid',
            'MEDIA_STORAGE_BACKEND': CLOUDINARY,
            'CLOUDINARY_CLOUD_NAME': 'dummy-cloud',
            'CLOUDINARY_API_KEY': 'dummy-key',
            'CLOUDINARY_API_SECRET': 'dummy-secret',
        })
        env.update(overrides or {})
        script = (
            'import socket\n'
            'def no_network(*args, **kwargs):\n'
            '    raise AssertionError("Network access is forbidden in storage tests")\n'
            'socket.socket.connect = no_network\n'
            'import django\ndjango.setup()\n'
            'from django.conf import settings\n'
            'from django.core.files.storage import storages\n'
            + assertions
        )
        result = subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                                env=env, capture_output=True, text=True, timeout=60)
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    @unittest.skipUnless(find_spec('cloudinary_storage') and find_spec('cloudinary'),
                         'Install requirements-media.txt for the Cloudinary integration check')
    def test_cloudinary_initializes_without_network_and_static_is_unchanged(self):
        self.run_settings(assertions='''
from django.core.management import get_commands, call_command
from django.db.models import ImageField, FileField
assert storages['default'].__class__.__name__ == 'MediaCloudinaryStorage'
assert storages['staticfiles'].__class__.__name__ == 'CompressedStaticFilesStorage'
assert get_commands()['collectstatic'] == 'django.contrib.staticfiles'
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
assert 'whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE
for field in (ImageField(), FileField()):
    url = field.storage.url('products/example.jpg')
    assert url.startswith('https://res.cloudinary.com/dummy-cloud/')
call_command('check', verbosity=0)
# Real static collection to an automatically removed test directory, never media.
import tempfile
from django.test import override_settings
with tempfile.TemporaryDirectory(prefix='surya-static-test-') as directory:
    with override_settings(STATIC_ROOT=directory):
        call_command('collectstatic', interactive=False, verbosity=0)
        from pathlib import Path
        assert (Path(directory) / 'admin/css/base.css').exists()
''')

    def test_missing_cloudinary_credentials_fail_without_echoing_values(self):
        for variable in ('CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET'):
            with self.subTest(variable=variable):
                result = self.run_settings({variable: ''}, succeeds=False)
                self.assertIn('Cloudinary media requires', result.stderr)
                self.assertNotIn('dummy-secret', result.stderr)

    def test_production_filesystem_without_persistent_root_is_rejected(self):
        result = self.run_settings({
            'MEDIA_STORAGE_BACKEND': 'django.core.files.storage.FileSystemStorage',
        }, succeeds=False)
        self.assertIn('Configure persistent/external media before production.', result.stderr)

    def test_explicit_persistent_filesystem_remains_supported(self):
        self.run_settings({
            'MEDIA_STORAGE_BACKEND': 'django.core.files.storage.FileSystemStorage',
            'PERSISTENT_MEDIA_ROOT': str(ROOT / 'media'),
        }, assertions="assert storages['default'].__class__.__name__ == 'FileSystemStorage'")

    def test_local_default_does_not_register_optional_apps(self):
        self.run_settings({
            'DEBUG': 'True', 'DATABASE_URL': '',
            'MEDIA_STORAGE_BACKEND': 'django.core.files.storage.FileSystemStorage',
        }, assertions="""
assert 'cloudinary_storage' not in settings.INSTALLED_APPS
assert 'cloudinary' not in settings.INSTALLED_APPS
assert storages['default'].__class__.__name__ == 'FileSystemStorage'
""")

    def test_s3_configuration_remains_supported(self):
        self.run_settings({
            'MEDIA_STORAGE_BACKEND': 'storages.backends.s3.S3Storage',
            'AWS_STORAGE_BUCKET_NAME': 'dummy-bucket',
        }, assertions="""
assert settings.STORAGES['default']['OPTIONS']['bucket_name'] == 'dummy-bucket'
assert settings.STORAGES['default']['OPTIONS']['file_overwrite'] is False
assert 'cloudinary_storage' not in settings.INSTALLED_APPS
""")

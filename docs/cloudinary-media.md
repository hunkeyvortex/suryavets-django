# Cloudinary media on Render

Only uploaded media uses Cloudinary. WhiteNoise, static collection, PostgreSQL,
models and existing catalog/order data are unchanged. S3 remains optional.

Build command:

```sh
pip install -r requirements-media.txt && python manage.py collectstatic --noinput
```

Start command:

```sh
gunicorn suryavets.wsgi:application --bind 0.0.0.0:$PORT
```

Add these in Render's environment settings, not in Git:

```text
MEDIA_STORAGE_BACKEND=cloudinary_storage.storage.MediaCloudinaryStorage
CLOUDINARY_CLOUD_NAME=<your cloud name>
CLOUDINARY_API_KEY=<your API key>
CLOUDINARY_API_SECRET=<your API secret>
```

Keep the existing production configuration: `DEBUG=False`, `DJANGO_SECRET_KEY`,
`DATABASE_URL`, explicit `DJANGO_ALLOWED_HOSTS`, HTTPS `PUBLIC_SITE_URL` and
`CSRF_TRUSTED_ORIGINS`. No persistent disk or `PERSISTENT_MEDIA_ROOT` is required
for Cloudinary. Never use temporary directories as production media storage.

When selected, Cloudinary requires all three credentials. The apps are loaded
only for this backend, after `django.contrib.staticfiles` so the package does not
override Django's `collectstatic`. The filesystem production guard stays intact.

The adapter is django-cloudinary-storage 0.3.x with the maintained Cloudinary
1.x SDK (minimum 1.44). The adapter has an older release history; compatibility
is checked locally rather than assumed from its Django version classifiers.
References: https://github.com/klis87/django-cloudinary-storage and
https://github.com/cloudinary/pycloudinary .

Validation:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python -m unittest shop.test_media_settings
```

The isolated tests use dummy credentials and block network connections. They
initialize media storage, generate ImageField/FileField URLs, run Django checks
and collect static files into an automatically removed test directory. They
also check missing credentials, filesystem rejection, and retained S3 settings.

Verified locally on 4 October 2026 with Django 6.1.1, Cloudinary 1.46.2 and
django-cloudinary-storage 0.3.0: all six storage configuration tests and 21
existing media/launch tests passed. Django system checks, migration drift checks
and `pip check` passed. No real Cloudinary upload or Render deployment was tested.

Important: changing the backend does NOT copy existing local media to Cloudinary.
Existing database file names must correspond to uploaded Cloudinary assets before
those images work. Migrating existing files, validating real credentials/uploads,
and checking the deployed Render service remain separate steps. No database
records or remote assets are modified by this configuration change.

# Phase 11: production configuration

The application uses SQLite locally when `DATABASE_URL` is empty. On Render, provide a PostgreSQL `DATABASE_URL`; `dj-database-url` selects it automatically.

Required Render environment variables:

- `DJANGO_SECRET_KEY`: a unique, long random secret.
- `DEBUG=False`
- `DATABASE_URL`: Render PostgreSQL internal connection URL.
- `DJANGO_ALLOWED_HOSTS`: the Render hostname, and later `suryavets.com,www.suryavets.com`.
- `CSRF_TRUSTED_ORIGINS`: comma-separated HTTPS origins, for example `https://your-service.onrender.com,https://suryavets.com,https://www.suryavets.com`.

Use an SMTP-compatible `DJANGO_EMAIL_BACKEND` and its provider settings before sending production order emails. HSTS defaults to one year in production; set `SECURE_HSTS_SECONDS=0` until the final HTTPS domain is confirmed if you need to defer it.

Static files are served by WhiteNoise after `collectstatic`. Product images are currently local development media; do not rely on Render's filesystem for persistent uploads. Configure Cloudinary or S3-compatible storage before uploading the production catalogue.

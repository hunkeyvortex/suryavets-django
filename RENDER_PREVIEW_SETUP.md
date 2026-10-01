# Render preview preparation — do not deploy yet

This is a configuration checklist, not an approved deployment or hosting purchase. No service, database, domain or scheduled job has been created.

## Commands

- Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Pre-deploy migration: `python manage.py migrate --noinput`
- Start: `gunicorn suryavets.wsgi:application --bind 0.0.0.0:$PORT --access-logfile - --error-logfile -`
- Health path: `/health/`

Keep migrations out of per-instance startup. Check that the chosen Render plan supports pre-deploy commands; if not, run a supervised one-off migration before routing traffic. No plan price or free-tier suitability is assumed. PostgreSQL and web service should be in the same region. Test PostgreSQL migrations and concurrent checkout before launch; this local run uses SQLite.

## Required environment

- `DEBUG=False`
- `DJANGO_SECRET_KEY`: independently generated, private, at least 50 characters.
- `DJANGO_ALLOWED_HOSTS`: exact preview hostname; no wildcard.
- `CSRF_TRUSTED_ORIGINS`: exact HTTPS preview origin.
- `PUBLIC_SITE_URL`: HTTPS preview origin, without trailing path.
- `DATABASE_URL`: managed PostgreSQL connection, encrypted and backed up.
- `SITE_NOINDEX=True`: retain on preview. Only change after launch approval.
- `ORDER_EMAIL_ENABLED=False`, `PASSWORD_RESET_EMAIL_ENABLED=False`, `RAZORPAY_ENABLED=False`, `ANALYTICS_EVENTS_ENABLED=False` initially.
- `SECURE_HSTS_SECONDS=0`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=False` initially. Increase gradually only after HTTPS/domain verification. Do not enable preload blindly.

Runtime settings reject missing/insecure production essentials. They preserve SQLite and local media for DEBUG development. Install production dependencies before production checks. Do not place real values in tracked files.

## Media

Render's ordinary application filesystem is not persistent media storage. Choose either:

1. External S3-compatible media: install `requirements-media.txt`, set `MEDIA_STORAGE_BACKEND=storages.backends.s3.S3Storage`, configure the adapter's bucket/region/endpoint and environment credentials, verify ACLs and CORS, then migrate uploads separately with checksums.
2. A deliberately provisioned persistent disk: set `PERSISTENT_MEDIA_ROOT` to its mounted path, arrange authenticated upload handling and a production media-serving layer. WhiteNoise only serves static files, not product uploads. Check disk/worker/backup constraints before selecting this option.

External storage abstraction is prepared; no media was uploaded. The exact provider/configuration, image URL availability and storage restore test remain deployment prerequisites.

## Operations

- Verify backups before migrations. Managed PostgreSQL backups/PITR plus separate versioned media backups are required; document retention and perform a restore drill.
- Collect static files at build time. WhiteNoise serves collected static assets in production. Verify images/CSS after deployment.
- Run `python manage.py operations_check` for database/migration/outbox counters without customer data.
- Outbox preview: `python manage.py send_order_notifications --dry-run`.
- After verified sending is explicitly enabled: `python manage.py send_order_notifications --limit 100` from one worker/cron invocation. Do not enable or schedule this now.
- `sending` or unknown-outcome notifications need provider reconciliation; never automatically reset them to pending. Known retryable failures have finite attempts and backoff. Sandbox previews are not delivered mail.
- Optional daily throttle cleanup: `python manage.py operations_check --clean-expired-throttles`. It deletes only expired abuse counters, not stock, orders or business records.
- No stock-reservation cleanup command was added: no independent expiring reservation model was found. Do not invent a stock-release job.
- Use stdout/stderr logs, monitor HTTP error rates/health failures and alert on stuck/failed outbox entries. Redact request bodies, email addresses, authentication/reset tokens and payment secrets from external monitoring. A monitoring provider has not been configured.
- Configure a trusted edge/client-IP strategy before scaling abuse protection: application limits deliberately ignore spoofable forwarded headers and use REMOTE_ADDR plus normalized login/reset identity. Shared proxy/NAT addresses can share limits.
- Contact messages and newsletter records are visible to explicitly permitted Django Admin staff. Define retention, newsletter confirmation/unsubscribe policy and a privacy-reviewed campaign process before sending campaigns. No campaigns are implemented or sent.
- Password-reset responses are generic and tokens are Django's built-in expiring/single-use tokens. Delivery remains off; configure a verified sender and test deliverability before enabling. Built-in synchronous delivery can have timing differences; an asynchronous generic mail outbox/edge rate limit is recommended before high-volume public exposure.

References: https://render.com/docs/deploys, https://render.com/docs/health-checks, https://docs.djangoproject.com/en/dev/howto/deployment/.

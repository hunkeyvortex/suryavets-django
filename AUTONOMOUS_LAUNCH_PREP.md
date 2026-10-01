# Autonomous launch preparation

29 September 2026 · `C:\Users\danyb\Desktop\suryavets-django`

Technical foundations implemented locally. **Not deployed and not launch-ready.** No real credentials were requested, no real notification queue was drained, no campaigns sent, and no Shopify/DNS/payment activation performed. Stock, prices and final merchandising selections were not changed.

Checkpoint: `codex/launch-prep-checkpoint-20260929`, `3f8f5136f848203e55071b8e38702b8c7cb50443`. Existing unrelated changes and untracked files were preserved.

## A. Performance

See `CATALOG_PERFORMANCE_PHASE.md` for exact before/after timings. The old eight-second behavior was not reproducible: requests were already around 0.2–0.3 seconds before this phase. Removed unused global featured-product work: dog catalog 17→14 queries; search 15→12; price sorting 17→14. Wall-clock samples are mixed, so only the query reduction is established. Existing family-price semantics, pagination and prefetch architecture are preserved.

## B. SEO

- `/sitemap.xml`: active canonical products and categories with active ancestry, plus home/contact/about. XML is escaped and private routes are excluded.
- `/robots.txt`: staging disallow-all by default; production public configuration lists private exclusions and sitemap URL.
- Canonicals, Open Graph and Twitter summary metadata in the shared storefront template. Category metadata fields added blank, with existing descriptions as fallback. Existing product metadata fields reused.
- JSON-LD Product and BreadcrumbList on product/category pages; Organization/WebSite on homepage. No reviews, ratings, descriptions or unsupported offer prices invented. Product offers are emitted only for a positive currently purchasable selection.
- Private account/CRM/admin/cart/checkout/auth/reset/search responses receive noindex headers and no-store caching. `SITE_NOINDEX=True` defaults to protecting preview pages. It is not access control.
- Meaningful storefront 404 and a standalone, database-independent 500 template.

Final copy, canonical-domain approval, all-page visual checks and a search-engine structured-data validator run remain release review items. Sitemaps are discoverability lists, not catalog-quality certification.

## C. Legacy redirects

Created `catalog_review/seo_redirect_review.csv`: **6,872 rows**, **6,866 deterministic mappings**, **six page handles left for review**. Sources are the two previously supplied Shopify product exports plus stored category `reference_path` values. Product mappings require exact source handle and matching normalized title identity; category mappings require a unique active reference path and active ancestors.

Runtime uses `catalog_review/seo_redirects.json`, cached by file modification time, and rechecks active destinations. Product and collection paths accept trailing slashes. Nested collection/product URLs work only when both parts are known. Unverified `/pages/` URLs and unknown paths return 404, never the homepage. Query links containing legacy `variant` or `variant_id` are rejected until an explicit Shopify-to-Django variant-ID mapping exists; silently reusing numeric IDs could choose the wrong pack.

`seo_redirect_matrix.json` retains source hashes and review rows. The spreadsheet skill/Artifact Tool authored and verified the CSV, preserving the requested five columns. Deployments must include the reviewed mapping artifact; report generation is not a business-data import.

## D. Contact

`/contact/` now accepts CSRF-protected POST, validates bounded name/email/optional phone/subject/message, saves `ContactSubmission`, then redirects without placing message contents in a query string. It renders validation/throttle errors, has a honeypot and database-backed rate limiting. Django Admin provides permission-controlled review/resolution. No outbound email is needed or attempted. Existing authenticated order support is separate because it requires an account/order relationship.

## E. Newsletter

Newsletter signup now requires valid email and an explicit consent checkbox. Lowercased unique email, consent timestamp and active/unsubscribed state are stored. Duplicate requests preserve the original consent date; an opted-out record is not silently reactivated. Staff can mark opt-outs in Admin, with timestamp recording. No paid platform/campaign integration. A public unsubscribe/double-opt-in delivery workflow and approved marketing/privacy process are prerequisites before sending any campaigns.

## F. Account security

Added `/password-reset/`, request-complete, token-confirmation and completion routes using Django's built-in forms/tokens/password validation. Tokens expire after one hour and become invalid after password change. Reset responses are generic for existing/nonexisting/rate-limited accounts. Reset links use configured PUBLIC_SITE_URL, not arbitrary request hosts. HTML and text templates are present. `PASSWORD_RESET_EMAIL_ENABLED=False` by default; no credentials or real sends used.

Login (customer/CRM/admin) and reset submissions have shared database fixed-window limits. Keys hash identifiers rather than storing cleartext IP/email. Spoofed forwarded-IP headers are ignored. Existing staff permissions/customer ownership protections remain intact. Trusted proxy/client-IP design must be checked on Render to avoid unfair limits for shared proxy/NAT addresses. Built-in synchronous reset sending can still have timing differences once enabled; generic responses are not a guarantee of timing-resistant account enumeration. Consider an asynchronous reset-delivery queue before high-volume exposure.

## G. Notifications

Existing order outbox already had a unique event/channel/audience constraint, conditional claim, finite attempts, backoff, sent/failed/preview states, deterministic provider idempotency key, sanitized error codes and HTML/text messages. These were reused. Added bounded batches (default 100, capped at 500) and `send_order_notifications --dry-run`, which only reports a count. Existing mocked Brevo retry/duplicate/uncertain-outcome tests were retained. Unknown or stuck `sending` records are not automatically resent; provider reconciliation remains required. Real pending notifications were not processed.

## H. Background commands

- `send_order_notifications --dry-run`: no sends/state changes.
- `send_order_notifications --limit 100`: future explicitly enabled worker invocation.
- `operations_check`: read-only database/migration/outbox/throttle counters, no private payloads.
- `operations_check --clean-expired-throttles`: explicitly removes only expired abuse counters.
- `profile_catalog`: read-only performance diagnostics.
- `review_seo_redirects --sources <exports>`: source-evidenced local redirect artifacts, no catalog mutation.

No external jobs were scheduled. No independent expiring stock-reservation model was found, so no speculative stock-release job was created.

## I–L. Production, static, media, health and Render

See `RENDER_PREVIEW_SETUP.md` for build/start/migration commands, environment checklist and backup/logging/worker guidance. Actual WSGI is `suryavets.wsgi:application`.

Production validates strong secret, explicit hosts, HTTPS public origin, PostgreSQL DATABASE_URL, WhiteNoise and persistent/external media configuration. Local SQLite/media remain supported. Cookies, HTTPS proxy header, frame/content headers and upload-size boundary are configured. HSTS defaults to zero for staged rollout rather than forcing irreversible subdomain policies.

`MEDIA_STORAGE_BACKEND` supports an external adapter; optional `requirements-media.txt` supplies S3-compatible storage, with bucket/region/endpoint options from environment and ordinary AWS environment credentials. Alternatively a deliberately mounted persistent path can be configured, but requires a separate production media-serving and backup plan. No media was uploaded.

Static collection verified: **217 files, no duplicate-source conflicts after removing the redundant shop/static directory registration**. WhiteNoise remains production-only. No render.yaml or deployment was applied: the documented settings must be matched to the chosen service/storage plan first; no price/free-tier capability is assumed.

`/health/` checks app/database reachability and returns only `ok` or sanitized `unavailable`. PostgreSQL connectivity, concurrency, backups/restores and live preview operation cannot be certified without the eventual infrastructure. Production-setting validation with temporary dummy configuration succeeded with only the intentional HSTS-zero warning; it did not connect to PostgreSQL.

## M. Analytics foundation

Provider-neutral, disabled-by-default local browser event bus (`ANALYTICS_EVENTS_ENABLED=False`). Supports view_item, successful add_to_cart, begin_checkout and eligible order-confirmation purchase events. No provider IDs, external requests, contact details or names/emails are included. Purchase events deduplicate within a browser session; this is not cross-device/server-side exactly-once delivery. Before connecting a provider, complete consent/privacy review and provider-side transaction deduplication.

## N. Tests and data preservation

- Full regression suite: **334 tests, OK, 14 optional tests skipped**.
- Explicit focused security plus offline homepage browser run: **15 tests passed**. Browser external requests blocked; tested 320/360/375/390/412/430/768/1024/1440px, variant cart behavior, navigation and layout.
- Contact validation/persistence/CSRF/honeypot/throttle, newsletter consent/duplicates/opt-out, reset HTML/text/token/single-use/generic response, forged-IP login throttling, JSON-LD escaping, private caching, health failure sanitization, unknown/external/variant redirects, analytics payload and dry-run notification behavior covered.
- `manage.py check`: passed. `makemigrations --check --dry-run`: no pending changes.
- Additive migration applied: `0018_public_launch_foundations` creates ContactSubmission, NewsletterSubscription and RequestThrottle; adds blank category meta_title/meta_description.
- Original-field fingerprints match the earlier Phase 3 baseline for Product (6,697), ProductVariant (6,678), ProductImage (2,620), Category (170), Brand (569), InventoryMovement (6,696), Order (3), OrderItem (3), review events and both catalog many-to-many relations. New schema fields were excluded from the historical comparison. No original catalog/order/stock/price data changed.

## Files changed

New code: `shop/public_forms.py`, `shop/public_views.py`, `shop/seo.py`, `shop/services/throttling.py`, `shop/templatetags/seo_tags.py`, `shop/templatetags/analytics_tags.py`, `shop/test_launch_prep.py`, `shop/migrations/0018_public_launch_foundations.py`; management commands `profile_catalog.py`, `operations_check.py`, `review_seo_redirects.py`.

New templates/assets: `shop/templates/public/contact.html`, `shop/templates/registration/reset_*`, `shop/templates/404.html`, `shop/templates/500.html`, `shop/static/css/public-forms.css`, `shop/static/js/commerce-events.js`.

Extended: `shop/models.py`, `shop/admin.py`, `shop/urls.py`, `shop/views.py` (post-success analytics only), `shop/context_processors.py`, `shop/services/notifications.py`, `shop/management/commands/send_order_notifications.py`, `shop/test_catalog_performance.py`, `shop/home_discovery_browser_test.cjs`, `shop/templates/base_shared.html`, `shop/templates/auth_login.html`, `shop/templates/includes/footer.html`, `shop/templates/catalog/product_list.html`, `suryavets/settings.py`, `suryavets/urls.py`.

Artifacts/docs: `catalog_review/seo_redirect_review.csv`, `seo_redirects.json`, `seo_redirect_matrix.json`, `requirements-media.txt`, `CATALOG_PERFORMANCE_PHASE.md`, `RENDER_PREVIEW_SETUP.md`, this report. Collected static files are generated output.

## Remaining owner/client-dependent tasks

1. Verify physical stock and unresolved catalog identities/artwork; choose final homepage products. Existing P0 issues are not resolved by this technical work.
2. Approve shipping zones/charges, COD eligibility, tax handling, returns and policy wording; none were invented.
3. Verify email sender/domain and enable/test delivery, password reset and notification inbox receipt. Approve newsletter consent/unsubscribe process before campaigns.
4. Configure Razorpay credentials and conduct authorized payment/refund/webhook reconciliation tests; live payment remains off.
5. Choose PostgreSQL/media/Render resources, retention/backups/monitoring and test a separate preview, including PostgreSQL concurrency and restore drills.
6. Approve six legacy page mappings and map any legacy variant-ID links; validate production-domain canonical URLs and SEO before cutover.
7. Only after acceptance: approved final imports, backup, DNS/cutover and Shopify retirement plan. Shopify must stay live until then.

References used for deployment preparation: [Render deploys](https://render.com/docs/deploys), [Render health checks](https://render.com/docs/health-checks), [Django deployment](https://docs.djangoproject.com/en/dev/howto/deployment/).

# SuryaVets CRM and original customer accounts

## Local workspace

Implemented inside **C:\Users\danyb\Desktop\suryavets-django**, using the existing `shop` app and database. No separate Render project or duplicate customer database. Boww & Meow's staff page structure was inspected as a workflow reference; no accounts, credentials or customer data were copied from it.

Baseline source checkpoint: `0796f17`. A timestamped `tmp/pre-crm-*.sqlite3` database backup was created before migration 0007. Migration adds stock history and internal activity; it does not alter old order totals or invent past movements.

## Open the pages

- Customer login: http://127.0.0.1:8007/login/
- Customer signup: http://127.0.0.1:8007/register/
- Staff CRM: http://127.0.0.1:8007/crm/
- Admin / staff permissions: http://127.0.0.1:8007/admin/

The customer login/signup design is intentionally original, as requested: forest green, gold, white, reusable SVG paw artwork and mobile layouts. Old unused login/register templates are retained; the active views render `auth_login.html` and `auth_register.html`.

## First operational CRM version

- Dashboard: open orders, recorded paid total, active catalog count and customer contacts.
- Orders: search, status/payment filters, pagination, item/address snapshots, internal notes, fulfilment transitions.
- Customers: guest and registered purchasers grouped by order email, history and internal contact notes. These are order contacts, not verified identities. A newly registered user without orders remains in Django Admin's user list rather than this order-contact directory.
- Inventory: searchable catalog, low/out-of-stock filters, individual pack adjustments, before/after quantities and staff attribution.
- Reports: payment-status and fulfilment counts, plus latest 50 stock movements. Pending orders are never labelled paid revenue. Paid totals are not net profit or reconciled financial statements.
- Viewer, Operations and Manager roles, enforced in views and write services. Staff flag alone is insufficient. Superusers can access the CRM.

## Access setup

Local migration and group setup have already been run. On another checkout, from the project folder:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py setup_crm_roles
.\.venv\Scripts\python.exe manage.py check
```

Use an existing superuser to sign in. If there is no administrator, create one interactively:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

For other staff, open Admin → Users, select the account, enable **Active** and **Staff status**, and assign one group:

| Group | Access |
| --- | --- |
| Surya CRM Viewer | Read CRM customer/order/inventory/report data |
| Surya CRM Operations | Viewer + fulfilment/cancellation + internal notes |
| Surya CRM Manager | Operations + audited stock adjustments |

No accounts were created in the development database and no existing user was promoted automatically. Group setup adds its named permissions while preserving any existing group permissions. Review pre-existing permissions before assigning a reused group. Never give customers staff access.

## Stock and order safeguards

- New checkout deductions and CRM adjustments share transactional stock history.
- Cancellation only before shipping, with a reason. Pending/failed-payment orders may cancel; paid/refunded orders require a separate reviewed refund/returns process, not this button.
- Exact original deductions are restored once. Repeated cancellation does not add stock twice. Untracked lines do not receive invented stock.
- Older stock-deducted orders without a complete ledger are refused automatic cancellation; do not manually set `inventory_recorded` to bypass this.
- Adjustments require permission, a reason and a signed review token. Stale stock, negative balances, altered tokens and duplicate submissions are guarded.
- Product/variant stock fields and order payment/status fields are read-only in Django Admin. Use CRM workflows for stock/status changes; new products/variants start at their model default stock and then receive an audited adjustment.
- Movement records protect referenced products/variants/orders from deletion. Archive catalog products instead.
- Full Shopify product/inventory snapshot writes stop once stock movements exist, including CRM adjustments. Preview/dry-run remains available. Product imports must not run against a trading storefront; a future reconciled/delta import workflow is required.

## Customer account safeguards

- Django password validation and authentication; explicit field errors and Show/Hide controls.
- Safe same-host return URLs; login/signup/logout self-redirects rejected.
- Anonymous basket lines merge into the account basket on login/signup; stock is checked again at checkout. Guest order ownership is not reassigned by matching email.
- Logout is POST + CSRF protected; customer registration cannot grant staff/superuser privileges.
- CRM pages are private/no-store and marked noindex. Notes are escaped and kept off customer receipts.

## Verification

Final local result: **79 tests passed**, including both optional browser suites. `manage.py check` passes and `makemigrations --check --dry-run` reports no changes. Login, signup and CRM login each returned HTTP 200 on the existing port 8007 preview. An active existing administrator was confirmed without reading or changing credentials.

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Browser verification is opt-in; without these variables the browser tests skip:

```powershell
$env:SURYA_BROWSER_NODE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:SURYA_PLAYWRIGHT_MODULE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:SURYA_BROWSER_EXECUTABLE='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
$env:SURYA_BROWSER_ARTIFACTS='C:/Users/danyb/Desktop/suryavets-django/tmp/crm-verification'
.\.venv\Scripts\python.exe manage.py test
```

Browser tests use a disposable test database, fake staff/customer accounts and fake orders. They test signup, password visibility, CRM sign-in, inventory adjustment, internal notes, cancellation, and page overflow at 375/390/430/768/1024/1440px. Desktop/mobile screenshots are stored under `tmp/crm-verification/` and excluded from Git. Test screenshots are not real customer records.

## Changed files

- `shop/models.py`, `shop/migrations/0007_crm_stock_history.py`: ledger, activity and complete-ledger flag.
- `shop/services/crm.py`, `shop/crm_forms.py`, `shop/crm_views.py`, `shop/crm_urls.py`: staff workflows.
- `shop/templates/crm/`, `shop/static/css/crm.css`: reusable staff UI.
- `shop/services/checkout.py`: record actual stock deductions atomically.
- `shop/admin.py`, `shop/management/commands/setup_crm_roles.py`: controlled admin writes and roles.
- `shop/management/commands/import_shopify_products.py`, `reconcile_shopify_inventory.py`: snapshot-overwrite guards.
- `shop/services/accounts.py`, `shop/views.py`, `shop/forms.py`: customer auth and basket preservation.
- `shop/templates/auth_base.html`, `auth_login.html`, `auth_register.html`, `includes/auth_fields.html`, `profile.html`: original account design and safe logout.
- `shop/static/css/auth.css`, `shop/static/js/auth.js`: responsive styles and password controls.
- `suryavets/urls.py`: separate `/crm/` namespace.
- `shop/test_crm.py`, `test_accounts.py`, `test_inventory.py`, `test_crm_browser.py`, `crm_browser_test.cjs`: regression/browser coverage.
- This guide and `SURYA_MIGRATION_AUDIT.md`.

## Remaining before production

This is not a complete enterprise CRM or a production-ready payment system. Still required: reviewed online payment/webhook/refund and COD collection workflows; returns after dispatch; shipment/carrier integration; transactional emails and password reset delivery; login rate limiting/MFA policy; physical stock and variant tracking verification; account identity/email-verification policy; PostgreSQL concurrency tests; privacy/retention/export controls; backups/security/SEO and Render staging tests. Staff notes are append-only in the UI; authorized database operators retain database access.

The Shopify storefront and DNS were untouched. Keep Shopify live. Existing preview is already running on port 8007; do not launch a duplicate server. If stopped, run `.\.venv\Scripts\python.exe manage.py runserver 8007`.

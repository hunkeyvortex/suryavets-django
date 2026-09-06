# Original basket and payment choices

Updated 7 September 2026 at the user's request. This is intentionally an original SuryaVets design, not a Shopify visual-parity milestone.

## Changes

- Cream/green/gold basket with delivery progress, product cards, pack details, formatted prices and an order summary. Mobile keeps the products before the summary; desktop has a sticky summary.
- Accessible +/- quantity controls with explicit Update, existing CSRF-protected update/remove forms and a redesigned empty state. No pricing or stock logic moved to the browser.
- Checkout offers Cash on Delivery (COD) and displays Online Payment as disabled/coming soon. A gateway is not connected, so both the form and order service reject attempted online orders. Existing historical manual-payment records are unchanged; new manual-payment orders are no longer offered.
- Existing coupon application/removal, stock checks, idempotent orders, accounts and CRM are preserved. No database migration or credentials needed.

## Files

- `shop/templates/basket.html`, `shop/static/css/basket.css`, `shop/static/js/cart.js`: new scoped basket presentation; previous cart template/CSS retained as inactive files.
- `shop/views.py`: render the new basket template.
- `shop/services/cart.py`: expose the existing delivery threshold to the progress element.
- `shop/forms.py`, `shop/services/checkout.py`: payment choices and unavailable-method enforcement.
- `shop/templates/checkout_new.html`, `shop/static/css/checkout.css`: payment cards and honest availability messaging.
- `shop/checkout_browser_test.cjs`, `shop/test_checkout.py`, `shop/tests.py`: browser flows, unavailable-method tests and formatted-price expectation.
- `SURYA_MIGRATION_AUDIT.md`, this guide: milestone tracking.

## Verification

All 105 tests passed with all three browser suites enabled. Django check passes; no migration drift. Browser coverage exercises quantity increase/decrease and Update, item removal, empty basket, coupon apply/remove and real COD order submission against a disposable test database. It also verifies the online radio is disabled. Basket and checkout are checked at 375, 390, 430, 768, 1024 and 1440 pixels; desktop/mobile screenshots reviewed. This is not payment-gateway testing.

Screenshots are under `C:/Users/danyb/Documents/ChatGPT/suryavets-django/basket-verification/`.

PowerShell commands from the existing project:

```powershell
cd C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

For optional browser tests, set these before the test command:

```powershell
$env:SURYA_BROWSER_NODE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:SURYA_PLAYWRIGHT_MODULE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:SURYA_BROWSER_EXECUTABLE='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
$env:SURYA_BROWSER_ARTIFACTS='C:/Users/danyb/Documents/ChatGPT/suryavets-django/basket-verification'
```

No server restart needed: use the existing `http://127.0.0.1:8007/cart/` preview and refresh. Baseline checkpoint branch: `codex/checkpoint-before-cart-redesign-20260907`, commit `9be7ae1`. Shopify, DNS, external payments and production remain untouched. Gateway selection, server-created payment sessions and verified webhooks are required before online payments can be enabled.

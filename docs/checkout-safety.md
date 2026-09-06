# Checkout and inventory safeguards

Local milestone: 2026-09-07. Source checkpoint before changes: d922aa5.
Database backup: tmp/checkpoints/before-checkout-safety.sqlite3.
No live Shopify actions, DNS changes, deployment or development-database test orders.

## Inventory findings

The supplied inventory_export_1.csv contains one location column, Andheri West, with 12 rows and 162 total units. All 12 handle/pack identities and quantities already match Django. No inventory quantities were overwritten. SKUs are blank in these rows, so reconciliation relies on exact handles and option names, not fuzzy product-title matching.

The spreadsheet skill's read-only validation checked the CSV structure and totals independently. The Django command then checked those identities against the database. The source CSV was not edited.

This file does not confirm availability across all 6,697 products. Products omitted from it were left unchanged. Existing variant tracking limitations and placeholder quantities on other imported products are not a verified stock source.

## Implemented behavior

- Checkout uses a signed, 30-minute review token bound to the cart and its item/quantity/price snapshot.
- The service locks the cart, then products and variants in deterministic order. Tracked quantities are deducted with conditional database updates within the same transaction as order creation and cart clearing. A shortage or later database error rolls everything back.
- Variant identity, active state, quantities, and current prices are checked again. A changed cart or price requires the shopper to review the refreshed total.
- A unique order checkout key prevents repeated submissions from creating additional orders. Replaying an earlier completed token returns its receipt without clearing newer cart items.
- Successful submission redirects to a confirmation URL. Refreshing confirmation does not submit another order. Guest receipts require the original session cart; authenticated receipts/history require the owner.
- Add/update/remove cart mutations use POST, CSRF protection and cart locks. Return URLs are restricted to the current host. Anonymous shoppers cannot modify another session's cart.
- Database lock conflicts produce a retryable response without losing the review token. The browser disables Place order during submission; server protections also work with JavaScript disabled.
- Empty cart reads no longer create authenticated carts or show a shipping fee. The cart image uses its imported URL fallback when no downloaded file exists.
- Admin cannot add/delete orders or add snapshot lines. Financial totals and checkout metadata are read-only. Payment/status changes still require an operational workflow; see limitations below.
- Added a read-only-by-default exact inventory reconciliation command. It requires an explicit location, rejects duplicate identities and invalid quantities, skips unmatched rows and never zeroes omitted products. Applying snapshots/full product exports is blocked when local stock-deducting orders exist.

## Verification

The full suite includes ordinary model/request tests, simultaneous checkout races, and an optional real-browser test on Django's disposable test database.

Final verification: all 56 tests pass with the browser runtime enabled; Django check passes and no migration drift is detected through migration 0006. Without browser configuration, 55 tests run and the optional browser test is skipped.

Covered: duplicate requests and retries, two carts competing for the last unit, aggregate duplicate cart lines, price/quantity changes, expired/foreign/missing tokens, stock shortages, inactive products, variant mismatch, rollback after order-write failure, untracked simple products, authoritative order pricing, ownership, CSRF, POST-only mutations, safe return URLs, inventory parser matching and no-write defaults.

The browser test serves real static files and exercises product → cart → checkout → confirmation, checks 390px/1440px layouts for document overflow, repeats the POST and checks that an unrelated browser cannot read the receipt. Its fixture orders are destroyed with the test database. No purchase was placed on Shopify or the development database.

SQLite concurrency tests pass locally. PostgreSQL-specific locking/load testing remains mandatory before a production rollout; this is not a claim that a Render/PostgreSQL deployment has been tested.

## Commands

```powershell
Set-Location 'C:/Users/danyb/Desktop/suryavets-django'
./.venv/Scripts/python.exe manage.py check
./.venv/Scripts/python.exe manage.py test
./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
./.venv/Scripts/python.exe manage.py reconcile_shopify_inventory 'C:/Users/danyb/Downloads/inventory_export_1.csv' --location 'Andheri West'
```

The inventory command is read-only without --apply. There is no reason to apply the current file: every quantity already matches. Never run stock-writing imports while the storefront is accepting orders; offline maintenance and movement reconciliation are required.

Optional browser test (uses the installed runtime and browser on this machine):

```powershell
$env:SURYA_BROWSER_NODE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:SURYA_PLAYWRIGHT_MODULE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:SURYA_BROWSER_EXECUTABLE='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
./.venv/Scripts/python.exe manage.py test shop.test_checkout_browser
```

## Files changed

- shop/services/checkout.py: atomic order creation and signed review tokens.
- shop/services/cart.py, shop/views.py, shop/urls.py: ownership, guarded mutations and checkout/receipt routing.
- shop/models.py, shop/migrations/0006_checkout_idempotency.py, shop/admin.py: idempotency metadata and admin safeguards.
- shop/templates/checkout_new.html, shop/templates/cart_new.html, shop/static/js/checkout.js: review/submit UI and imported-image fallback.
- shop/management/commands/reconcile_shopify_inventory.py and import_shopify_products.py: conservative inventory handling.
- shop/test_checkout.py, shop/test_inventory.py, shop/test_checkout_browser.py, shop/checkout_browser_test.cjs, shop/tests.py, shop/test_pricing.py: regression coverage.
- This document and SURYA_MIGRATION_AUDIT.md: progress and remaining work.

## Still required before launch

1. Complete, current inventory and per-variant tracking/backorder rules. Multi-location stock must not be blindly summed into one field.
2. Cancellation/expiry/restocking workflow. This implementation deducts stock immediately for accepted pending COD/manual orders. Merely changing an order status to cancelled does not return stock; do not assume automatic reservation release.
3. Payment provider integration, verified callbacks, reconciliation/refunds and email notifications. Orders remain payment-pending; no online money is collected.
4. Prescription approval rules, final delivery zones/rates and tax rules. Existing shipping arithmetic is retained, not verified as a production policy.
5. PostgreSQL concurrent-load tests, security review, backups/restore and production monitoring.
6. Guest-cart merge on login, broader authentication hardening, remaining visual/merchandising differences and SEO redirects.

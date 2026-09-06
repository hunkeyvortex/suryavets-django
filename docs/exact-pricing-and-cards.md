# Exact pricing and shared product cards

Completed local milestone: 2026-09-07. Live Shopify and DNS were not changed.

## What changed

- Added nullable Decimal `selling_price` fields to Product and ProductVariant through additive migration 0005. Explicit prices take precedence; older manually entered products retain the percentage fallback, rounded to paise. Zero is a valid explicit price.
- Shopify `Variant Price` now supplies the exact selling price. A higher compare-at price supplies the original price; the rounded percentage is a display badge only, never the basis of an imported selling price.
- A separate `restore_shopify_prices` command validates all supplied prices and variant name/SKU identities before applying any updates. It is read-only unless `--apply` is supplied. No products, variants, images, inventory or order lines are deleted by this repair.
- Price filters and ordering now use the same selling-price calculation as cards, rather than the compare-at price.
- Reimports update variants by product/name and retain downloaded images when their source URL matches. Missing export variants are deliberately retained, not silently deleted. Renamed variants still require explicit reconciliation; no Shopify variant IDs are available in these CSVs.
- Split CSV/ZIP sources are grouped by handle across all files. Identical repeated variant rows are collapsed; conflicting prices/SKUs for the same variant name are rejected. Missing, negative, non-finite, excessive-precision and oversized prices are rejected instead of becoming free products.
- Cards use one template and one shared stylesheet: measured red badges, green-outline buttons, two-line titles, grouped decimal prices, square images, radii/shadows and responsive carousel columns. Removed the invented `No rating yet` card line.
- Products with multiple active variants use Choose options. The server requires a selection rather than silently choosing a pack. Detail pages select an available pack and update price, compare-at visibility and quantity limits on changes. Server-side prices remain authoritative.

## Actual data repair

Backup before changes: `tmp/checkpoints/before-exact-prices.sqlite3`.
Source checkpoint before changes: `fb18a81`.

Validated 6,697 products and 6,677 existing variant records against both supplied product ZIPs.
Corrected 2,428 product display prices and 2,424 variant display prices.
Example: ARNICA MONTANA 30ML was calculated as Rs. 95.45 from a rounded 17% discount; the export specifies Rs. 95.00 against Rs. 115.00.
A repeated read-only validation reports zero product/variant price mismatches.

Stock was untouched. Existing carts use updated catalogue prices; saved order-line unit prices remain unchanged.
The supplied inventory file has only 12 rows and is still insufficient to verify the whole catalogue.

## Verification

- 29 Django tests pass, including 14 added price/import/card/variant regression tests.
- `check` passes; `makemigrations --check --dry-run` reports no drift.
- Full importer dry run validates 6,697 handles, 6,697 priced export rows (20 default-title rows need no separate variant record), and 2,619 image references.
- Live/local homepage card screenshots compared at 375, 390, 430, 768, 1024, 1440 px. No document overflow or JavaScript errors in these tested states. The first cards contain different merchandise, so this is a component comparison, not a merchandising or full-page parity claim.
- Card widths (live/local): 151.5/151.5, 161/161, 181/181, 195.516/195.719, 205/205, 243.188/243.188 px, respectively. Matched radii, shadows and square image dimensions. Small rounding differences remain.
- Corrected local Arnica detail page renders Rs. 95.00.
- Isolated browser fixture verifies variant price changes, compare-at visibility and quantity clamping without creating real products/orders. Current imported catalogue has no products with multiple variant records; backend multi-variant behavior is covered using test fixtures.
- Evidence: `C:/Users/danyb/Documents/ChatGPT/suryavets-django/reference-audit/product-card-verification.json`, `card-measurements.json`, `card-live-*.png`, `card-local-*.png`; scripts `verify-product-cards.cjs`, `verify-variant-ui.cjs` in that workspace.

## Changed files

- Models/admin/migration: `shop/models.py`, `shop/admin.py`, `shop/migrations/0005_exact_selling_prices.py`.
- Prices/imports: `shop/services/pricing.py`, `shop/management/commands/import_shopify_products.py`, `shop/management/commands/restore_shopify_prices.py`.
- Views: `shop/catalog_views.py`, `shop/views.py`.
- Templates/formatting: `shop/templates/base_shared.html`, `shop/templates/includes/product_card.html`, `shop/templates/catalog/product_detail.html`, `shop/templatetags/shop_filters.py`.
- Frontend: `shop/static/css/product-card.css`, `shop/static/js/catalog.js`, `shop/static/js/storefront.js`.
- Tests: `shop/test_pricing.py`.
- Tracking: this document and `SURYA_MIGRATION_AUDIT.md`.

## Commands (PowerShell)

Already applied and running on port 8007. Refresh the existing preview; do not start another server on that port.

```powershell
Set-Location 'C:/Users/danyb/Desktop/suryavets-django'
./.venv/Scripts/python.exe manage.py check
./.venv/Scripts/python.exe manage.py test
./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
./.venv/Scripts/python.exe manage.py restore_shopify_prices 'C:/Users/danyb/Downloads/products_export_1 (1).zip' 'C:/Users/danyb/Downloads/products_export_2 (1).zip'
```

Only for another checkout/database after backup: run `manage.py migrate`, validate the exports, then explicitly add `--apply` to the price-repair command if its report is correct. Do not run a full product reimport merely to correct prices: it also updates metadata and inventory.

## Next gates

Full inventory reconciliation; explicit inventory tracking/backorder policy; stock recheck/reservation and transaction-safe order creation; duplicate-submit protection; cart ownership/redirect security; payment verification. Remaining visual work includes homepage merchandising order and collection/product/footer/page-specific parity. No launch or payment-readiness claim is made.

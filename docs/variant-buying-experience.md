# Variant buying experience — 8 September 2026

## Audit before implementation

The active project is `C:/Users/danyb/Desktop/suryavets-django`, not a new project at the older `suryavets` path. Source checkpoint: `codex/checkpoint-before-variant-buying-20260908` at `3170320`. SQLite backup: `tmp/pre-variant-buying-20260908.sqlite3`.

1. Product already has UUID identity, unique handles, category/brand relations, exact Decimal base/selling prices and stock.
2. ProductVariant already exists: 6,677 variants, but **zero products have multiple variants** in the imported catalog. No similarly named products were merged.
3. CartItem already identifies the product and exact variant; different sizes create separate lines. Server prices remain authoritative.
4. OrderItem already snapshots name, size, SKU, unit price and quantity; later catalog edits do not change historical totals.
5. ProductImage already supports ordered galleries, source URLs and local optimized photos/thumbnails. All 2,619 available source photos were migrated in the previous phase.
6. Shopify importer groups exact handles and exact option combinations. Existing operational-stock guards prevent a full snapshot import from overwriting checkout/CRM movements.
7. **4,342 of 6,697 products lack image references.** This task cannot assign trustworthy photos to those products without additional exact source assets.
8. Existing exports have no variant-specific image URLs. Variant images must be explicitly supplied/assigned; no pack-size imagery was guessed.
9. Additive migration `0010_variant_buying`: optional net quantity/unit, comparison group, flexible JSON attributes, ordering and same-product image FK. Image visibility allows recoverable removal. All existing identity, price, stock and order data remain in place.
10. Two existing duplicate-SKU groups were detected. They are preserved for reconciliation. New/changed CRM SKUs and importer assignments reject collisions; there is intentionally no destructive global unique-SKU migration. Variant IDs, not SKU strings, identify purchases.

## Implemented

- Mobile-first two-column pack cards; three columns on wide screens, native accessible radio controls and visible out-of-stock states.
- Exact selected price, MRP, conservative discount percentage, MRP savings, unit price, SKU and image update without reloading. Quantity stepper and Buy now use the same validated cart endpoint. Buy now proceeds to checkout with the selected pack plus any existing basket items; it does not charge a payment.
- Unit quantities support g/kg, ml/L and item counts. Other legitimate option types use names and JSON attributes without misleading unit calculations.
- Comparisons are **opt-in**: only active, in-stock packs sharing an explicit comparison group and comparable units participate. Use that group only for the same formulation/item. No shipping weight or animal-weight range is parsed as net quantity.
- Pack value saving = smallest comparable available pack's exact unit rate × selected quantity − selected price. Only positive savings are shown, rounded down to paise. This is separate from MRP savings. Best value uses the lowest exact comparable unit rate, not largest size; no label for an all-equal rate group.
- Product cards show the lowest available pack price (or lowest active price if all are unavailable), and Choose size for multiple packs. Price filters/sorting use the same offer. A single active pack is explicitly posted from its card. Multiple packs cannot be silently added without a selection.
- All-disabled packs cannot fall back to base-product purchase. Checkout also rejects stale base-product lines when packs exist.
- Cart uses selected pack imagery where supplied, exact names and separate lines. Checkout/order snapshots retained.
- CRM: add/edit/disable packs; manage exact MRP/selling price, SKU, quantity/unit, group, attributes, order and product-scoped image. Stock uses the existing audited adjustment page. New packs start at zero. First-pack creation is blocked until any base stock is reconciled; no automatic stock transfer.
- CRM photo library: upload additional photos, preview, select main photo, reorder, remove with a reason and restore. Removal hides the record and clears pack assignments; files remain stored. Restoring a photo does not silently restore pack assignments. Uploads are now WebP with 360px thumbnails.
- Importer now preserves option attributes, orders newly imported images by Image Position, imports explicit Variant Image references, deduplicates URL paths and preserves staff images/archived records. No full import was run against the operational database.
- Image audit adds Missing Variant Images. CRM exposes the same filter. A missing variant image means "not explicitly verified/assigned", not permission to copy another pack's photo.

## Staff workflow

1. Open `/crm/inventory/`, edit the exact product, then **Packs & variants → Add pack**.
2. Enter exact name, SKU, prices and verified net quantity/unit. Leave quantity/unit blank if unknown.
3. For the same formula in different sizes, use the same comparison-group text. Different formula/flavour/strength must not share a group.
4. Assign an exact photo from this product's active library. Save, then **Adjust stock** to record opening units with a reason.
5. Use **Photo library → Manage photo** for ordering and recoverable removal/restore.

## Validation and visual review

Final verification: **133 tests passed with all browser suites enabled**, including the new nine-width variant journey. Django system checks and migration-drift checks pass. Legacy checkout browser selectors were updated to distinguish Add to Cart from the new Buy now action; the entire suite was rerun successfully afterward.

Live reference inspected: https://suryavets.com/products/matisse-chicken-and-rice . Local equivalent: http://127.0.0.1:8007/product/matisse-chicken-and-rice/ . Compared at 390px; local image/title spacing was reduced after comparison. Green, white, gold accents and contained packaging retained. This is a requested buying-UX improvement, not a claim of pixel-for-pixel parity.

Dedicated disposable multi-pack fixtures test widths 320, 360, 375, 390, 412, 430, 768, 1024 and 1440. Browser checks exercise gallery/pack-specific images, selected states, MRP, discounts, both savings displays, unit price, Best value, disabled stock, quantity, exact cart sizes, separate lines, cart quantity update, keyboard choice and Buy now. Screenshots of 320/390/1440 layouts are saved under the scratch workspace's `variant-verification/`. Colored test images are fixtures only, not product packaging assigned to the catalog.

No sticky purchase bar was introduced: a normal prominent purchase section avoids covering support controls or page content. No fake ratings, taxes, discounts, images or nutrition were added.

The post-migration comparison against the pre-change backup found zero differences in existing product/variant names, SKUs, prices and stock, and zero differences in historical order-line snapshots. All 2,619 previously migrated local image files remain referenced.

## Commands

```powershell
cd C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py audit_product_media --report tmp/PRODUCT_IMAGE_AUDIT.csv
```

Browser test classes require `SURYA_BROWSER_NODE`, `SURYA_PLAYWRIGHT_MODULE` and `SURYA_BROWSER_EXECUTABLE`; without those, normal test runs explicitly skip browser suites. Existing development server remains on port 8007.

## Changed files

Models/migration: `shop/models.py`, `shop/migrations/0010_variant_buying.py`.

Commerce: `shop/services/variants.py`, `pricing.py`, `cart.py`, `checkout.py`; `shop/catalog_views.py`, `views.py`, `templatetags/shop_filters.py`.

CRM/import/media: `shop/crm_catalog_forms.py`, `crm_catalog_views.py`, `crm_views.py`, `crm_urls.py`, `admin.py`, `services/product_media.py`, `management/commands/import_shopify_products.py`, `audit_product_media.py`.

Presentation: `shop/templates/includes/product_buying.html`, `product_card.html`; `catalog/product_detail.html`, `base_shared.html`, `basket.html`; CRM inventory/product/variant/image templates; `shop/static/css/buying.css`, `shop/static/js/catalog.js`.

Tests: `shop/test_variant_buying.py`, `test_variant_browser.py`, `variant_browser_test.cjs`, and updated pricing/CRM/checkout browser regression tests.

## Remaining data / launch requirements

Approve real multi-pack product families before reorganizing separate imported handles. Populate exact pack quantities, comparison groups, stock and images through CRM or a reviewed migration mapping. Current real catalog still has zero multi-variant products; no test products were added to it.

Acquire the 4,342 missing original product images, reconcile duplicate SKUs and verify imported stock before launch. Persistent production media, online payment integration and production cutover remain separate phases. Shopify/DNS/Render were not changed.

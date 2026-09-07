# Product, variant, image and nutrition audit

Audited 7–8 September 2026 against the existing project at `C:/Users/danyb/Desktop/suryavets-django` (not a new project). Sources are the two supplied `products_export_1 (1).zip` and `products_export_2 (1).zip` files. Live reference: https://suryavets.com/.

## Architecture findings requested in the attached brief

1. **Product:** UUID identity, unique slug, SKU, brand, primary category and collections, exact Decimal prices, stock/tracking and active/featured flags already exist. These were preserved.
2. **Variants:** ProductVariant exists with a flexible display name, SKU, weight text, exact prices, active state and stock. Normalized quantity/unit, display order and a variant-specific image relationship are not yet implemented.
3. **Cart:** CartItem references both Product and ProductVariant; product/variant form part of the line identity. Existing session carts and quantity handling were retained.
4. **Orders:** OrderItem snapshots product name, variant name, SKU, unit price and quantity. Checkout locks/rechecks prices and stock and writes a stock ledger. Product edits do not rewrite those snapshots.
5. **Images:** ProductImage has a product FK, image file, original source URL, alt text, display order and primary flag. Initially all 2,619 image rows used Shopify CDN URLs; none had a local file.
6. **Importer:** Existing importer groups rows by exact Shopify handle and variants by option name, rejects conflicting price/SKU rows, imports Image Src references and retains stock-overwrite guards. The new media-only command does not run full product import and never updates prices/stock.
7. **Image coverage before migration:** 6,697 products; 4,342 with no image, 2,145 with one image and 210 with multiple images. The supplied exports have exactly 2,355 handles with images, so missing photos are not simply unimported rows.
8. **Multiple variants:** 6,677 variants in total, but zero products with multiple variants in the database or supplied exports. Pack sizes are represented by separate handles. Do not merge them by similar names.
9. **Schema changes in this pass:** Optional ingredients/nutrition/source/review fields on Product, plus a thumbnail file and verification metadata on ProductImage. Migration 0009 is additive. Future variant work should add optional Decimal quantity, controlled unit and comparison-group fields, display order and same-product image mapping, with explicit approved family mappings before any regrouping.
10. **Data risks:** Incorrect pack grouping, copying another size's packaging, unverified nutritional statements, stale exports overwriting operational stock, broken CDN references and future ephemeral production media. None is solved by substituting generic imagery or merging similar names.

## Implemented in this pass

- `audit_product_media` exports a CSV covering every product: image count, missing/failed/unchecked status, duplicate references, sources, local file coverage, variant names and nutrition review state. Spreadsheet-formula prefixes in product strings are escaped by the application exporter.
- With `--apply --sources`, exact-handle export image references can be appended without replacing staff uploads. Existing references are deduplicated per product by source path. Existing content/approved nutrition is not overwritten.
- Explicit Ingredients, Composition, Guaranteed Analysis and similar labelled sections are staged as **unverified drafts**. No numerical nutrient estimates or feeding/dosage recommendations are generated. A candidate mention is not proof of a reliable label. 1,650 products yielded ingredients/composition/nutrition drafts; none were automatically approved.
- CRM has Missing images, Failed image checks and Nutrition awaiting review filters. Editors show IMAGE REQUIRED and nutrition draft notices. Managers can enter a source and approve reviewed content for public display.
- Available referenced product images can be downloaded to configured Django media storage, preserving source URLs. CDN host and redirects are restricted; HTTPS certificate/hostname verification stays enabled. On this Windows setup, native certificate validation via [Truststore](https://truststore.readthedocs.io/en/stable/index.html) resolved the initial TLS verification failure.
- Main images are optimized WebP up to 1,400 px and thumbnails up to 360 px, retaining aspect ratio. Product cards and gallery thumbnails use the smaller files. Images with errors remain flagged; a timeout is CHECK FAILED, not falsely labelled a confirmed 404.
- Reusable gallery has named keyboard-accessible buttons, selected states and lazy thumbnails. No random packaging, AI packaging or inferred variant photo assignments.

## Limits and remaining phases

**This is not completion of the attached variant/buying-experience brief.** Remaining work includes normalized units, trustworthy comparison groups and savings/Best Value calculations, variant creation/disable/reorder and image assignment, image reorder/removal UI, broader buying-area redesign, and full live/mobile visual comparison. The current separate products were not combined.

All 4,342 products without export image references need verified assets from the owner/manufacturer or a newer export. The gallery does not manufacture a product image for them. Additional images beyond the 210 existing multi-image products can only be added when correct source assets are supplied or verified.

Nutrition review is a product-label/content review, not veterinary medical advice. Source descriptions can be outdated or inaccurate; check the exact current pack/manufacturer before approving them. This pass leaves existing descriptions untouched.

Local files currently live under `media/products/` and `media/products/thumbnails/` through Django storage. This does **not** deploy them to Render or solve production persistence. Use external persistent media storage before cutover. Original Shopify stays live.

## Verification

Final migration result: all **2,619 available image references** now have local optimized images and thumbnails, covering **2,355 products**. Nine initial timeouts succeeded on retry; zero failed checks remain. The final CSV contains all 6,697 products and flags the 4,342 products without source images. No new image references were found beyond the existing export-backed gallery images.

Full suite: 123 tests passed with all five browser suites enabled. New tests cover conservative extraction, hidden drafts, file-host restrictions, image resizing, resumable migration, source/stock preservation, failure classification and CRM filters. Gallery interaction, loaded images, selected state and minimum tap sizes checked at 320, 360, 375, 390, 412, 430, 768, 1024 and 1440 px. Desktop and 320 px screenshots reviewed. This is gallery verification, not certification of the full future variant experience.

A before/after comparison found one local checkout during this work: one product/variant changed from one unit to zero, matched by a new checkout ledger event. It was preserved. Product and variant prices were unchanged; the migration does not reset operational stock.

## Commands and files

```powershell
cd C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py audit_product_media --report tmp/PRODUCT_IMAGE_AUDIT.csv
# Resume only missing local image files. Already migrated images are skipped.
.\.venv\Scripts\python.exe manage.py audit_product_media --apply --download --report tmp/PRODUCT_IMAGE_AUDIT.csv
.\.venv\Scripts\python.exe manage.py test
```

The source-data staging command adds `--sources` followed by the exact two supplied export paths. Run it only on authorized exports, with `--apply` to stage content. No need to rerun full product import.

Changed code: `models.py`, migration `0009_product_media_nutrition.py`, `services/product_media.py`, management command `audit_product_media.py`, `crm_catalog_forms.py`, `crm_views.py`, `admin.py`, product/gallery/card and CRM templates, gallery JS/CSS, `requirements.txt`, and media unit/browser tests. All are inside the existing `shop` app except requirements/docs.

Backup: `tmp/pre-media-nutrition-20260907-235935.sqlite3`. Source checkpoint before changes: `codex/checkpoint-before-product-media-20260907`. Detailed current coverage: `tmp/PRODUCT_IMAGE_AUDIT.csv`.

# Trusted image recovery — 1 October 2026

## Direct answers

**A. Previously missing 4,342 products that now have a trusted real image: 0.**

**B. Products still lacking usable local artwork: 4,342.** These remain on placeholders where their packs have no image. Three additional pre-existing packaging discrepancies remain flagged for manual review; file coverage is not a certification that every existing package is correct.

**C. Were uncertain images auto-assigned? NO.**

One deterministic **variant-image link** was recovered: DROOLS ADULT CHIC & VEG DRY FOOD (XL), 20KG, SKU `'8941`, variant `13365`, now points to its existing source-owned image `5260`. The product already owned the file, so it is not counted as a newly illustrated product. The pack visibly says 20 kg. No new packaging, stock, price, SKU, title, family grouping or order data was created or changed.

## Before / after

| Metric | Before | After |
|---|---:|---:|
| Total products | 6,697 | 6,697 |
| Canonical families | 6,420 | 6,420 |
| Products with usable local image files | 2,355 | 2,355 |
| Products missing usable local image files | 4,342 | 4,342 |
| Families with local image coverage | 2,296 | 2,296 |
| Variants with source-owned local pack imagery | 2,341 | 2,342 |
| Explicit variant-image foreign keys with usable files | 152 | 153 |
| Newly recovered image files | 0 | 0 |
| Restored exact variant assignments | 0 | 1 |
| New family-level coverage | 0 | 0 |

The larger variant-coverage number includes existing single-pack product-image relationships. It is deliberately separate from explicit variant-image pointers. Placeholders count as neither real images nor recovered images.

## Sources inspected

- All 2,620 ProductImage records, active/archived relationships, stored source URLs, variant assignments and canonical families.
- Local `media/products`, thumbnails and other local media assets. All 2,620 recorded original files and available thumbnails passed file checks in this run.
- `catalog_exports/images` and its banner/category/logo assets; cached homepage/template and earlier import/media code were inspected. These do not supply additional missing exact-product images.
- Both owner-supplied Shopify product ZIPs: 2,619 source image-row references. Exact handles, titles/vendors, SKUs and options were compared. The supplied exports do not provide authoritative Shopify numeric product/variant IDs; none were invented.
- `product_image_coverage.csv`, `image_recovery_summary.md`, `variant_pack_review.csv`, `pack_image_observations.json`, current pack-identity evidence and archived variant-pack reports. The index records 9,604 historical artwork references as evidence, not new approval.
- 13 unassigned files were inventoried. They comprise category/banner/logo assets and non-image files, not an orphaned product-photo library. Filename-only evidence was never used to assign a product.
- No OCR, Google Images, third-party store images, AI packaging, Shopify write, payment operation, deployment or DNS operation.

## Candidate classification

The validated pre-apply run contained 6,698 product/variant rows:

- 2,354 existing covered rows, preserved.
- 1 HIGH exact recovery candidate, applied after validation and visual inspection.
- 1 MEDIUM unresolved mapping: Drools extra variant `13377`, named like the product rather than a pack, with blank SKU. It was not changed or assigned a 20KG image.
- 4,342 rows without trusted source artwork.
- Three existing rows additionally have LOW-confidence critical packaging discrepancies. They remain marked for review, not approved by this phase.
- Zero approved family fallbacks were activated automatically.

The idempotency dry-run after recovery finds **zero new exact recovery candidates**. Its `applied_count: 0` means that dry-run itself changed nothing; the cumulative applied ledger retains the one completed recovery.

### Duplicates

84 identical-byte image groups were found, 67 spanning more than one current canonical family. Shared bytes alone do not prove an error, so these are informational duplicate groups, not automatic rejection or reassignment. Existing critical identity evidence remains separate. No files were deleted or deduplicated.

## Recovery workflow

`recover_product_images` defaults to dry-run. It validates stored files through Django storage APIs, with supported extensions/types, non-empty bounded content, dimensions, Pillow verification and SHA-256 hashes. Source downloads, when needed for a validated HIGH candidate, reuse the existing allowlisted Shopify downloader and optimized image encoder. This actual recovery required no download.

Apply requires `--validated-plan`. A fresh source/file signature and catalog fingerprint must match the reviewed plan. Existing explicit assignments, rejected images, conflicting pack evidence and uncertain matches are not replaced. A timestamped JSON relationship backup is written before apply. Every recovery is recorded in a timestamped CSV, the cumulative CSV and an internal CRM activity event. The cumulative ledger survives repeat dry-runs and empty apply runs.

The apply process verifies unchanged business-table fingerprints and unchanged variant fields other than `image_id`. Prices, stock, product identity and existing orders were preserved. No image files were overwritten or deleted.

Checkpoint branch: `codex/trusted-image-recovery-20261001`, pointing to pre-change commit `e4f69b6`. Previously untracked files were preserved, not swept into a commit.

## Rendering and CRM

- Shared resolver uses valid active source-owned exact-pack images first. Recorded validation failures return no public image URL. No filesystem probe is performed by the card resolver.
- Simple-product primary images are filtered through the same validation-aware helper.
- New optional `ProductImage.family_reference_for` and approval-evidence fields allow authorized staff to approve a generic image only for its own active canonical family. Approval requires a reason/evidence and is recorded in staff history. It never populates `ProductVariant.image` automatically.
- Cards display approved family references only when exact imagery is absent and show **“Family reference image · selected size may differ.”** Changing variants preserves that distinction.
- Product detail retains the exact-pack placeholder and can show a separately labeled generic reference. Generic artwork is not inserted into the exact-pack gallery or order image snapshot.
- Cart and future order snapshots continue using exact-pack imagery. Historical order image references were not rewritten. Wishlist, related products, search and collections reuse the shared card component; Buy Again retains the exact selected variant.
- Existing manually curated homepage policy still requires acceptable exact-pack artwork. It was not weakened to populate missing merchandising slots.
- CRM inventory adds Approved family artwork alongside missing, placeholder, review and recovered filters. The recovered filter reads the recovery ledger; image-edit pages show imported source, storage reference and validation status. Audit-derived filters are snapshots and require refresh after edits.
- Migration `0019_trusted_family_artwork` is additive and was applied locally. Existing approval fields default blank; no family approval was fabricated.

## Reports

- `catalog_review/image_recovery_candidates.csv`
- `catalog_review/image_recovery_unresolved.csv`
- `catalog_review/image_recovery_applied.csv` — one HIGH assignment
- `catalog_review/image_recovery_index.json` — source, file, mapping, duplicate and historical evidence
- `catalog_review/image-recovery-backup-*.json` — original relationships/fingerprints
- `catalog_review/image-recovery-applied-*.csv` — immutable per-run logs

The older September image-coverage files remain historical baselines; the new recovery index and this report describe the current result.

## Tests and performance

- Full suite: **348 discovered, successful with 14 optional skips**.
- Eleven new recovery tests cover HIGH recovery, LOW rejection, no overwrite, stale-plan rejection, exact-over-family precedence, unrelated-family isolation, broken-path fallback, dry-run immutability, persistent apply logs, price/stock/identity preservation, staff evidence validation and query behavior.
- Focused recovery suite passed again after cumulative-log changes.
- Explicit homepage/browser suite passed at 320, 360, 375, 390, 412, 430, 768, 1024 and 1440px.
- Explicit purchase-safety browser test passed on desktop/mobile, including product detail, disabled invalid packs, cart and checkout guards.
- Real local recovered Drools detail verified at 390 and 1440px: expected image loaded, no JavaScript errors, no horizontal overflow. No real cart/order write was used for that check.
- `manage.py check` passed; migration drift check reports no changes.
- Nine prefetched cards resolve with **zero additional SQL queries**; a test forbids storage probes during card rendering.
- Dog category remains 14 queries, search 12, price-sorted category 14. Sample repeated local timings: 0.353s / 0.285s / 0.506s respectively. These are local observations, not a claimed speed increase. Expensive file validation/indexing runs only in the audit command.

## Main changed files

`shop/services/image_recovery.py`, `shop/management/commands/recover_product_images.py`, `shop/services/pack_images.py`, `shop/services/product_cards.py`, `shop/services/image_coverage_snapshot.py`, `shop/services/merchandising.py`, `shop/models.py`, `shop/admin.py`, `shop/migrations/0019_trusted_family_artwork.py`, `shop/catalog_views.py`, `shop/crm_views.py`, `shop/crm_catalog_forms.py`, `shop/crm_catalog_views.py`, shared card/variant/gallery templates, CRM image/inventory templates, `shop/static/js/catalog.js`, `shop/static/js/product-cards.js`, `shop/static/css/image-polish.css`, `shop/test_image_recovery.py` and the reports above.

## Commands

```powershell
Set-Location C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe manage.py recover_product_images --dry-run
.\.venv\Scripts\python.exe manage.py test shop.test_image_recovery --noinput
.\.venv\Scripts\python.exe manage.py check
```

Only after inspecting a fresh dry-run, apply its deterministic candidates with:

```powershell
.\.venv\Scripts\python.exe manage.py recover_product_images --apply --validated-plan catalog_review/image_recovery_index.json
```

The command reuses the known export paths recorded by the previous audit, or accepts explicit `--sources`. Currently there are no further HIGH recovery candidates. More missing-product coverage requires new owner/manufacturer-approved artwork or a trustworthy new source mapping. The extra Drools option and the three critical discrepancies still need staff decisions; no size, SKU or price was altered to make an image fit.

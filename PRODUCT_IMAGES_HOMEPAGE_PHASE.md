# Product images and shopping presentation

## Outcome and limits

Implemented a safe presentation improvement and catalog-wide coverage audit. This is **not a claim that every product now has verified artwork or that the whole requested phase is complete**.

**A. Are all products display-safe?** Shared product cards and product galleries now use neutral SuryaVets placeholders and handle failed image loads. Sampled homepage, dog collection and product-detail pages had no visible broken images or horizontal overflow at nine widths. This does not certify every URL, every legacy surface, or image identity. Three known packaging discrepancies remain for review.

**B. Were only verified images auto-assigned?** No images were assigned. No safe new mapping was found in the audit. Existing relationships, stock, prices and order data were preserved.

**C. Is the homepage polished in the Boww & Meow direction?** The existing six-pet discovery, needs, brand, hero, trust, newsletter and navigation architecture was retained. Shared cards now use a compact Choose size dialog with a mobile bottom sheet. Boww & Meow's local card template informed the image/brand/title/size/price/CTA hierarchy; SuryaVets colors and assets remain. Real homepage merchandising still needs explicit staff selections. No invented best sellers were populated. The entire requested homepage redesign is not claimed complete.

## Audit and safety

- Existing project inspected at `C:\Users\danyb\Desktop\suryavets-django`.
- Read-only public reference inspected at https://suryavets.com/ and local Boww & Meow card markup inspected at `PetCareCRM/store/templates/store/includes/home_product_card.html`.
- Django check passed before editing.
- Existing working changes preserved. Tracked checkpoint: `codex/image-polish-checkpoint-20260929`, commit `e36f61b8c046239b48f49ff50b574468ce493b8d`. It does not include previously untracked files; those were preserved in place.
- No schema change. No deployment, Shopify operation, DNS change, payment operation or actual customer notification.

## Coverage

| Metric | Before | After |
|---|---:|---:|
| Products with usable local image files | 2,355 | 2,355 |
| Products without usable local image files | 4,342 | 4,342 |
| Canonical families with local image coverage | 2,296 | 2,296 |
| Variants with source-owned local pack images | 2,341 | 2,341 |
| Images recovered | 0 | 0 |

There are 6,697 products and 6,420 canonical families. Coverage counts do not certify image identity. Two unresolved mappings and three known critical visual discrepancies remain unchanged. See `catalog_review/image_recovery_summary.md` and the 6,698-row `catalog_review/product_image_coverage.csv` for details.

## Implemented presentation

- Shared branded, non-packaging placeholder: “Image coming soon / Photo for this exact pack.”
- Card and main-gallery image errors switch to the placeholder, including already-failed cached loads.
- Clean contained image area; no packaging crop or stretch. Existing 360px thumbnail and optimized full-image pipeline retained.
- Multi-size cards have Choose size, price/MRP and selected-pack context. Existing form moves into one native dialog, avoiding duplicate variant inputs.
- Mobile dialog attaches to the bottom; desktop uses a centered dialog. Native focus containment, Escape, close button, outside click and focus restoration.
- Size choices show their price and keep invalid/unavailable options disabled. Existing server-side purchase validation remains authoritative.
- Single variants retain direct Add to Cart. Quantity remains one on cards; cart controls remain the place to adjust it.
- Touch swipe changes only visible thumbnails in the selected pack's gallery.
- No unverified Best Value claims added. No automatic promotion of imported best-seller flags.
- CRM adds read-only audit filters for placeholder packs, review-required images and recovered images, while reusing existing editing tools.

## Performance

Five local Django requests per version, same database, checkpoint versions of changed templates versus current templates:

| Version | Median seconds | Queries |
|---|---:|---:|
| Checkpoint | 0.2674 | 9 |
| Current | 0.2617 | 9 |

Treat this as unchanged performance, not a material speed claim. The actual homepage has no manually selected merchandise, so these timings do not represent a fully curated product homepage. The isolated browser test covers bounded curated sections with fixture products. Frontend network-idle screenshot timings are not server benchmarks. External network requests were blocked during automated visual checks.

## Verification

- Full suite: 337 discovered, passed with 14 optional skips.
- Additional explicit browser test passed at 320, 360, 375, 390, 412, 430, 768, 1024 and 1440px.
- Browser assertions: layout, trust row, categories, navigation, slider, tab switching, dialog opening/closing/focus, failed-image fallback, selected 6KG pack added at current price in an isolated test database.
- 27 real-local read-only page checks: homepage, dog collection and product detail at nine widths. All HTTP 200, no horizontal overflow and no visible broken images detected.
- Screenshots captured at 390, 430 and 1440px. Inspected mobile product detail, shared cards and size sheet. Fixture artwork exists only in tests, never catalog data.
- Three new image-audit tests: no catalog mutation, missing placeholder, unrelated image rejected. Existing pack identity and merchandising tests retained.
- `manage.py check`: passed. `makemigrations --check --dry-run`: no changes.
- Local preview restarted to clear cached templates.

## Changed application files

- `shop/management/commands/audit_image_coverage.py`
- `shop/management/commands/profile_homepage.py`
- `shop/services/image_coverage_snapshot.py`
- `shop/crm_views.py`
- `shop/templates/crm/catalog_inventory.html`
- `shop/templates/base_shared.html`
- `shop/templates/includes/product_card_v2.html`
- `shop/templates/includes/card_variant.html`
- `shop/templates/includes/product_gallery.html`
- `shop/static/css/image-polish.css`
- `shop/static/js/product-cards.js`
- `shop/static/js/catalog.js`
- `shop/test_image_coverage.py`
- `shop/home_discovery_browser_test.cjs`
- This report, image summary, JSON snapshot and CSV coverage report.

## Remaining work

1. Obtain owner/manufacturer-approved exact-pack images for uncovered products. No trusted missing images can be invented.
2. Review two ambiguous mappings and the three existing critical pack discrepancies.
3. Implement explicit audited family-image approval before enabling a labeled cross-size family fallback. Currently exact-pack safety intentionally wins over coverage.
4. Select genuinely approved homepage merchandise in the existing CRM workflow; empty sections remain hidden rather than filled with arbitrary rows.
5. A broader homepage redesign and all-catalog visual/identity certification remain beyond this verified increment. Existing sections were preserved, not completely rebuilt.

To run the focused checks:

```powershell
Set-Location C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_image_coverage shop.test_pack_identity shop.test_merchandising shop.test_home_discovery --noinput
.\.venv\Scripts\python.exe manage.py profile_homepage
```

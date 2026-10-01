# Phase 3: pack / variant identity review

Date: 29 September 2026. Scope: local catalog review and exact-pack presentation safety. **Ready for manual review, not launch-ready.** No merchandising work, deployment, Shopify modification, payment configuration, or stock changes were performed.

## Results

| Measure | Count |
|---|---:|
| Products reviewed | 6,697 |
| Canonical families reviewed | 6,420 |
| Existing linked multi-product families | 221 |
| Variants reviewed | 6,678 |
| Report rows, including simple products | 6,698 |
| Rows with conflicts/review flags | 5,335 |
| Individual issue occurrences (overlapping) | 6,057 |
| P0: highest purchase-impact review priority | 3 |
| P1: identity/duplicate/source review | 1,129 |
| P2: formatting-only priority | 4,203 |
| Safe formatting fixes applied | 0 |
| Non-formatting flagged rows left unchanged (P0 + P1) | 1,132 |
| Wrong-grouping families detected automatically | 0 |
| Wrong-image candidates | 3 |
| Images visually spot-checked | 4 |
| Catalog/source records modified | 0 |

Priority counts count each row once at its highest priority. Issue-type totals overlap: 996 possible split-product rows, 70 possible duplicate rows, 69 slug/variant mismatches, four title/variant mismatches, two uncertain SKU-label rows, two ambiguous multi-pack image rows, 15 vendor differences, one unconfirmed source identity, and 4,895 formatting occurrences. These are review candidates, not authorization to merge or correct data. Zero detected wrong groupings is not a human certification of all families.

## Existing architecture and audit

Products retain their original UUIDs. `Product.variant_family` links a source product to a canonical product; `family_name` supplies presentation naming. Original ProductVariant, cart, stock and order identities remain attached to their source products. Cards group existing confirmed links; no grouping utility was applied in this phase.

The Shopify importer maps Handle to Product.slug and matches variants by product/options with SKU evidence. There is no separate Shopify-handle field. Source matching therefore uses exact exported handle-to-current-slug matches; unmatched records are not guessed. Both supplied product export ZIPs are used, with source member/record references and SHA-256 provenance. Historical exports are evidence, not proof of today's physical inventory or approval of a correction.

Review checks include title/slug versus parsed pack, SKU collisions, source-handle identity, units, formulation/vendor/type/prescription/species differences, family graph consistency, duplicate/split candidates and image ownership/assignment. Name similarity alone never authorizes grouping. Dose concentrations are excluded from pack parsing. Unknown unit abbreviations remain uncertain rather than being declared different sizes.

## Important image findings

| Product | Current variant | Visible artwork | Result |
|---|---|---|---|
| NEOROF INJ (S) | 10ML | 20 mL | P0: owner must confirm pack/artwork |
| CICLOPET SYRUP (S) | 25ML | 50 ml | P0: owner must confirm pack/artwork |
| INJEK 10MG INJ | 1ML | 1 mg/0.5 ml; five 0.5 ml ampoules | P0: strength and pack identity review |
| HESTACEF CV DRY SYRUP | 30ML | 30 ml | Filename was misleading; observed pack matches |

Observations are in `catalog_review/pack_image_observations.json` and only apply when actual local image bytes match the recorded SHA-256. This avoids carrying approval across a replacement image. Images were not replaced or reassigned. Only these four images were visually inspected; other artwork remains IMAGE REVIEW REQUIRED or missing/ambiguous as indicated. The report is not a batch visual certification.

No automatic holds or approval decisions were written. A flagged product can still be purchasable under the existing safety rules until an authorized owner reviews/holds/corrects it. **Review the three P0 records before any launch.**

## Implemented behavior fixes

- Explicit Django variant query selection is preserved; malformed, missing, foreign or conflicting variant IDs cannot silently select another pack.
- An unavailable source-member pack stays unavailable rather than silently substituting an available sibling.
- Switching packs updates the URL, exact price, savings, stock, submitted variant ID and allowed gallery images. Reload retains the selected pack. Query IDs are local Django variant IDs, not Shopify variant IDs.
- Cards, detail pages, carts and future order image snapshots share exact source-product image ownership rules. Invalid/foreign/inactive assignments and unassigned multi-pack artwork show a missing-image state rather than borrowing sibling packaging.
- Existing historical order snapshots were not rewritten. Valid existing family links and Phase 2 purchase validation remain in place.
- Staff inventory now has a Pack Identity Review filter and per-product evidence. It reads a dated report snapshot and does not silently approve products or bypass CRM authorization.

CRM entry points after staff login:

- http://127.0.0.1:8000/crm/inventory/?identity=P0
- http://127.0.0.1:8000/crm/inventory/?identity=review

## Deliverables and preservation

- `catalog_review/variant_pack_review.csv`: complete row-level identity inventory.
- `catalog_review/pack_identity_priority.csv`: flagged rows, highest risk first.
- `catalog_review/pack_identity_manifest.json`: counts, source hashes, limitations, before/after database fingerprints.
- `catalog_review/pack_identity_crm.json`: staff-only review snapshot consumed by CRM.
- `catalog_review/pack_image_observations.json`: hash-bound visual evidence.

CSV includes the requested identity, family, size/unit, image, confidence, recommended action and source fields, plus review status, evidence details and owner decision/evidence columns. UTF-8 BOM supports spreadsheet opening; formula-like text is escaped. Import SKU columns as text to retain leading zeros. Priority reflects risk; confidence describes evidence for the flag, not certainty of a replacement value.

Previous reports were copied into `catalog_review/identity-history-*` before replacement. The older Phase 1 pack report is historical; this report supersedes its pack-identity analysis only. Owner notes in archived versions remain available; regeneration is not an approval workflow.

Report generation uses a SELECT-only database guard and compares complete before/after fingerprints for products, variants, images, categories, brands, relations, inventory history, orders/order items and review events. All matched. No source catalog fields, stock, prices, inventory history or existing orders changed. No migrations are required.

Tracked-work checkpoint: branch `codex/pack-identity-checkpoint-20260929`, commit `63ee4a2a308b4707bf3327840f3abf949d80d611`. Pre-existing untracked work was preserved, not reset or removed.

## Files changed in this phase

New code:

- `shop/services/pack_identity.py`
- `shop/services/pack_images.py`
- `shop/services/pack_review_snapshot.py`
- `shop/management/commands/audit_pack_identity.py`
- `shop/test_pack_identity.py`

Existing code extended:

- `shop/catalog_views.py`
- `shop/models.py` (CartItem image presentation only; no schema change)
- `shop/services/checkout.py` (future exact-pack image snapshot only)
- `shop/services/product_cards.py`
- `shop/services/variants.py`
- `shop/crm_views.py`
- `shop/crm_catalog_review.py`
- `shop/static/js/catalog.js`
- `shop/templates/includes/product_buying.html`
- `shop/templates/includes/product_gallery.html`
- `shop/templates/crm/catalog_inventory.html`
- `shop/templates/crm/catalog_review.html`
- `shop/variant_browser_test.cjs`

Also the five deliverables above, archived reports and this document. Other existing dirty files are not phase-3 changes.

## Verification

- Full Django suite: 309 tests, OK, 14 skipped (optional integration/browser coverage is not claimed by this run).
- Final targeted regression after cart/checkout image adjustment: 71 tests, all passed.
- Explicit browser runs: three variant/purchase-safety tests passed; subsequent updated variant URL/reload run: two tests passed.
- Variant browser coverage includes 320, 360, 375, 390, 412, 430, 768, 1024 and 1440 px using isolated fixture products. These verify behavior/layout, not the artwork of every real product.
- `manage.py check`: passed.
- `manage.py makemigrations --check --dry-run`: no changes detected.
- `git diff --check`: passed (line-ending warnings only).
- Independent spreadsheet import/count validation: 6,698 full rows and 5,335 prioritized rows; severity totals agree with the manifest.

Repeat checks from the project directory:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_pack_identity shop.test_checkout shop.test_purchase_safety shop.test_catalog_performance --noinput
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Regenerate the read-only report when evidence changes:

```powershell
.\.venv\Scripts\python.exe manage.py audit_pack_identity --sources "C:\Users\danyb\Downloads\products_export_1 (1).zip" "C:\Users\danyb\Downloads\products_export_2 (1).zip" --image-observations catalog_review/pack_image_observations.json --archive-existing
```

## Next manual review, not merchandising

1. Confirm the three P0 products against supplier/manufacturer packaging and the original source. Record the exact correction or hold decision; do not guess replacements.
2. Review SKU abbreviations, title/slug discrepancies and ambiguous image assignments with source evidence. Do not change public slugs without a later redirect plan.
3. Review split/duplicate candidates using confirmed formulation, species, age stage, strength and source relationships. Approve family links individually; similar names are insufficient.

**Answer: yes, the evidence and controls are safe enough to begin manual pack/family review. No, catalog identity and physical stock are not yet certified for launch.**

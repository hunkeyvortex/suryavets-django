# Phase 4 — manual homepage merchandising

29 September 2026 · Local project: `C:\Users\danyb\Desktop\suryavets-django`

**Homepage merchandising now requires explicit manual curation. It no longer trusts imported flags on their own. No final products were selected automatically.**

## Counts

| Measure | Count |
|---|---:|
| Previous imported Best Seller flags | 6,457 |
| Previous imported Featured flags | 6,457 |
| New manually selected families | 0 |
| Curated and eligible families | 0 |
| Product cards currently displayed in homepage merchandising | 0 |
| Active canonical families passing current eligibility checks, available for owner selection | 2,239 |
| Excluded: purchase blocked / no purchasable variant | 112 |
| Excluded: missing suitable exact-pack image | 4,066 |
| Excluded: unresolved P0 identity finding | 3 |
| Inactive canonical families | 0 |

Exclusion reasons are mutually exclusive first-failure categories, not independent overlapping counts. Eligibility is not identity approval, physical-stock verification or evidence of sales performance. Image checks enforce assignment, active status, recorded errors, local-file presence or HTTPS source reference; they do not certify remote URL uptime or packaging content. P0 evidence comes from the Phase 3 snapshot. Missing evidence fails closed. Corrections must be reviewed and that report regenerated before previously flagged families can be promoted.

## Existing architecture reused

- Product `is_bestseller` and `is_featured` flags: retained, not bulk-reset.
- Existing canonical `variant_family` relationships: one card per canonical family; no grouping changes.
- Existing purchasing policy, card component, pack-image selection, navigation and home template.
- Existing staff permissions and CRM activity history for audit records.
- Existing main Best Sellers / Featured fallback section and dog/cat Mealtime favourites tabs. No new marketing sections were invented.

## Additive schema

Migration `shop/0017_manual_homepage_merchandising` adds:

- `merchandising_active`, default false: explicit manual homepage gate, independent of store publication.
- `merchandising_rank`, default 100: lower first, then stable name/primary-key ordering.
- `is_new_arrival`, default false.
- `is_promotional`, default false.

New Arrival / Promotional can be classified in CRM/admin but do not create new homepage sections in this phase. Best Seller and Featured keep their existing homepage behavior, with the new gate and safety checks. Food tabs also require manual selection; no automatic category picks remain.

Migration was applied locally. Hashes of all pre-existing Product fields, ProductVariant, ProductImage, InventoryMovement, Order and OrderItem rows matched before/after. Stock, prices, image assignments, existing orders and catalog identities were preserved. No imports were run on the real catalog. No payment changes, deployment or Shopify modifications occurred.

Tracked-code checkpoint: `codex/merchandising-checkpoint-20260929`, commit `8463841ea4f9a8b1807e07ecc025131eb4727ff3`. Existing untracked files were preserved.

## Homepage behavior

Only explicitly selected, active canonical families with a purchasable positive-price variant and suitable selected-pack image pass. Purchase holds, zero-price-only families, inactive roots, unresolved P0 evidence and unavailable selected artwork exclude the family. A valid purchasable sibling can keep its canonical family eligible. Invalid variants retain the existing disabled purchase controls; they are not silently substituted.

Manual rank is authoritative. There is no computed sales ranking or new Best Value claim. The main section defaults to 12 cards, configured once by `HOMEPAGE_MERCHANDISING_LIMIT` in settings and clamped to 1–20. Existing food tabs retain their four-card layout. Empty product sections are hidden rather than filled with automatic fallback products. Hero, category discovery and other existing non-product sections remain.

Later Shopify imports preserve Best Seller / Featured labels for actively curated products; imported flags cannot automatically activate a product. This guard was tested only with isolated fixtures.

## CRM instructions

Open http://127.0.0.1:8000/crm/merchandising/ after staff login. The sidebar links to **Homepage merchandising**.

1. Search for a family and review its evidence/eligibility message.
2. Select one or several families (maximum 50).
3. Set **Curated for homepage**, the desired labels and a rank.
4. Save. This replaces the six merchandising fields for selected families; unchecked labels are cleared. No price/stock/publication fields are accepted.

Reading requires staff status, `access_crm` and `view_product`; saving also requires `change_product`. CSRF protection is used. Every changed selection is recorded with actor and before/after values in CRM activity history. Existing admin Product forms also expose these fields.

Filters: Curated Best Seller, Featured, New Arrival, Promotional, Homepage Eligible, Missing Image, Blocked from Purchase. Dynamic safety/image filters require searches narrowed to at most 200 families, with an explicit message otherwise, to avoid slow full-catalog scans. Normal label filters and search are paginated database queries. Eligibility is checked live and does not approve a product.

## Files changed

New:

- `shop/services/merchandising.py`
- `shop/crm_merchandising.py`
- `shop/templates/crm/merchandising.html`
- `shop/migrations/0017_manual_homepage_merchandising.py`
- `shop/test_merchandising.py`
- This report.

Extended:

- `shop/models.py`, `shop/admin.py`, `suryavets/settings.py`
- `shop/services/homepage.py`
- `shop/templates/home_new.html`, `shop/templates/crm/base.html`, `shop/crm_urls.py`
- `shop/management/commands/import_shopify_products.py` (curated-label preservation only)
- `shop/test_home_discovery.py`, `shop/tests.py`
- `shop/test_home_discovery_browser.py`, `shop/home_discovery_browser_test.cjs`

## Verification

- Full regression suite passed after updating the prior test that expected an empty promotional section. Optional integration/browser tests remain skipped in the ordinary suite.
- Final focused merchandising/homepage run: **20 tests passed**, including preservation of curated labels during a later import, missing local artwork, exact family selection, P0 exclusion, rank/limit, no render mutations and CRM permissions/safe bulk updates.
- Explicit homepage browser test passed at **320, 360, 375, 390, 412, 430, 768, 1024 and 1440 px**. Checked page overflow, food-grid columns/tabs, fixed trust boxes, navigation, slider, manually selected card count, variant pricing and selected-pack Add to Cart. Images/products are isolated test fixtures, not new real catalog selections.
- Mobile fixture screenshot inspected for image consistency, price readability, controls and spacing.
- `manage.py check`: passed.
- `manage.py makemigrations --check --dry-run`: no pending changes.
- `git diff --check`: passed, with existing line-ending warnings only.

Repeat from the project directory:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_merchandising shop.test_home_discovery --noinput
```

## Owner/client decision needed

Choose the actual 8–20 intended families (default display limit 12), their labels and rank. Start with products whose identity and artwork have been reviewed. The three P0 products remain excluded. Physical stock remains unverified. No sales-derived popularity is claimed, and the catalog is not launch-ready.

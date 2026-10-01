# Catalog and search performance — 26 September 2026

## Scope and safety

Optimized the existing storefront; no redesign, data reimport, schema migration,
price/stock changes, approval enforcement, Shopify changes or deployment.
Existing uncommitted work was preserved. Before editing, tracked changes were
captured at `codex/catalog-performance-checkpoint-20260926`
(`5ac1a6bf4a598323ac8d3ecf1cca1946720806df`). This reference does not include
untracked files; those were left in place.

## Cause and fix

- Every listing previously calculated correlated family-price subqueries even
  without a price filter/sort. Wide DISTINCT/count queries repeated that work.
- Category and family-search joins multiplied listings, requiring DISTINCT.
- Each request counted the same result twice (view plus paginator).
- The SQLite planner used the low-selectivity active-product index inside price
  and stock subqueries, scanning active products repeatedly for each root.

Changes in `shop/catalog_views.py` and `shop/services/pricing.py`:

- Only build a price expression for price filtering/sorting; use an alias rather
  than projecting prices onto every row. Price sorting does not affect COUNT.
- Use correlated EXISTS for collection membership and family-name/SKU matching.
- Reuse the paginator's cached count. Add a PK tiebreaker for stable pagination.
- Select family IDs through existing PK/family indexes and variants through the
  existing product FK index. Check source activity with a PK-based EXISTS so it
  cannot redirect the planner into a full active-catalog scan.
- Preserve cheapest available active-pack pricing, fallback prices, exact selling
  prices and availability rules. Use decimal division for legacy variant prices.
- Search now also finds the root product's variant SKU, previously omitted.

No cross-request price/stock cache or external search service was introduced.

## Measurements

Existing audit baseline (22 September): Dog collection and `q=royal` search each
exceeded an eight-second HTTP timeout. This is a lower bound, not a measured
completion time. Diagnostic queries this turn also exceeded the imposed query
time budget before optimization; interrupted debug error rendering is not a valid
whole-request latency benchmark.

Read-only Django-client measurements against the imported SQLite catalog after
the fix (response rendering included; not browser asset/image loading):

| Route | Seconds | Matching listings |
| --- | ---: | ---: |
| `/categories/` | 0.45 | 6,420 |
| `/category/dog/` | 0.54 | 4,722 |
| `/category/cat/` | 0.30 | 3,530 |
| `/search/?q=royal` | 0.19–0.30 | 165 |
| Dog, page 2 | 0.27 | 4,722 |
| Dog, price ascending | 0.78 | 4,722 |
| Search royal, price range + availability + descending | 0.58 | 90 |
| Dog, price range + ascending | 1.34 | 3,507 |
| No-result search | 0.16 | 0 |

Restarted local server on port 8000 and verified actual HTTP responses, all 200.
Three sequential samples per route, while the wider test suite was running:

| Route | Seconds (three samples) |
| --- | --- |
| Dog collection | 1.555, 0.999, 1.000 |
| Search royal | 0.836, 1.004, 0.808 |
| Dog, price ascending | 1.049, 1.076, 1.185 |
| Dog, price range + ascending | 1.697, 1.412, 2.210 |

These are local development measurements, not production SLA or load-test claims.
Re-profile on production-like PostgreSQL before deployment. SQL plans confirm
family/variant PK and FK index lookups replace repeated active-product scans.

## Verification

- Django system checks: pass.
- Migration drift check: no changes detected.
- Focused catalog/pricing/family/variant/card tests: 64 passed.
- Added 15 regression tests in `shop/test_catalog_performance.py` for price-query
  avoidance, single COUNT, family prices, disabled packs, stock, decimal/zero
  prices, SKU search, unique listings, stable pagination and prefetched cards.
- Full `manage.py test shop --noinput` with browser tests enabled: **242 passed,
  no skips**, in 402.685 seconds. Tests used an isolated database and mocked
  payment/email providers. Expected mocked failure logs are not real sends.

Files changed for this task: `shop/catalog_views.py`, `shop/services/pricing.py`,
`shop/test_catalog_performance.py`, this report and `SHOPIFY_PARITY_AUDIT.md`.

Repeat from the project directory:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_catalog_performance shop.tests shop.test_pricing shop.test_pack_families shop.test_variant_buying shop.test_product_cards --noinput
```

Other catalog-integrity and launch-readiness findings in `SHOPIFY_PARITY_AUDIT.md`
remain open. Faster pages do not verify supplier stock, product images or prices.

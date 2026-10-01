# Catalog performance — autonomous launch preparation

29 September 2026. Real local dataset: 6,697 products, 6,678 variants. Read-only Django test-client requests against the actual local SQLite database; full HTML rendering included, browser asset/network time excluded. Two sequential requests per URL. Timings are samples, not a production load-test SLA.

| Request | Before seconds (first / repeat) | After seconds (first / repeat) | Queries before → after |
|---|---|---|---|
| `/category/dog/` | 0.292 / 0.221 | 0.355 / 0.255 | 17 → 14 |
| `/search/?q=royal` | 0.216 / 0.207 | 0.247 / 0.250 | 15 → 12 |
| `/category/dog/?sort=price_low` | 0.309 / 0.318 | 0.335 / 0.307 | 17 → 14 |

The historical eight-second problem did **not** reproduce before this phase. Earlier catalog fixes were already present. This phase removes three unnecessary SQL queries per page; wall-clock results are mixed and do not establish a general speedup. SEO metadata/security processing was also added during this phase. Do not present this as an eight-second-to-subsecond optimization.

## Evidence and change

The global `get_featured_products` context processor fetched 12 imported-featured products plus their images/variants even when the current template did not use them. It now returns a lazy value and uses the existing manual-curation service if an older template actually requests it. No catalog membership, price or stock changes.

Before: two repeated image query shapes and two repeated variant query shapes (main page plus unnecessary featured prefetch). After: no repeated SQL shapes in these sampled requests. This was redundant page-wide loading, not a per-card N+1. Existing paginated card prefetches, related category/vendor loading and canonical-family handling remain intact.

Representative slowest SQL after change:

- Dog default: product page selection 89 ms; category membership count 62 ms; category-tree query 33 ms.
- Search: product page selection 79 ms; name/brand/category/SKU search count 56 ms; category query 32 ms.
- Price sort: family-price ordered page selection 142 ms; category count 62 ms; category query 25 ms.

Default browsing/search already avoid family-price subqueries. Price sorting/filtering deliberately uses the existing availability-aware family expression. Counts do not project the expensive price annotation. Canonical-family members and images are prefetched only for the page. No new index or cache was justified by these samples; no stale price/stock cache was introduced.

## Reproduce

```powershell
.\.venv\Scripts\python.exe manage.py profile_catalog
.\.venv\Scripts\python.exe manage.py test shop.test_catalog_performance --noinput
```

The profiling command reports status, elapsed time, query count, summed SQL time, repeated normalized query shapes and the three slowest query prefixes. It makes no external requests and writes no business data. Existing price/filter/family regression tests are retained. A new regression asserts that an unused featured context executes zero SQL.

PostgreSQL execution plans, realistic concurrent load and real-device asset/network timing remain preview-environment checks; SQLite samples cannot certify those.

# Catalog performance audit — 28 September 2026

Dataset: 6,697 products, 6,420 canonical listings, 6,678 variants. No catalog query or index changes were made in this read-only audit.

## Before / existing fix / current measurement

The 22 September baseline in `CATALOG_PERFORMANCE.md` records Dog and Royal search exceeding an eight-second HTTP timeout. That is a lower bound, not a completed response measurement.

The 26 September implementation already removed unnecessary family-price annotations from ordinary browsing, replaced multiplying joins with EXISTS, reused paginator counts and avoided SQLite's repeated low-selectivity active-index scans. Historical rendered Django-client results after that fix were Dog 0.54 s and Royal search 0.19–0.30 s. These are historical measurements, not results from today's machine conditions.

Current read-only anonymous Django-client GETs include response rendering but exclude network, browser JavaScript, image loading and production concurrency. Every response was HTTP 200. Three samples per endpoint were captured during each report run:

| Endpoint | Queries | First audit run (seconds) | Repeat run (seconds) |
| --- | ---: | ---: | ---: |
| `/category/dog/` | 17 | 1.63–1.90 | 1.18–5.78 |
| `/search/?q=royal` | 15 | 1.31–1.37 | 1.24–4.97 |
| `/category/dog/?sort=price_low` | 17 | 1.56–1.67 | 1.76–2.67 |

The repeat overlapped other local verification work. SQL time also varied (Dog up to 3.79 s); these noisy runs do not establish a new query regression or a production performance guarantee. Query counts remain bounded. Raw sample times and SQL durations are in `catalog_review/audit_manifest.json`; the previous run is preserved under `catalog_review/history-*`.

Likely earlier bottlenecks were correlated family pricing and repeated counts; the existing fix addresses those. No evidence justified another large rewrite during Phase 1. Before launch, measure warmed and cold responses on an otherwise idle machine, inspect slow-query plans, then repeat on PostgreSQL and after publication-gating changes. Track p50/p95 under representative concurrency separately from image performance.

## Repeat

Run the read-only `audit_catalog_quality` command with `--profile` and a new output directory, or `--archive-existing`. It blocks non-SELECT SQL, checks business-row fingerprints before/after and never performs cart/order POSTs.

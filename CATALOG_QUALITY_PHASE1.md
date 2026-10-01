# Catalog quality Phase 1 — read-only audit

28 September 2026. **Review preparation complete; publication safety is not implemented by this phase. The catalog is not launch-ready.**

## Findings requiring action

- 6,697 products, 6,420 canonical listings, 6,678 variants.
- 92 zero-price variants, all active and recorded in stock. Current checkout permits zero prices; this is a Phase 2 purchase-safety blocker. No free-item exception/approval field currently exists.
- 131 blank variant SKUs. 4,342 products have no active image record.
- 6,676 variants still have stock=10. No variant ledger-chain/balance mismatches were detected, but a balanced development adjustment is not a verified physical count.
- Supplied inventory export has only 12 identities, all matched. It is dated historical evidence, not verification of the other products or current quantities.
- 24 duplicate/similar candidate groups. These include intentionally grouped packs; they are not 24 proven duplicate products.
- 6,496 master rows need pack review. 371 have possible title/handle/normalized-quantity conflicts, while 6,179 variants lack normalized pack quantity/unit. Titles may describe animal weight/dosage; do not infer the correct pack from these signals.
- 6,457 products have imported best-seller flags; 6,180 are active canonical listings. No verified Shopify sales history was supplied. Local order counts are not assumed to be genuine sales evidence.
- 2,223 products need descriptions; no medical/nutritional copy was generated. 2,179 products have specialist-review signals, not asserted prescription/cold-chain rules.
- Zero products currently have valid catalog approval. Approval enforcement would therefore block the entire current catalog until staff review. Plan and test that change explicitly in Phase 2.

## Deliverables

`catalog_review/` contains the nine requested CSV reports and `catalog_summary.md`, plus a machine-readable integrity/provenance manifest. Existing zero-price and blank-SKU reports were preserved under a timestamped `history-*` directory. The pre-existing `products_without_images.csv` was left untouched and is older than the new reports.

There are 6,698 master rows: 6,678 variants plus 20 products with no variants. Image and stock reports are row-level and include simple products. Counts overlap; do not add them together. `unpublished_recommendations.csv` is a proposed review queue, not an applied unpublishing operation.

The requested CSV schema and source identities take precedence over workbook formatting. CSV exports remain native Django output so they can be regenerated without a spreadsheet runtime in production. They have explicit review reasons, source fields, safe text escaping and blank owner-decision/evidence fields. Import SKU/ID columns as Text. A rerun archives existing answers but does not automatically carry them forward or approve them.

## Existing systems retained

- Self-referencing Category; Product/Variant/Image; Brand; exact Decimal prices; `variant_family`; pack quantity/unit/comparison-group fields.
- Source-aware Shopify importer, inventory reconciliation, pack grouping and media audit commands. Import/reconciliation guards block applying old snapshots after ledger/order activity.
- Product-card and detail services, current-price cart/checkout, append-only stock movements and permission-controlled adjustments.
- CRM catalog editing, images, variants, archive/restore and signed, evidence-based approval records. Stock, identity and approval changes remain separate.

Later changes should extend these systems, not duplicate them. Existing importer defaults (including quantity=1 for an untracked source) must not be treated as verified stock. Family/card logic currently preselects the cheapest available pack; the requested explicit Choose Size bottom sheet is still future work.

## Safe curation plan

1. Phase 2: centralize purchase eligibility across cards/detail, direct Add/Buy Now POSTs, quantity updates, reorder, existing carts and atomic checkout. Reject nonpositive prices by default; do not substitute MRP. Decide a controlled approval rollout with the owner and test stale reviews/grouped packs. No automatic free-item exception.
2. Review pack/source mismatches and exact image assignments using the existing CRM. Current uploads must not be overwritten by historical export values without evidence.
3. Add an explicit owner-curated merchandising placement/rank separate from legacy imported flags, with existing staff permissions, eligible approved packs and configurable 8–20 product homepage limits. Do not mass-reset flags or invent sales rankings.
4. Extend CRM quality filters, then add the mobile Choose Size sheet. Reuse variant IDs, exact prices, stock checks and existing comparison-group math.
5. Repeat catalog performance and purchasing/security regression tests after gating. Render/DNS/Shopify remain out of scope.

## Changes and verification

New code only:

- `shop/services/catalog_quality.py` — read-only evidence analysis, stock/pack/image/duplicate findings and row fingerprints.
- `shop/management/commands/audit_catalog_quality.py` — repeatable SELECT-only exporter, preserved older reports, optional GET profiling.
- `shop/test_catalog_quality.py` — 11 tests covering detection, source ambiguity, image-file/ownership checks, ledger reconciliation, no mutation, source coverage, report preservation and CSV formula escaping.

Documentation: this file, `CATALOG_PERFORMANCE_NOTES.md` and generated reports. No application behavior, model, schema, existing source file, stock ledger, product values or storefront template was changed. Prior unrelated working changes remain intact.

Checks: Django check passed; migration drift check returned no changes. **72 tests passed** in 17.270 seconds across catalog quality, approval, pack families, pricing and performance. These are audit/existing-rule tests, not proof that the future purchase safeguards are implemented. No browser visual changes were made.

Checkpoint: `codex/catalog-quality-checkpoint-20260928` at `3ce07b1b348094e2920f99ee3995c8b42c5d96e1`. This preserves prior tracked state; existing untracked files were left intact. Before/after row fingerprints match for catalog, taxonomy, family links, images, orders/items, ledger, review history and category/pet memberships.

## Commands

From `C:\Users\danyb\Desktop\suryavets-django`:

```powershell
.\.venv\Scripts\python.exe manage.py audit_catalog_quality --sources 'C:/Users/danyb/Downloads/products_export_1 (1).zip' 'C:/Users/danyb/Downloads/products_export_2 (1).zip' --inventory 'C:/Users/danyb/Downloads/inventory_export_1.csv' --output-dir catalog_review --archive-existing --profile
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test shop.test_catalog_quality shop.test_catalog_approval shop.test_pack_families shop.test_pricing shop.test_catalog_performance --noinput
```

**Is the catalog safe to review for launch? Yes: the reports and existing CRM provide a non-destructive review starting point. Is it safe to launch? No: prices, stock, pack identity/images and approvals remain unresolved, and purchase enforcement is pending.**

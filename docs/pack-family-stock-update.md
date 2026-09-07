# Existing pack families and stock reset — 8 September 2026

## Applied locally

- Linked 221 conservative pack families comprising 498 existing product records. The 277 sibling records no longer produce duplicate catalog cards; their original URLs and identities remain valid.
- Every existing variant (6,677) and every product without variants (20) now has stock 10. This is the owner's requested opening balance, **not a physical inventory verification**. Orders will deduct stock normally; stock is not permanently pinned to 10.
- Added 6,692 inventory adjustments; five balances were already 10. Existing movement records were not changed. Visibility and tracking flags were preserved.
- 287 candidate families remain unlinked for review. There are no invented sizes, prices, SKUs or manufacturer-only packs. The complete catalog is NOT claimed to have fully verified variant coverage.

Example: `/product/n-d-gf-chic-adu-mini-dry-food-800gm/` now offers 800GM (₹816), 2.5KG (₹2,232) and 7KG (₹5,640). The live source `/products/n-d-gf-chic-adu-mini-dry-food-l-7kg` was opened and its 7KG label and ₹5,640 price checked. Other mappings are based on the supplied Shopify data, not individual live-page verification.

## Conservative linking, not destructive merging

Candidates must share normalized title, brand, primary category, product type, prescription flag and exact handle stem. Each source must have exactly one active variant and a positive selling price. Explicit terminal handle quantities must agree with pack labels; quantities must be distinct and use the same measurement dimension. Conflicting names, ambiguous quantities, additional option dimensions and count/accessory packs remain for review.

`Product.variant_family` and `family_name` let a root present linked packs. Variants retain their original `product_id`, prices and SKUs. Cart validation accepts only an active pack belonging to that family and stores its original source product. Historical orders and inventory remain attached to the original source. Legacy sibling URLs show the family with that source pack selected. Category and pet memberships are preserved and unioned onto the root.

Shared catalog cards, price filtering/sorting and product pages use family pack availability. CRM product editors link to each source pack editor and audited stock controls. Best-value comparisons remain opt-in: grouping alone does not verify formulation equivalence. Source photos are retained; missing pack photos show an explicit notice rather than automatically substituting another size. Import photo accuracy still needs review (the N&D example's imported artwork appears to say lamb while its source title says CHIC); this update does not certify label/image accuracy.

## Safety and verification

- Pre-change Git checkpoint: `codex/checkpoint-before-pack-families-stock-20260908` at `8cb959e`.
- Pre-change SQLite backup: `tmp/pre-pack-families-stock-20260908.sqlite3`.
- Review reports: `tmp/PACK_FAMILY_REVIEW.json` and `tmp/PACK_FAMILY_APPLIED.json` (local, not committed).
- Migration `0011_existing_pack_families` applied.
- `manage.py check`: passed. `makemigrations --check --dry-run`: no drift.
- Full suite: **139 tests passed**, including separate-source pack browser journeys at nine widths (320–1440), exact cart/order pack identity, injection rejection and stock reset retry safety. Desktop/mobile fixture screenshots reviewed; actual N&D family page inspected. No Shopify pixel-match claim.
- Read-only backup comparison: zero changed/removed historical product names/slugs/SKUs/prices, variant owners/names/SKUs/prices, order item rows or existing inventory movements.
- Shopify, DNS and Render were untouched.

## Commands

From `C:\Users\danyb\Desktop\suryavets-django`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_pack_families --noinput
```

Grouping was applied with:

```powershell
.\.venv\Scripts\python.exe manage.py group_existing_packs --report tmp/PACK_FAMILY_APPLIED.json --apply
```

The stock reset was already applied. **Do not issue a new batch just to refresh the page**. The following original batch is idempotent and will skip if retried, so it cannot erase subsequent purchases:

```powershell
.\.venv\Scripts\python.exe manage.py set_catalog_stock --quantity 10 --batch 78f15495-46f1-47a4-a6a4-ad234d115010 --reason "Owner-requested local catalog balance of 10 per pack on 2026-09-08; not physical inventory verification." --apply
```

For future intentional resets, use a new UUID only after reconciling real inventory. Omitting `--apply` previews a reset without changing data.

## Changed files

- Schema: `shop/models.py`, `shop/migrations/0011_existing_pack_families.py`.
- Linking/reset: `shop/services/pack_families.py`, `shop/management/commands/group_existing_packs.py`, `shop/management/commands/set_catalog_stock.py`.
- Catalog/cart/CRM: `shop/catalog_views.py`, `shop/views.py`, `shop/crm_catalog_views.py`, `shop/services/pricing.py`, `shop/services/variants.py`.
- Presentation: `shop/templates/catalog/product_detail.html`, `shop/templates/crm/product_editor.html`, the shared `product_buying.html`, `product_card.html`, `product_gallery.html`, `shop/static/js/catalog.js`, `shop/static/css/buying.css`.
- Tests: `shop/test_pack_families.py`, `shop/test_variant_browser.py`.
- Documentation: this guide and `SURYA_MIGRATION_AUDIT.md`.

## Remaining

Review the 287 held groups and verify new manufacturer-only pack identities, selling prices, SKUs and supply before activation. Reconcile the two existing duplicate-SKU groups. Obtain missing original photos and verify imported label accuracy; 4,342 products still have no source image. Review nutrition drafts separately. None of those gaps are hidden by this stock reset.

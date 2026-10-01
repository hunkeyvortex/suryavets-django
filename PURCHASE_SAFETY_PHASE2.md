# Phase 2 — Purchase safety

Verified 29 September 2026 in `C:\Users\danyb\Desktop\suryavets-django`.

## Result and boundary

**No: a zero-price or otherwise policy-invalid variant cannot become a new order through the audited application purchase paths.** There is no free-item exception. Direct database/ORM access is privileged infrastructure access, not a customer purchase API; future order-creation integrations must call the same service.

92 of 6,678 current variants have nonpositive effective selling prices. They are blocked without changing their prices. This is purchase protection, not catalog launch approval or verification of physical stock.

`shop/services/purchasing.py` owns the policy and its SQL projection. It rejects inactive products/roots/packs, nonpositive effective prices, missing or unrelated required packs, explicit latest CRM holds, invalid quantities and insufficient recorded stock. Simple products respect their existing inventory-tracking flag; variants require stock. A linked family member cannot silently become a base-product purchase.

An unreviewed import is not the same as an explicit hold. The existing default review queue remains a launch-review concern. A latest `held` review blocks its product (and all packs if the held product is a canonical family). Approval does not override price/activity/stock checks. No products were auto-approved. No schema or free-item flag was added.

## Entry-point audit

| Entry point | Protection |
| --- | --- |
| Product detail, quick-add/card, choose-size | Shared Add to Cart endpoint validates exact selected SKU server-side; UI also disables invalid choices. |
| Buy Now | Same endpoint and policy before redirecting to checkout. |
| Direct/crafted Add to Cart POST | Unrelated IDs rejected; inactive/zero/negative/unavailable packs cannot create a line. |
| Normal quantity POST and AJAX autosave | Policy applied to requested resulting quantity; rejected updates preserve saved quantity and return current basket state. |
| Existing cart / checkout review | Every line revalidated; named warnings identify the affected pack. Invalid totals are withheld from the displayed summary. |
| Checkout submission / order creation | `place_order` independently validates all lines using locked products, roots and variants. Any invalid line rejects the whole transaction before order items, stock deductions or coupon reservation. |
| Coupon apply/remove | Invalid baskets cannot advance into checkout; coupons never override item eligibility. Invalid checkout does not consume coupon usage. |
| Buy Again / reorder | Checks current exact identity, current price and stock; skips invalid packs with explanation. No size substitution or historical-price reuse. |
| Guest-cart merge on sign-in | Combined quantities validated atomically; invalid merge leaves guest/account baskets unchanged and reports the issue. |
| Legacy `views_new` module | Not routed; exported purchase functions now delegate to the audited current views. |
| CRM/manual order / Admin | No CRM manual-order creation route found. Existing Admin order/OrderItem creation restrictions retained. CRM status management does not create replacement purchase lines. |

Existing order snapshots and idempotent receipt retrieval are preserved. A previously completed order is not retroactively rewritten when its catalog data changes.

## Customer and CRM behavior

- Mixed families retain valid selectable packs. Invalid packs show unavailable/price-unavailable messaging, not free pricing.
- All-invalid families show an unavailable state and disabled purchasing.
- From price, Best Value, savings, sale badges, price filters and sorting use eligible packs only. All-unavailable prices are NULL and sort last instead of appearing as zero-price bargains.
- Basket warnings identify the product and pack. No silent removal/substitution or partial checkout occurs. Removal remains available.
- CRM inventory supports `?safety=zero` and `?safety=blocked`, alongside the existing review queue. The review page explains per-pack rejection reasons. The hold selector explicitly states that it blocks purchases.
- Mutation rejections log path, reason code and product/variant IDs only. Ordinary page views do not generate rejection logs.

## Verification

- `python manage.py check`: passed.
- `python manage.py makemigrations --check --dry-run`: no changes detected.
- `python manage.py test shop --noinput`: 293 discovered; 279 passed, 14 optional browser tests skipped in this run.
- Explicit browser-enabled targeted run: 19 passed, no skips (`shop.test_purchase_safety`, `shop.test_purchase_safety_browser`, `shop.test_cart_autosave_browser`). This overlaps the full-suite backend tests; counts are not additive.
- Browser safety journeys exercised 1440, 375, 390 and 430px: valid pack, disabled zero-price pack, mixed family, entirely unavailable family/card, valid cart/checkout review, blocked existing cart and direct checkout URL. No horizontal overflow or JavaScript errors in the tested journey.
- Existing cart autosave browser regression passed, including rapid quantity edits.
- Tests use isolated Django test databases. No real orders, stock deductions, email sends or payments were made by these safety checks.
- Real-data read-only dog price-sort request: HTTP 200, approximately 0.99s in-process on this machine (one observation, not a performance SLA).
- Refreshed local preview at `http://127.0.0.1:8000/`; category smoke request returned 200. Preview process has email sending and Razorpay disabled; environment files unchanged.

Screenshots are test fixtures, not newly imported products. They are saved at `C:\Users\danyb\Documents\ChatGPT\suryavets-django\safety-mixed-{width}.png` and `safety-blocked-cart-{width}.png` for the four tested widths. Desktop and mobile screenshots were visually inspected.

## Data preservation

Tracked-work checkpoint: `codex/purchase-safety-checkpoint-20260928`, commit `005da9686d37bf887afd1d63f0f5e7eb8109d1e1`. Existing dirty and untracked work was preserved, not reset.

Read-only row fingerprints before final verification and afterwards match across products (6,697), variants (6,678), images (2,620), categories (170), brands (569), inventory movements (6,696), orders (3), order items (3), review events (0), collection memberships (30,580) and pet memberships (10,716).

Selected matching SHA-256 fingerprints:

| Data | SHA-256 |
| --- | --- |
| Products | `8a4870c41a6854453972ac02ffe16f7bbd8ebb752658f60f7cc3616e174435dd` |
| Variants, including prices and quantities | `b3bc3be93636104d7dfd2c48a1358b7846cf315f1e4fc3c5fa800c5bf4251600` |
| Inventory movements | `7db2777ab9ac5a72e266e536e843b3ac49353ff9e4611b060c0bd0ad0719ccac` |
| Orders | `7bff06af581236015daea1a9777e93abfb9f0a175a54ea7cd7e08e3d3a7d23e0` |
| Order items | `e606dd42ecfdd8632b111638fa930eda682eec8bcfecac293bba82b3e6c555dd` |

No migrations, price corrections, bulk stock changes, ledger rewrites, approvals, Shopify writes, DNS changes or deployments were performed. The inventory export still covers only 12 entries; full physical stock remains unverified.

## Files changed in this phase

- Policy/services: `shop/services/purchasing.py` (new), `accounts.py`, `cart.py`, `checkout.py`, `pack_families.py`, `pricing.py`, `product_cards.py`, `reorder.py`, `variants.py`.
- Views: `shop/views.py`, `views_new.py`, `catalog_views.py`, `crm_views.py`, `crm_catalog_review.py`.
- Templates: `shop/templates/basket.html`, `crm/catalog_inventory.html`, `crm/catalog_review.html`, `includes/card_variant.html`, `includes/product_buying.html`, `includes/product_card_v2.html`.
- Frontend: `shop/static/css/basket.css`, `shop/static/js/cart.js`, `catalog.js`, `product-cards.js`; `shop/templatetags/shop_filters.py`.
- Tests: `shop/test_purchase_safety.py` (new), `test_purchase_safety_browser.py` (new), `purchase_safety_browser_test.cjs` (new), `test_catalog_performance.py`, `test_catalog_approval.py`, `test_pricing.py`.
- This report. Other pre-existing working-tree changes do not belong to this phase.

## Re-run locally

```powershell
cd C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test shop --noinput
```

Browser tests require `SURYA_BROWSER_NODE`, `SURYA_PLAYWRIGHT_MODULE`, and `SURYA_BROWSER_EXECUTABLE` pointing to the installed Node, Playwright and Chrome runtimes. Run `manage.py test shop.test_purchase_safety_browser shop.test_cart_autosave_browser shop.test_purchase_safety --noinput` after configuring them. `SURYA_BROWSER_ARTIFACTS` optionally selects an existing screenshot folder.

Phase 2 is complete within this scope. Catalog source review and owner-approved physical stock reconciliation remain separate tasks. This report does not declare the store launch-ready.

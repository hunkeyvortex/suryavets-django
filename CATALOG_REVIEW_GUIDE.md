# Catalog review — staged rollout

25 September 2026. **Review-only mode. Storefront purchasing is unchanged.**

Automatic purchase blocking was not enabled: doing so would immediately block the entire unreviewed imported catalog. The safety review required explicit approval for that rollout. This stage adds a usable review workflow; it does not claim the catalog or checkout is launch-safe yet.

## Use it

1. Sign in to the existing CRM and open `/crm/inventory/`.
2. Select **Review queue**, then **Review catalog** beside a product.
3. Review every exact pack, SKU, MRP/selling price, image and recorded quantity. Use **Edit product and photos** or **Review stock history** for existing editing/adjustment tools.
4. Supply a meaningful source reference including stock-count time and warehouse/location. The old all-products stock=10 values are not verification.
5. Tick the three confirmations and choose **Approve review**, or keep the item in the review queue with an explanation.

Access requires an active staff user with `shop.access_crm` and the new `shop.approve_catalog` permission. Superusers already qualify. Assign **Can approve catalog products for sale** to trusted reviewers in Django Admin; no existing users or role groups were automatically granted this permission. Editing products and adjusting stock still require their own existing permissions.

## Controls implemented

- Default: no imported product is automatically reviewed or approved.
- Server-side approval checks reject missing exact SKUs, zero/negative prices, selling price above MRP, negative quantities, absent/invalid image references and missing local image files. Multi-pack products need exact image assignments.
- Remote HTTPS image references require staff verification; the workflow does not download them or certify remote availability or package accuracy.
- A signed, reviewer-specific review token includes catalog data, current quantities and latest stock movement. Changed/expired/reused review forms are rejected rather than approving stale data.
- Changes to prices, identities, pack options, image references or reviewed content make the review stale, including bulk updates that bypass model saves.
- Normal stock changes do not alter the approved product identity. Staff must still use the existing audited stock-adjustment workflow; this feature does not certify arbitrary direct database edits.
- Each decision stores reviewer, time, source note, assertions and a snapshot. The history is read-only in Django Admin and absent from customer pages.
- Approval does not adjust stock, restore quantities, import data, publish/archive products, send email or affect payments/orders.
- The inventory **Has approval record** filter includes potentially stale records; the displayed per-product state distinguishes them. It is not a guaranteed launch-ready-product filter.

## What remains before enforcement

Obtain fresh full inventory/product exports and approve actual corrections. Preserve the existing stock ledger and account for later orders/adjustments; use existing adjustment tools with reasons rather than blanket reimport.

After explicit rollout approval, implement and verify purchase/publication restrictions across listing/detail, direct cart and Buy Now POSTs, quantity changes, existing carts, reorder and atomic checkout. Include stale-approval and grouped-pack tests. **Those purchase restrictions are not enabled or claimed complete by this stage.** No environment flag secretly switches them on.

An explicit free-product approval policy, real image-content verification, review-expiry policy and production PostgreSQL concurrency acceptance remain separate decisions. Restoring previous field values can restore a matching content fingerprint; decision history still remains. This fingerprint detects content differences, not every edit ever made.

## Safety and verification

- Full suite: **227 tests passed**, including browser tests, no skips (394.559 seconds).
- After mobile layout refinement: all **28 review tests passed** again, including the browser workflow (57.369 seconds).
- Review page tested at 320, 360, 375, 390, 412, 430, 768 and 1440px; 320px and desktop screenshots visually inspected. Pack details become labelled cards on phones.
- Django check passed; migration drift check returned no changes.
- Compared every pre-existing column/row in products (6,697), variants (6,677), images (2,619), orders (3), order items (3), stock movements (6,695), users and user/group permission assignments against the backup: all preserved. Real review events: zero.
- Browser artifacts: `C:\Users\danyb\Documents\ChatGPT\suryavets-django\catalog-review-verification` (test fixtures only).

### Files changed for this stage

- `shop/models.py`, `shop/migrations/0016_catalog_review_workflow.py`: additive metadata/history/permission.
- `shop/services/catalog_approval.py`, `shop/crm_catalog_review.py`: validation, snapshot comparisons and staff decision flow.
- `shop/crm_urls.py`, `shop/crm_views.py`, `shop/templatetags/shop_filters.py`: route, inventory filters and review labels.
- `shop/templates/crm/catalog_review.html`, `shop/templates/crm/catalog_inventory.html`, `shop/static/css/crm-catalog.css`: responsive review UI.
- `shop/admin.py`: read-only decision history.
- `shop/test_catalog_approval.py`, `shop/test_catalog_review_browser.py`, `shop/catalog_review_browser_test.cjs`: new tests, without weakening the existing regression tests.
- `SHOPIFY_PARITY_AUDIT.md` and this guide: staged rollout status and instructions.

Existing Brevo changes and unrelated user files were preserved. No cart/checkout/payment service was altered.

Checkpoint branch: `codex/catalog-approval-checkpoint-20260925` at `750947fa5e5e63493e891348cdc269f5bd7c5d74`. It preserves the prior tracked working state without resetting it; unrelated untracked files were left untouched.

Database backup: `C:\Users\danyb\Documents\ChatGPT\suryavets-django\catalog-before-approval-20260925.sqlite3`. Contains private store data: keep it local and do not commit or share it.

Migration `0016_catalog_review_workflow` adds only review metadata, an event table and a permission. It does not populate approvals or change existing product quantities/prices/visibility. Do not restore the database backup over newer orders; use it only as part of a reviewed recovery plan.

PowerShell commands:

```powershell
Set-Location 'C:\Users\danyb\Desktop\suryavets-django'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_catalog_approval --noinput
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

The optional browser regression uses the existing `SURYA_BROWSER_NODE`, `SURYA_PLAYWRIGHT_MODULE`, `SURYA_BROWSER_EXECUTABLE` and `SURYA_BROWSER_ARTIFACTS` settings. It runs against a disposable test database, never real staff/product records.

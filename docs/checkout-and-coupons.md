# Original checkout and CRM coupons

Implemented in the existing local `C:\Users\danyb\Desktop\suryavets-django` project. No live Shopify changes, deployment or DNS changes.

## Preview and use

- Checkout: http://127.0.0.1:8007/checkout/ (requires a non-empty basket).
- Coupon management: http://127.0.0.1:8007/crm/coupons/.
- Create a coupon: http://127.0.0.1:8007/crm/coupons/new/.

Use an existing administrator or an active staff account in **Surya CRM Manager**. Viewer/Operations users can see coupons but cannot create/edit them. No promotional codes were seeded in the development database. Codes used by automated tests exist only in disposable databases.

In CRM, choose Create coupon, enter a code and internal campaign name, select Percentage or Fixed amount, then set the value and any restrictions. Enable **Active at checkout** when ready and save. Edit the coupon to adjust its rules or disable it; codes are immutable after creation. Create a new coupon for a new code. Changes record the staff actor and changed field names. Previous orders retain their original code and discount.

## Checkout design

This is an original SuryaVets green/gold/white design, not a Shopify page copy. Contact, delivery, billing and payment are grouped into sections. Desktop has a sticky order summary; mobile uses a full-width stacked layout. Product thumbnails, pack/quantity details, savings and the final total are visible. Billing fields reveal when the same-address checkbox is cleared. The page also works without JavaScript; in that case billing fields remain visible.

Apply/remove coupon uses a CSRF-protected form submission and preserves unfinished address fields. Successfully applied codes are remembered in the session for that cart across refreshes, revalidated on every review, and cleared after successful order placement. Account changes that switch to another cart do not silently transfer its coupon.

## Coupon rules

- One code per order, case-insensitive input; 3–40 letters/numbers/hyphens/underscores.
- Percentage or fixed rupee savings, optional maximum discount, minimum product subtotal, start/end dates and total usage limit.
- Codes start disabled until staff enable them. Dates use the application timezone, explicitly shown in CRM (currently UTC); blank dates mean no scheduling restriction.
- Savings apply to current product prices, including existing sale prices; no exclusions or stacking. Shipping is not discounted. The existing ₹499 free-delivery threshold is evaluated **before** coupon savings.
- Discount is rounded to two decimal places and never exceeds the product subtotal.
- A use is consumed when the order is successfully placed, not when paid. Cancellation **does not** return that use. There is no per-customer limit, first-order restriction or abuse-prevention identity check yet; use total limits appropriately.
- Application is not a reservation. Coupons are locked, validated and conditionally reserved within the same transaction as stock deductions/order creation. Failed checkout rolls back the use. Duplicate checkout submissions return the same order without another use.
- Coupon code, discount amount and final totals are snapshotted onto each order. A signed checkout review includes coupon revision and savings; changing a code or its rules requires another review rather than silently changing the price.
- Managers cannot overwrite a stale edit, reduce the usage limit below recorded uses, reset the counter, or delete coupons through the UI. Django Admin provides read-only coupon records; use CRM for rule changes.

## Local setup and verification

All **102 tests passed** with browser tests enabled. Django check and migration-drift checks pass through 0008. This includes a real concurrent two-cart/one-use coupon test on SQLite; PostgreSQL still needs separate deployment validation.

Baseline Git checkpoint: `5fc9d64`. A timestamped `tmp/pre-coupons-*.sqlite3` backup was created before migration `0008_checkout_coupons`. Migration and updated role setup have already run locally.

From the project folder on another checkout:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py setup_crm_roles
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Optional browser tests use the existing `SURYA_BROWSER_NODE`, `SURYA_PLAYWRIGHT_MODULE`, and `SURYA_BROWSER_EXECUTABLE` variables documented in `docs/crm-and-accounts.md`. Set `SURYA_BROWSER_ARTIFACTS` to `C:/Users/danyb/Desktop/suryavets-django/tmp/checkout-coupon-verification` to capture screenshots. Browser tests create/edit a coupon in CRM, apply/remove it in checkout, verify address preservation, submit an order and repeat the submission safely. Checkout overflow is tested at 375/390/430/768/1024/1440px. Staff coupon screens are checked at desktop/mobile widths. Screenshots contain fake test data only.

## Changed files

- `shop/models.py`, `shop/migrations/0008_checkout_coupons.py`: coupon rules, order snapshots, audit link and permissions.
- `shop/services/coupons.py`, `shop/services/checkout.py`: quotes, signed review and atomic usage/stock validation.
- `shop/forms.py`, `shop/views.py`: checkout form layout fields, coupon application/removal and session persistence.
- `shop/templates/checkout_new.html`, `includes/checkout_field.html`, `shop/static/css/checkout.css`, `shop/static/js/checkout.js`: original responsive checkout.
- `shop/crm_forms.py`, `shop/crm_views.py`, `shop/crm_urls.py`, `shop/templates/crm/coupons.html`, `coupon_edit.html`, `base.html`, `shop/static/css/crm.css`: staff coupon management.
- `shop/admin.py`, `shop/management/commands/setup_crm_roles.py`: access control and read-only admin records.
- `shop/templates/includes/order_totals.html`, `order_success.html`, `order_detail.html`, `crm/order_detail.html`: historical savings and totals.
- `shop/test_coupons.py`, `shop/test_coupon_browser.py`, `shop/checkout_browser_test.cjs`: rule, security, concurrency and browser coverage.

## Not changed / remaining

No online payment is charged or confirmed here. Payment gateway/webhooks/refunds, reliable email delivery, PostgreSQL concurrency verification, physical inventory verification, fraud/rate limiting and final production tests remain separate work. Coupons do not make pending orders paid. The existing server is on port 8007; no new preview server or hosting project was created.

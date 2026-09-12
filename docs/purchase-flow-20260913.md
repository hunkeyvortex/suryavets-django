# Purchase flow — 13 September 2026

## Audit and scope

Actual repository: `C:\Users\danyb\Desktop\suryavets-django` (`Desktop\suryavets` does not exist). Starting commit `e8a7577`; tracked tree was clean. Unrelated untracked exports/media/scripts were preserved. Git checkpoint: `codex/checkpoint-before-purchase-flow-20260913`. SQLite backup: `tmp/before-purchase-flow-20260913.sqlite3` (private, not committed).

Reused: Product/ProductVariant, session/authenticated Cart and CartItem, signed checkout review tokens, server pricing/coupons/shipping, transactional stock ledger, Order/OrderItem snapshots, OrderStatusHistory, OrderNotification, email/password login, saved addresses, CRM permissions and customer-owned account queries. No Razorpay integration existed. Online purchases were intentionally rejected; COD worked. No separate payment signals or duplicate order database were added.

Existing notification worker only sent plain-text customer status messages. Settings used Django 6.1 MAILERS, with console email locally and delivery disabled. SMTP options were not wired. Confirmation was a generic page with pending-payment wording even for COD. Product-card `next` fields returned buyers to catalog pages.

## Implemented behaviour

1. Successful normal Add to Cart always redirects to `/cart/`. Buy Now uses explicit `intent=buy_now` and redirects to checkout. Validation failures retain existing safe error handling. Cart writes remain CSRF-protected POSTs. Variant IDs, active state, stock and quantity are validated server-side; sizes remain separate cart lines.
2. Existing responsive cart and coupon/shipping calculations are reused. Cards still add one item without quantity controls; cart/detail controls remain functional. No PIN-code feature was added.
3. Checkout computes totals from locked current records and verifies signed review fingerprints. A checkout key creates only one order. Existing snapshots retain name, exact pack, SKU, price, quantity, image reference and line total. The same order is immediately available to CRM and, for signed-in buyers, My Account.
4. COD creates a Placed/payment-Pending order and reserves stock once. Online checkout creates an internal Awaiting-payment order and one PaymentAttempt, reserving the exact stock and coupon once. It does NOT announce a placed/paid order or queue confirmation email yet. The customer can resume from My Account.
5. Test-only Razorpay Orders API setup uses server-calculated INR paise. Live keys cannot enable this implementation. Browser verification requires an HMAC using the stored gateway order ID, then server API checks of payment ID/order ownership, captured state, amount, currency and the gateway order's paid state. Signed `payment.captured` webhooks use the same verification function. Captured payment moves the order to Placed/payment-Paid, preserving separate fulfillment status and real events.
6. Duplicate initialization reuses the bound gateway order. A timeout/unknown create outcome is marked Uncertain and cannot automatically create another remote payment order. Browser callback/webhook retries do not duplicate stock deductions, placed events or email outbox rows. An unknown extra payment requires reconciliation.
7. Confirmation now distinguishes COD pending from verified online paid, and provides View order, Track your order and Continue shopping for authenticated buyers. Guest receipts remain session-owned; no unsafe public guest-order links or automatic email-based order claiming were introduced.
8. Existing outbox now has customer/admin audiences and recipient snapshots. Branded HTML and text alternatives include historical line items, totals, address and actual payment state. Admin messages use `ORDER_NOTIFICATION_EMAIL`; no personal address is hardcoded. Customer messages exclude internal notes. Links derive only from configured `PUBLIC_SITE_URL`; customer links require account login and CRM links require staff permission.
9. Delivery runs after transaction commit when enabled. Atomic Pending→Sending claims prevent automatic double sends. SMTP failure cannot roll back the order. Failed or interrupted Sending rows are NOT blindly retried: SMTP acceptance can be ambiguous. Reconcile with the provider before an explicitly approved resend. Exactly-once inbox delivery cannot be guaranteed by SMTP.

## Schema and data

Migration `0014_purchase_flow_notifications` adds PaymentAttempt, notification audience/recipient and Awaiting-payment status. It replaces the notification uniqueness constraint with event/channel/audience uniqueness; old rows default to Customer. No historical notifications are backfilled or sent. The migration is applied locally.

Read-only comparison against the backup confirms every old column in orders, order items, products, variants, stock movements, carts, cart items, addresses, users, events and notifications is unchanged. There are still two local orders and zero local gateway attempts after tests; fixtures use separate disposable databases.

## Configuration (not enabled yet)

The current settings read **process environment variables**. `.env.example` is a reference; this project does not automatically load `.env`. Set these in the terminal/service that starts Django, then restart that same server. Do not put credentials in source control or chat.

- `RAZORPAY_ENABLED`: enable only after supplying test credentials.
- `RAZORPAY_KEY_ID`: a Razorpay `rzp_test_...` key.
- `RAZORPAY_KEY_SECRET`: matching test secret.
- `RAZORPAY_WEBHOOK_SECRET`: separately configured webhook secret.
- `DJANGO_EMAIL_BACKEND`: console for safe development; SMTP only for an approved real inbox test.
- `ORDER_EMAIL_ENABLED`: False by default; gates all delivery.
- `ORDER_EMAIL_AUTO_SEND`: True by default; False leaves delivery to the explicit worker.
- `ORDER_NOTIFICATION_EMAIL`: one authorized admin mailbox.
- `DEFAULT_FROM_EMAIL`: verified sender identity.
- `PUBLIC_SITE_URL`: actual application origin for email links (local HTTP only in DEBUG; production HTTPS).
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`: SMTP settings mapped into Django 6.1 MAILERS OPTIONS, with a 15-second timeout.

For safe preview, use the console backend with test customer/admin addresses. Do not switch to SMTP and drain an old outbox without reviewing Pending rows in Django Admin. Both real email and gateway execution remain disabled in the current local environment.

```powershell
cd C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop --noinput
# After configuring the backend and reviewing queued recipients:
.\.venv\Scripts\python.exe manage.py send_order_notifications
```

Webhook endpoint: `/payments/razorpay/webhook/`. Browser verification is CSRF-protected; only the webhook is CSRF-exempt and it requires a raw-body signature. A reachable development callback URL is needed to test actual remote webhook delivery; no tunnel or deployment was created.

## Recovery and remaining work

- No real Razorpay TEST keys or email credentials were configured by the user. Real gateway checkout, real webhook delivery and real inbox delivery have **not** been tested. Test doubles are not proof of third-party integration success.
- Configure automatic capture in the Razorpay test dashboard and check a genuine captured test payment. Authorized-only or failed payments remain pending and send no paid-order confirmation.
- Unpaid/uncertain reservations are deliberately retained for review; there is no unsafe automatic stock release while a remote payment may still capture. Reservation expiry, payment cancellation/refund policy and PostgreSQL concurrency testing are prerequisites for production enablement. This is not production-payment readiness.
- `reconcile_test_payment ORDER_NUMBER --gateway-order-id order_... [--payment-id pay_...]` checks gateway receipt, currency and amount before binding an uncertain existing attempt. With a payment ID it performs the same captured-payment verification. It never creates a second remote order, issues refunds or forcibly marks a failed payment paid.
- Guest purchases do not magically appear in an unrelated/login-by-email account. Sign in before checkout for My Account history; guests retain a session-protected receipt and email details.
- SMTP transport/client-specific rendering (Gmail/Outlook) and provider reconciliation procedures still need real-environment verification. HTML browser previews are not email-client certification.
- Shopify, DNS and Render were not modified. No real customer emails or payment requests were sent.

## Files

Backend: `shop/views.py`, `forms.py`, `urls.py`, `models.py`, `admin.py`, `payment_views.py`; `services/checkout.py`, `order_tracking.py`, new `payments.py` and `notifications.py`; existing notification command plus new reconciliation command. Configuration: `suryavets/settings.py`, `.env.example`, migration 0014.

UI: checkout/payment/confirmation templates, account order card, product buying action, two email templates, payment JS and confirmation CSS. Tests: purchase flow unit and browser tests, email preview test, existing account/variant/checkout regression assertions. All additions extend the existing application.

## Final verification

`manage.py check` passes; `makemigrations --check --dry-run` reports no changes. The final full run completed **183 tests, OK, no skips**, with all browser runtimes enabled. This includes simulated captured-payment checkout, exact variant stock, customer/admin email counts, callback/webhook repeats, fake signatures, amount/currency/order mismatch, out-of-stock, rollback, SMTP failure, uncertain-attempt reconciliation, customer ownership and CRM access. Existing account, coupons, cart, import and catalog suites also pass.

Cart/variant UI is tested at 320/360/375/390/412/430/768/1024/1440px; confirmation at phone/tablet/desktop widths; both HTML emails at 320/390/600px. Browser screenshots were inspected for the confirmation pages and both emails. Preview artifacts are in `C:\Users\danyb\Documents\ChatGPT\suryavets-django\purchase-flow-verification`. All gateway/browser payment responses in these tests are explicitly simulated; no real gateway or SMTP transport verification is implied.

## Reference

Payment verification follows the [Razorpay Standard Checkout integration guidance](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/) and [webhook validation guidance](https://razorpay.com/docs/webhooks/validate-test/): server-side signature verification, captured payment checks and signed webhook bodies. Existing Django 6.1 installed mail backend code was inspected for MAILERS configuration.

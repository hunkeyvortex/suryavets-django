# Customer accounts and CRM tracking

Implemented in the existing `C:/Users/danyb/Desktop/suryavets-django` project. The requested `Desktop/suryavets` directory does not exist. See `docs/account-order-audit.md` for all thirteen initial audit findings and the pre-change backup/checkpoint.

## One order system

Customer and staff pages read the same `Order`, `OrderItem` and `OrderStatusHistory` rows. An authorized CRM transition immediately commits the new status and timestamped event in the same transaction. The customer sees it when opening/refreshing their order page. No second tracking database, simulated dates, polling service or Shopify dependency is used.

The legacy `pending` database value is retained and displayed as **Placed**. Normal progression is:

Placed → Confirmed → Processing → Packed → Shipped → Out for delivery → Delivered.

Cancellation is a terminal alternate route before dispatch. Backward or skipped stages are rejected. Staff reason and optional customer note are separate. Marking Shipped requires courier and AWB; an optional tracking URL must use HTTPS. Payment success never marks an order delivered.

Order status represents operational fulfillment. Shipment details are attached to that order, not another conflicting status field. Payment and return status remain independent:

- Payment: pending, paid, failed, refund pending, partially refunded, refunded.
- Return: no return, requested, approved, rejected, received.

Returns require a delivered order and explicit customer request. Staff must review eligibility; food/medicine returns are not promised. Receiving goods neither restocks nor refunds them automatically. Separate manager payment permission records externally verified references/outcomes; it **does not charge or refund money**. Refund references are retained on internal payment events, preserving the original payment reference. No automatic amount-based refund ledger or Razorpay integration is implied.

## Customer routes

| Route | Function |
| --- | --- |
| `/account/` | Dashboard tiles, recent orders, logout |
| `/account/orders/` | Paginated history, exact purchased variants, totals |
| `/account/orders/<order-number>/` | Snapshot detail, vertical tracker, shipment, customer-visible events |
| `/account/orders/<uuid>/` | Preserved legacy link to the same owned order |
| `/account/pets/` | Add/edit/remove pets; shop by catalog pet type |
| `/account/wishlist/` | Saved products, current price/availability, Choose size or Add to cart |
| `/account/addresses/` | Add/edit/delete/default; address line 2 supports landmarks |
| `/account/profile/` | Name and phone; current email displayed read-only |
| `/account/security/` | Django password-change validation, current session retained |
| `/account/support/` | Owned, order-linked support requests and customer-visible replies |

All routes require authentication. Every object lookup is scoped by user ownership, not a submitted user ID or matching email. Guest orders are not silently claimed by registration. Private pages send no-store/noindex headers. Mutations require POST and CSRF. Customer templates never serialize event internal notes or CRM activity.

### Buying again and cancellation

Buy again reorders all available lines using their original product/variant identities and **current prices**. Deleted/disabled packs, archived products, insufficient stock and unreviewed zero prices are skipped with messages. Missing packs never become another size or a base-product purchase. Existing cart quantities count toward stock limits; checkout still performs its independent locked price/stock check.

Customers can cancel only Placed/Confirmed orders with pending/failed payment and a complete stock ledger when stock was deducted. Staff can cancel eligible pre-dispatch orders. Existing append-only reversal logic restores recorded stock at most once. Paid/refunded orders and unsafe legacy stock records require support/manual review; cancellation is not a refund. Address edits and catalog changes never rewrite purchase snapshots.

New checkout items capture their image URL/reference. Older orders receive no guessed photo or transition dates. The existing order's known creation time became its Placed event; no legacy notification was queued. Source image URLs can still become unavailable if media is deleted; immutable file retention is a production media policy to finalize.

## Staff workflow

1. Open `/crm/orders/` with an authorized staff account.
2. Search order number, customer name, email or phone; filter status/payment/dates or returns.
3. Open Manage, inspect exact purchased items, address, payment and stock history.
4. Choose the next permitted status; enter an internal reason. Only put customer-safe information in Customer note.
5. For Shipped, supply courier/AWB and optionally the HTTPS courier URL.
6. Save. The shared timeline records the actor, real time and visibility-separated notes.

Dashboard New orders / To pack / Shipped / Delivered today cards are database-driven links. `/crm/support/` lets staff review support requests; `write_crm_notes` permission is required to respond. Replies are visible in the customer's own support area.

Active staff plus `access_crm` are required. Operations can process orders, review returns and write notes. Managers additionally get `manage_crm_payments` to record external payment verification. Viewer accounts cannot mutate these records. Running the existing role setup extended the existing Manager group; no users, passwords, staff flags or memberships were changed. Audit/history and outbox entries are read-only in Admin. There is no unrestricted backward-status override; exceptional corrections require a separately designed audited procedure.

## Notifications: deliberately disabled

Customer email policy: one order-confirmation email per order, plus one separate new-order alert to the configured admin. COD queues confirmation when placed; online orders queue it only after verified payment. Creation is serialized per order to avoid duplicate confirmations. Later confirmation/fulfillment/cancellation/refund events remain visible in My Account but do not queue customer emails. Legacy queued status emails are retained for audit and suppressed at delivery. Internal notes and ordinary page saves never send email. No address-specific delivery date is promised without configured delivery-time rules.

`ORDER_EMAIL_ENABLED=False` is the default. No email was sent to real customers. Configure a verified backend/sender and review development outbox entries before enabling production delivery. The worker is explicit:

```powershell
.\.venv\Scripts\python.exe manage.py send_order_notifications
```

The worker atomically claims pending messages, sends only public event fields and marks confirmed acceptance. It does not retry failed or ambiguous `sending` rows blindly: an email provider can accept a message just before a process failure, so those rows require reconciliation to avoid duplicates. SMTP acceptance is not a delivery receipt. No recurring worker or external messaging provider has been deployed yet.

## Deliberate boundaries

- No Google OAuth, Razorpay checkout, automatic courier integration, payments or real refunds added.
- Email changes require support/identity verification; no insecure editable-email account takeover path. Self-service verified email change and password recovery remain future work.
- Pet photos are deferred until private media delivery exists. Optional breed/DOB/weight are supported, with no medical recommendations.
- Return policy, refund accounting, notification transport/scheduling and exceptional corrections need production business rules.
- Shopify, Render and DNS remain untouched.

## Verification and commands

Migrations 0012 and 0013 are additive and applied. Check and migration-drift checks pass. Full regression suite: **156 tests passed with browser suites enabled**, followed by **20 focused account tests passed**, including four additional address-selection/pet/reorder/password cases. Shared staff-to-customer tracking and exact-pack reorder are exercised in a disposable browser fixture. Account layouts checked at 320/360/375/390/412/430/768/1024/1440px; CRM at seven widths including 320. Mobile tracker and desktop dashboard screenshots reviewed. This is the requested original SuryaVets-themed account design, not a Shopify pixel-match claim.

Final post-polish verification: **21 account unit/browser tests passed** (20 focused unit tests plus the nine-width shared tracking browser journey). System and migration-drift checks pass again.

Read-only comparison against the SQLite backup found zero changed/removed pre-existing order, order-item, product, variant, stock-ledger, address or User rows. New history is additive; existing stocks and payment state are unchanged.

Already applied; for a fresh checkout of this code, run from the existing project:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py setup_crm_roles
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_account_tracking shop.test_crm shop.test_checkout --noinput
```

For browser tests, use the documented local Node/Playwright/Edge environment variables as in the existing browser suites. Browser fixtures never create customer records in the real development database.

## Changed areas

- Models/migrations: `shop/models.py`, `shop/migrations/0012_*`, `0013_seed_existing_order_history.py`, read-only audit Admin registration.
- Shared services: `shop/services/order_tracking.py`, `reorder.py`, existing `crm.py` and `checkout.py`.
- Account: `shop/account_views.py`, `account_forms.py`, `templates/account/`, `static/css/customer-account.css`, existing routes/checkout address selection/product wishlist control.
- CRM: `crm_order_views.py`, existing views/forms/routes/templates/CSS and role setup command.
- Notifications: `management/commands/send_order_notifications.py`, settings and secret-free `.env.example`.
- Tests: `test_account_tracking.py`, `test_account_browser.py`, `account_browser_test.cjs`, updated strict workflow expectation in `test_crm.py`.
- Documentation: audit, this guide and migration checklist.

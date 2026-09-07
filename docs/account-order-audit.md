# Account and shared order tracking audit — 8 September 2026

## Before implementation

The supplied `Desktop/suryavets` folder does not exist. The existing running project is `C:/Users/danyb/Desktop/suryavets-django`; no replacement project is being created. Django checks pass. There are 3 users, 1 order, 1 order item and 1 address. The order is pending with payment pending. Tracked worktree was clean at `c2506c1`; unrelated untracked assets/scripts are preserved.

1. **Order:** UUID, unique SV order number, checkout idempotency key/cart, user (nullable for guests), email/phone, order/payment states and method/reference, shipping/billing address snapshots, Decimal subtotal/shipping/discount/total, coupon snapshot, customer notes, stock-deducted/ledger flags and created/updated dates.
2. **OrderItem:** original product and variant nullable references, purchased product name, variant name, SKU, Decimal unit price, quantity; line total is derived. No historical image reference yet.
3. **Payment:** pending/paid/failed/refunded, separate from fulfillment. COD checkout works; online payment is intentionally blocked. No Razorpay gateway or Google OAuth found. Do not mistake Gmail email/password login for Google sign-in.
4. **Order status:** pending → processing → shipped → delivered, with guarded pre-shipment cancellation. CRMActivity stores internal free-text changes, not a safe structured customer timeline.
5. **CRM:** dashboard, searchable/filterable order list, order detail, internal notes, controlled transitions, permission checks, compare-and-swap concurrency protection, audited cancellation/restocking. Payment data is read-only.
6. **Customer account:** login-required dashboard with ten recent orders, ownership-scoped UUID order detail, POST logout. No full history/tracker/reorder yet.
7. **Addresses:** user-owned multi-address model, add/list and default shipping selection at checkout. Missing edit/delete/default actions and explicit checkout selection.
8. **Wishlist:** absent.
9. **Pets:** catalog PetCategory exists; no customer pet profiles.
10. **Authentication:** Django User, email/password authentication, deterministic internal registration username and case-insensitive email checks, guest-cart merge, safe login redirects, password validators. No user model replacement needed.
11. **Permissions:** active staff + access_crm required. Operations/managers manage orders and notes; inventory and coupon permissions are separate. Customers never receive staff roles on signup.
12. **Required additive schema:** expanded order/payment choices; independent return state; courier/tracking fields; immutable order event history; event-specific notification outbox; historical item image reference; profile phone; owned pets/wishlist/support requests. Existing addresses reused.
13. **Data risks:** never infer missing milestone timestamps, convert guest orders into accounts by email matching, overwrite purchased prices, treat payment as delivery, automatically refund a cancellation, duplicate restocking, substitute unavailable packs, expose CRM notes or discard legacy UUID links. Existing return eligibility is undefined: requests must be staff-reviewed, not auto-approved. Existing physical inventory and payment records are not being changed by this feature.

## Plan and checkpoint

1. Add shared status history and guarded shipping transitions; preserve existing status values (`pending` displayed as Placed).
2. Extend CRM tracking, filters and attention counts; keep customer-visible notes separate from internal notes.
3. Build mobile account shell, order history/detail/tracker and exact-pack reorder on existing orders/cart.
4. Add owned pets, wishlist, address actions, profile/security and structured support.
5. Add a disabled-by-default email outbox; no live notifications or payments during development.
6. Run privacy/transition/reorder regression tests and responsive browser checks.

Git checkpoint: `codex/checkpoint-before-account-tracking-20260908`. Database backup: `tmp/pre-account-tracking-20260908.sqlite3`. Both precede schema changes. Historical events are backfilled only when a timestamp is known; unknown legacy milestones are explicitly marked as such.

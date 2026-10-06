# Production order emails

## Policy

- Successful placement (`pending`): exactly one admin alert, no customer email.
- CRM transition to `confirmed`: exactly one customer email, no second admin alert.
- Processing, packed, shipped, out for delivery, delivered, cancelled, payments
  and returns: no further customer emails. Status history is preserved.
- Online `awaiting_payment` is not successful placement. Verified payment moves
  the order to `pending` and queues the admin alert; CRM confirmation is separate.

Brevo and the existing HTML/plain-text templates are reused. Admin recipients
come from `ORDER_NOTIFICATION_EMAIL`; customer recipients come from their order.
The messages include purchased item/variant/SKU/price snapshots, address, totals,
payment details, and any coupon code. Internal notes are excluded.

## Render environment

```dotenv
DJANGO_EMAIL_BACKEND=shop.mail_backends.BrevoEmailBackend
BREVO_API_KEY=<existing-private-Brevo-key>
BREVO_SANDBOX=False
DEFAULT_FROM_EMAIL=<verified-Brevo-sender>
DEFAULT_FROM_NAME=SuryaVets
ORDER_NOTIFICATION_EMAIL=<business-alert-inbox>
ORDER_EMAIL_ENABLED=True
ORDER_EMAIL_AUTO_SEND=True
PUBLIC_SITE_URL=https://suryavets-django.onrender.com
```

Use Render's private environment settings, never Git. Keep
`ORDER_EMAIL_ENABLED=False` until the backend and sender are verified. Use True
for the controlled live test after deployment succeeds. Production sender-domain
authentication should be finalized for deliverability; provider acceptance alone
does not establish inbox delivery.

## Migration and history

Migration 0021 adds a nullable unique `deduplication_key`. Existing rows remain
NULL and are not enrolled, sent, deleted or changed. New keys are per order and
audience. Existing legacy notification records prevent re-enrollment of that
audience when older orders are later touched. Ordinary order saves do not enqueue
anything. A future explicit confirmation on an older order with no legacy
customer notification may enqueue a confirmation; deployment itself never does.

Apply migration before serving the new code (`python manage.py migrate`). Old
code remains compatible with the added nullable column during a rolling deploy.
Do not run a bulk outbox send during deployment. Interrupted `sending` or
ambiguous provider outcomes require reconciliation, not blind retry. Confirmed
rejections can be retried individually, using the same provider idempotency key.

## One-order production test

Use a NEW test order, not SV-71C1C4A067 (created under the old email policy).
Use an inbox you own; mark the order TEST—DO NOT DISPATCH and choose COD so no
online payment is charged. Agree to checkout terms yourself. Do not dispatch it.

1. Confirm the new deployment and migration have succeeded, and set the variables
   above with email sending enabled.
2. Place exactly one test order. Expect one admin subject:
   `New SuryaVets Order — <number>`. The customer inbox receives nothing yet.
3. Refresh the confirmation page: no extra email.
4. In CRM, change that order from Placed to Confirmed. Expect one customer subject:
   `Your SuryaVets Order <number> is Confirmed`. No new admin alert.
5. Repeat/refresh the status-save page: no duplicate confirmation.
6. Change Confirmed to Processing. Expect no further customer email.
7. Verify both actual inbox delivery and Brevo transactional logs. If admin and
   customer share an inbox, distinguish the two subjects and their event timing.
8. Keep the order marked as a test. Arrange staff-authorized cancellation and
   inventory restoration as appropriate; do not delete its audit history.

Read-only outbox inspection:

```powershell
python manage.py send_order_notifications --dry-run
```

This does not send or modify messages and excludes legacy rows. After inspecting
the specific provider result, a confirmed retryable rejection can be retried:

```powershell
python manage.py send_order_notifications --retry-failed <notification-id>
```

No recurring worker is provisioned by this change. Normal delivery runs after
the event transaction commits. Deferred/rate-limited rows need the existing
worker to run later; do not claim guaranteed delivery or automatically retry
unknown outcomes.

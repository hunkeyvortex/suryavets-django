# SuryaVets — Brevo transactional email setup

Implementation date: 13 September 2026. Existing application: `C:\Users\danyb\Desktop\suryavets-django` (not a new project).

## Current readiness

The account is now connected for **local testing**. On 13 September 2026, after you completed Brevo email/phone verification, the active API key named `surya` was saved in `.env.brevo.local.json` (Git-ignored, Windows access restricted to the owner and SYSTEM). Your existing Gmail sender is verified; no branded domain is configured yet. The API key expires on 12 September 2027 according to Brevo's UI.

Brevo accepted a sandbox request and then **one explicitly approved real connection-test email** to your own inbox. Brevo's transactional log shows **Sent and Delivered** for that single `[TEST] SuryaVets transactional email` at 03:08 on 13 September 2026. These are two events for one message, not two emails. Inbox/spam placement and Gmail/Outlook rendering still require checking by you. No customer/order emails were sent and the outbox was not processed. Domain authentication and production delivery setup are not complete.

The delivery log shows that Brevo rewrote the Gmail From address onto a `brevosend.com` address. This is suitable for this initial connection test, not the final branded sender. Configure and authenticate a SuryaVets-owned sender/domain before production mail; DNS remains untouched.

Use the local launcher (ordinary `manage.py` does not auto-load this private file):

```powershell
Set-Location 'C:\Users\danyb\Desktop\suryavets-django'
.\.venv\Scripts\python.exe brevo_local.py check
# Optional local server using the saved connection; order mail remains disabled:
.\.venv\Scripts\python.exe brevo_local.py runserver
```

`brevo_local.py` never enables order emails or drains the outbox. Its `test --to YOUR_INBOX` command uses sandbox by default; adding `--allow-live` sends a new real test on each invocation. Do not repeat the real test merely to inspect its status. The temporary credential-entry server has been stopped. No secret values are contained in the launcher or this document.

The local TLS issue was resolved using the project's existing `truststore` dependency and native OS certificate validation, scoped to the Brevo adapter. Certificate and hostname verification remain required; no unverified TLS context or security bypass was added. See [Truststore's native certificate API](https://truststore.readthedocs.io/en/latest/).

Razorpay/payment logic, Shopify, DNS and Render were not changed. Email delivery remains off unless explicitly enabled in the environment. Selecting Brevo defaults to sandbox mode.

## What was reused and changed

The existing order event → `OrderNotification` outbox → Django `EmailMultiAlternatives` flow is unchanged in principle. Existing checkout/status events create the notifications, not page loads. Customer/admin have separate rows under the existing unique event/channel/audience constraint. The backend is replaceable through Django `MAILERS`; application order code does not call the Brevo API.

- `shop/mail_backends.py`: small HTTPS API adapter, no new dependency; configurable timeout capped at 30 seconds; no redirects with credentials; validated response/message ID; sanitized errors.
- `shop/services/notifications.py`: reuse existing claims, subjects, absolute links and templates; save provider ID; sandbox state; bounded retry scheduling.
- `shop/models.py`, `shop/migrations/0015_brevo_outbox_delivery.py`: additive notification fields `provider_message_id`, `retryable`, `next_attempt_at`, plus `preview` state. No order/payment schema change or data rewrite.
- `shop/admin.py`: delivery/retry metadata visible in existing read-only notification admin.
- `shop/management/commands/send_order_notifications.py`: existing worker gains scoped processing and safe failed-row retry.
- `shop/management/commands/test_transactional_email.py`: explicit operator transport test through the same backend, not another notification system. Does not create orders.
- `shop/templates/emails/order.html`, `order.txt`: reused branded customer/admin content; added tracking links and explicit timezone. Email-compatible tables/inline styles and Outlook fixed-width fallback; no JavaScript.
- `suryavets/settings.py`, `.env.example`: environment configuration only, no keys.
- `shop/test_brevo_email.py`: mocked transport, outbox and optional browser tests.
- `brevo_local.py`: explicit local-only private configuration helper/launcher; never imported by production settings.

The customer email includes purchased item/variant/SKU/quantity/prices, totals, delivery address, actual payment status, and authenticated order/tracking links. Admin gets the same purchase snapshot plus customer contact information and an authorized CRM link. Internal notes are excluded. Guest emails deliberately omit private account links instead of exposing order data through a public URL. Historical item data comes from `OrderItem`, not current catalog prices.

## 1. Set up Brevo manually

1. Create/sign in to your own [Brevo account](https://app.brevo.com/). Complete any account/transactional-sending activation requested by Brevo. Confirm your account can send transactional mail and has available quota.
2. Open **Settings → Senders, Domains, IPs → Senders → Add a sender**. Use `SuryaVets` as the name and a mailbox you control, such as `orders@suryavets.com` if it exists. Complete the verification code sent to that mailbox when requested. An example address in this guide does not mean it is verified. See [Brevo sender setup](https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email).
3. For domain authentication, open **Settings → Senders, Domains, IPs → Domains → Add a domain**, enter `suryavets.com` (no `https://`), and select authentication. For an existing entry, use **Authenticate**. Brevo supplies account-specific verification TXT, DKIM TXT/CNAME and DMARC information. Copy only the exact records it provides; verify afterward in Brevo. Propagation can take up to 48 hours. See [official authentication instructions](https://help.brevo.com/hc/en-us/articles/12163873383186-Authenticate-your-domain-with-Brevo-Brevo-code-DKIM-DMARC).

**DNS boundary:** no DNS changes are authorized or performed in this task. Domain authentication is a later owner-approved manual step. Have your DNS administrator review Brevo's records before applying them. Preserve Shopify's website records, existing MX/mail delivery, and existing DKIM/SPF/DMARC policy; do not create duplicate SPF/DMARC records or accept automatic replacement of an existing DMARC policy blindly. A manually verified sender may allow initial testing subject to your Brevo account restrictions; it does not replace domain authentication for production readiness.

4. Open **Settings → SMTP & API → API keys → Generate a new API key**. Name it `SuryaVets development transactional email`, generate, and securely save it; Brevo displays it once. Use the **API key**, not an SMTP password or MCP key. Keep it out of screenshots, chat, Git and frontend code. Use a separate key for production later. [Official API key instructions](https://developers.brevo.com/docs/api-key-authentication).

## 2. Configure the local process

Settings currently read process environment. Merely creating `.env` does **not** load it automatically. Set variables in the terminal that starts Django and in the terminal that runs the worker. Restart existing processes after changing their environment. Do not print/dump the environment.

| Variable | Local test value / purpose |
| --- | --- |
| `DJANGO_EMAIL_BACKEND` | `shop.mail_backends.BrevoEmailBackend` |
| `BREVO_API_KEY` | Your secret Brevo API key, supplied locally |
| `BREVO_SANDBOX` | `True` initially; explicitly `False` for real inbox tests |
| `BREVO_TIMEOUT` | `15` seconds; code bounds it to 1–30 |
| `DEFAULT_FROM_NAME` | `SuryaVets` |
| `DEFAULT_FROM_EMAIL` | The sender address verified in your account |
| `ORDER_NOTIFICATION_EMAIL` | Your controlled admin test inbox |
| `PUBLIC_SITE_URL` | `http://127.0.0.1:8000` locally; actual HTTPS Django origin later |
| `ORDER_EMAIL_ENABLED` | `True` for explicit tests, otherwise `False` |
| `ORDER_EMAIL_AUTO_SEND` | `False` while testing, so order events queue until explicitly processed |

Use only your own inboxes for tests. `PUBLIC_SITE_URL` must point to Django, not the live Shopify domain. A localhost link only opens on the development computer, not a phone or someone else's computer. Do not send localhost links to customers.

PowerShell, in the same terminal (prompts avoid storing the key as literal shell history):

```powershell
Set-Location 'C:\Users\danyb\Desktop\suryavets-django'
$env:DJANGO_EMAIL_BACKEND = 'shop.mail_backends.BrevoEmailBackend'
$env:BREVO_SANDBOX = 'True'
$env:BREVO_TIMEOUT = '15'
$env:DEFAULT_FROM_NAME = 'SuryaVets'
$env:DEFAULT_FROM_EMAIL = Read-Host 'Verified sender address'
$env:ORDER_NOTIFICATION_EMAIL = Read-Host 'Your admin test inbox'
$env:PUBLIC_SITE_URL = 'http://127.0.0.1:8000'
$env:ORDER_EMAIL_ENABLED = 'True'
$env:ORDER_EMAIL_AUTO_SEND = 'False'
$brevoSecureKey = Read-Host 'Brevo API key (hidden)' -AsSecureString
$env:BREVO_API_KEY = [System.Net.NetworkCredential]::new('', $brevoSecureKey).Password
Remove-Variable brevoSecureKey
.\.venv\Scripts\python.exe manage.py check
```

The environment value must be plaintext in process memory for the HTTP client; protect the local user session. Never run `Get-ChildItem Env:` or print the key when sharing logs. Closing the terminal discards these process-level settings. `.env.example` contains only blank names for the new Brevo settings.

## 3. First sandbox test (no inbox delivery)

```powershell
$brevoTestInbox = Read-Host 'Your own test inbox'
.\.venv\Scripts\python.exe manage.py test_transactional_email --to $brevoTestInbox
```

This uses the same backend with an explicit `[TEST]` subject and no fake order. Brevo sandbox uses `X-Sib-Sandbox: drop` inside the API payload headers. A successful response has a message ID, but **does not deliver mail or create Brevo email logs**. It tests request validity, not inbox delivery. [Brevo sandbox documentation](https://developers.brevo.com/docs/using-sandbox-mode).

Without Brevo credentials, keep `DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` for offline previews. Enabling email with that backend prints content locally; protect logs because they contain order/customer data. Console acceptance is not delivery and is not replayed later through Brevo.

## 4. One real transport test, only after sender setup

```powershell
$env:BREVO_SANDBOX = 'False'
.\.venv\Scripts\python.exe manage.py test_transactional_email --to $brevoTestInbox --allow-live
```

Check the returned provider message ID in Brevo **Transactional → Email → Logs**, your inbox and spam folder. Verify the From identity and authentication results in message headers. `201`/message ID means provider acceptance, not guaranteed inbox delivery. If the result is uncertain, inspect Brevo first; the diagnostic command is a separate explicit test on every invocation, not an idempotent order notification.

## 5. Test the real customer + admin templates

1. Keep `ORDER_EMAIL_AUTO_SEND=False`; start Django from the configured terminal using `.\.venv\Scripts\python.exe manage.py runserver 8000`. Do not start another copy on an occupied port: restart the existing local server with these variables.
2. Log in using your own test customer account/email. Add a known variant and place one local **COD** order. This exercises the existing flow without changing payment settings or charging anything.
3. Open `/admin/shop/ordernotification/` with an authorized staff account. Find the **new** order's customer and admin notifications and note each numeric notification ID. Confirm both recipients are inboxes you control. Do not process the old backlog during testing.
4. In another terminal configured identically, process only those IDs (replace `123` and `124`):

```powershell
.\.venv\Scripts\python.exe manage.py send_order_notifications --notification-id 123
.\.venv\Scripts\python.exe manage.py send_order_notifications --notification-id 124
```

5. In sandbox these become `preview`; no inbox delivery occurs. In live mode they become `sent` on API acceptance, with a timestamp/provider ID. Switching sandbox off will **not** resend preview rows. Use a new test order for the live template test.
6. Verify one customer email and one admin email, exact purchased variant/quantity/prices, correct COD pending-payment wording, shipping address and links. Refresh the confirmation page and run the two scoped commands again: no additional emails should be accepted.
7. Open both in Gmail mobile/desktop and Outlook. Check wrapping, rupee signs, CTA links and long product titles. Browser layout tests are useful but do not certify email-client rendering.

Customer links require login and ownership; admin CRM links require staff permissions. No tracking secret or unprotected private order link is introduced. Email dates show the configured Django timezone explicitly.

## 6. Failures, retries and duplicate protection

The same persistent outbox row is atomically claimed before a send. Accepted/preview rows are never selected again. Browser refresh and process restart do not create a new claim. A deterministic per-notification idempotency key is also included in the Brevo payload; provider deduplication has a limited window and does not replace the local guard. Brevo documents a **30-minute** window in its [idempotency guide](https://developers.brevo.com/docs/heterogenous-versions-batch-emails). Do not assume exactly-once delivery across arbitrary network failures.

| State / error | Action |
| --- | --- |
| `pending`, zero attempts | May be disabled, missing/invalid recipient, a non-customer-visible event or blocked by the existing payment guard. Inspect configuration; no guessing recipients. |
| `pending`, `brevo_http_429` | Rate limited; retry only once `next_attempt_at` is due. Worker must run again. Exponential backoff honors numeric Retry-After, with bounded attempts. |
| `failed`, retryable, attempts below 5 | Confirmed rejection/configuration problem (e.g. missing key, HTTP 401/403/422). Fix its cause, then explicitly retry that row. |
| `failed`, non-retryable | Timeout, 400, 5xx, malformed response or other uncertain outcome. Review provider logs first; normal retry command refuses it. |
| `sending` after a crash | Acceptance might already have happened. Never reset blindly. Match provider logs by notification reference/recipient/time; ask an engineer to reconcile with an audit record. |
| `preview` | Sandbox accepted; no delivery. Terminal state, not a pending real email. |
| `sent` | Backend/provider accepted; not a delivery/bounce guarantee. Existing console-backend rows also use this historical state. |

```powershell
# Example only: after fixing a confirmed rejection for this specific row
.\.venv\Scripts\python.exe manage.py send_order_notifications --retry-failed 123
```

Maximum five send attempts per notification; no infinite retry. Rate limits reschedule automatically in the DB, but no background scheduler is installed by this change. Other safe errors require explicit retry. Ambiguous sends deliberately require operator reconciliation rather than risking duplicate customer emails. Error fields/logs contain static codes and row IDs, not raw API responses or keys. Email failures do not delete/invalidate orders.

Do not manually alter old states or delete outbox rows to resend. Automated delivered/bounced webhook ingestion is not implemented in this scope; use Brevo's transactional logs for now. Check failures, stuck `sending` rows, quota and backlog routinely before production use.

## 7. Later Render configuration (not deployed now)

Add the same variables to secure Render environment settings. Use a separate production key, verified branded sender, real admin recipient, actual HTTPS Django origin, `BREVO_SANDBOX=False`, and `ORDER_EMAIL_ENABLED=True` only after acceptance tests. Keep credentials out of render.yaml/Git. Set `ORDER_EMAIL_AUTO_SEND=False` with a reliably scheduled worker running `python manage.py send_order_notifications`; otherwise enabling auto-send attempts delivery after commit but still requires the worker for delayed retries. Agree on scheduling, alerts, volume limits and backup/recovery before launch. Do not enable a worker against an unreviewed migration backlog.

The API uses HTTPS on port 443 rather than SMTP. No hosting plan, DNS, Shopify or deployment change was made.

## 8. Verification commands and remaining gates

Validation completed locally on 13 September 2026:

- `manage.py check`: passed; `makemigrations --check --dry-run`: no changes.
- Full suite: **198 tests passed**, browser runtime enabled, no skips (402.936 seconds).
- New Brevo-specific suite: 15 tests, including both email layouts at 320/390/600px; all passed with browser runtime enabled. External Brevo HTTP was mocked.
- Migration 0015 applied after SQLite backup `tmp/before-brevo-20260913.sqlite3`. Existing columns/rows in orders, items, payment attempts, notifications and status history match that backup exactly.
- Git checkpoint before implementation: `codex/checkpoint-before-brevo-20260913`.
- Browser artifacts: `C:\Users\danyb\Documents\ChatGPT\suryavets-django\brevo-email-verification`. These are test fixtures, not customer emails or real payment/provider transactions.

```powershell
Set-Location 'C:\Users\danyb\Desktop\suryavets-django'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_brevo_email shop.test_purchase_flow --noinput
```

All Brevo network calls in the new tests are mocked. Optional browser test uses the existing `SURYA_BROWSER_NODE`, `SURYA_PLAYWRIGHT_MODULE`, `SURYA_BROWSER_EXECUTABLE`, `SURYA_BROWSER_ARTIFACTS` environment settings and checks both HTML templates at 320, 390 and 600px.

Before production acceptance: verified sender/domain, configured key, successful sandbox request, one real transport test, one customer/admin order pair, live mailbox/client verification, repeat-send check, a tested worker schedule and monitoring. The implementation is ready to start these controlled tests, not a claim that they have already happened.

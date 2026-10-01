# Cart quantity autosave — 26 September 2026

The cart's +/− controls and typed quantities now save automatically. Line totals, subtotal, delivery, estimated total, free-delivery progress and cart badges use the server's Decimal-based values. JavaScript hides Update; the ordinary CSRF-protected form remains usable without JavaScript.

Changes are debounced for 350 ms and serialized across cart rows. Rapid edits retain the latest requested absolute quantity. Stock rejection restores the saved quantity. Unconfirmed network changes show Retry and prevent checkout until resolved. No inventory is reserved by cart edits.

## Files changed for this task

- `shop/views.py`: existing quantity endpoint returns an optional JSON snapshot; stock checks and cart ownership retained.
- `shop/services/cart.py`: shared authoritative cart snapshot.
- `shop/static/js/cart.js`: autosave queue, totals, counts and failure handling.
- `shop/templates/basket.html`, `shop/static/css/basket.css`: row identifiers and accessible saving/error feedback.
- `shop/test_cart_autosave.py`: ten backend regression tests.
- `shop/test_cart_autosave_browser.py`, `shop/cart_autosave_browser_test.cjs`: isolated browser tests for rapid clicks, typing, network retry, stock limits, persistence and no-JS fallback.
- `shop/checkout_browser_test.cjs`, `shop/variant_browser_test.cjs`: existing purchasing tests now wait for automatic saves instead of clicking Update.

## Verification

`python manage.py check` passed. All 53 selected tests passed, with browser tests enabled (116.436 seconds). Existing variant and checkout tests include nine viewport widths from 320 to 1440 pixels. Tests used disposable data; no real orders, inventory, prices, emails or payments were changed. Local cart and updated script returned HTTP 200 after restarting the preview at http://127.0.0.1:8000/.

Run from `C:\Users\danyb\Desktop\suryavets-django` in PowerShell:

```powershell
.\.venv\Scripts\python.exe manage.py check
$env:SURYA_BROWSER_NODE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:SURYA_PLAYWRIGHT_MODULE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:SURYA_BROWSER_EXECUTABLE='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
.\.venv\Scripts\python.exe manage.py test shop.test_cart_autosave shop.test_cart_autosave_browser shop.test_checkout_browser shop.test_variant_browser shop.test_coupon_browser shop.tests shop.test_checkout --noinput
```

Tracked work was checkpointed before changes on `codex/cart-autosave-checkpoint-20260926` (`02c1d71bc60075cf16408ae3c32759ecf2c21817`). Existing untracked work was preserved in place. No schema migration is needed. Shopify and DNS were untouched.

# Inline product cards — 8 September 2026

The approved green/gold card concept is implemented in the shared Django card component. It applies to homepage product sections, collection grids, search, recommendations and wishlist cards. This is an explicitly requested redesign, not a claim of Shopify visual parity.

## Behaviour

- Real active pack options, including verified linked source products, appear as selectable chips. Additional options use a collapsible More sizes section.
- Selecting a pack updates its exact current price, MRP, saving, discount, stock limit and assigned photograph. Missing exact pack photos remain visibly unavailable rather than borrowing another pack's artwork.
- The card includes quantity controls, Add to Cart, wishlist access and a product-detail link. Anonymous wishlist access goes through login. Without JavaScript, customers follow the product-detail link to choose a pack.
- Every purchase uses the existing server-side cart validation. Client price fields cannot change the charged price, and a linked pack retains its actual source product and variant IDs.
- No product records, stock, images, orders or schema were changed. The mockup's illustrative sizes were not imported. Previously missing photos still need verified source assets.

## Files

- `shop/services/product_cards.py`: read-only pack presentation.
- `shop/templatetags/shop_filters.py`: shared template tag.
- `shop/templates/includes/product_card.html`, `product_card_v2.html`, `card_variant.html`, `card_heart.html`: reusable markup.
- `shop/static/css/product-cards-v2.css`, `shop/static/js/product-cards.js`: responsive styling and isolated per-card controls.
- `shop/templates/base_shared.html`: assets loaded globally.
- `shop/account_views.py`: wishlist prefetching.
- `shop/test_product_cards.py`, `shop/variant_browser_test.cjs`: regression coverage.

## Verification

Run from `C:\Users\danyb\Desktop\suryavets-django`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test shop --noinput
```

Django checks pass; no migration changes are detected. The standard suite reports 167 tests, OK with 8 opt-in browser tests skipped. The separate browser run enables `SURYA_BROWSER_NODE`, `SURYA_PLAYWRIGHT_MODULE` and `SURYA_BROWSER_EXECUTABLE` for the two variant fixtures: a single source with several packs, and verified linked source packs. Each runs at 320, 360, 375, 390, 412, 430, 768, 1024 and 1440px, checking inline selection, prices, photographs, stock, quantity, cart identity, detail-page buying and overflow. Screenshot fixtures use solid colour test images, not production photographs.

Safe pre-change branch: `codex/checkpoint-before-inline-product-cards-20260908`.
Refresh `http://127.0.0.1:8007/` or `/categories/`; use Ctrl+F5 if old assets are cached. No database commands or new server port are needed to use the change.

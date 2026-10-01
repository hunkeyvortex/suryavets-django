# Homepage and mobile discovery refresh — 26 September 2026

## Reference and scope

Compared `Desktop/PetCareCRM` (Boww & Meow) homepage, shared layout, homepage
styles, mobile dock and category-sheet behavior with SuryaVets. Captured both
sites at 390px and 1440px. The Boww preview used a SQLite `mode=ro` connection
and disabled email; its source and catalog were not changed.

This follows the owner's new direction to adapt Boww & Meow's shopping/mobile
patterns, not to maintain pixel parity with Shopify. SuryaVets retains its logo,
green identity, existing campaign artwork, trust boxes and checkout backend.
The result is an adaptation, not a claim of an exact copy of Boww & Meow.

Tracked-work checkpoint: `codex/homepage-refresh-checkpoint-20260926`, commit
`f089b0333122088675108a4c15a301ffdb06268a`. Existing untracked work was preserved.

## What changed

1. Compact mobile search/header and a horizontal category shortcut strip.
2. Mobile Home / Categories / Cart / Wishlist / Account dock, safe-area padding
   and a native modal category sheet (Escape, focus restoration, backdrop close).
   The original hamburger retains the complete nested category tree.
3. Existing hero slider retained, with pause/play, focus/hover/hidden-tab pause,
   reduced-motion support, inactive slides removed from keyboard navigation,
   and clearer slide indicators.
4. Four service/trust boxes remain a fixed, non-sliding row.
5. Six visible pet cards, three columns on phones, linking to Django categories.
6. Dog/Cat food tabs with reusable product cards and two columns on phones.
   Tabs also support arrow keys, Home/End and useful no-JavaScript links.
7. Best-seller rail with working controls, plus Shop by need and Shop by brand.
8. Existing shipping banner links to shipping information; a contact section
   provides a clear support route. Account header now links signed-in users
   directly to My Account, and icon-only cart/account links have accessible names.

## Data and buying behavior

- Homepage categories and catalog products come from Django. Food sections use
  the actual category hierarchy, including descendants and collection membership.
- Inactive products and linked family children are not duplicated as cards.
- Uses the same variant-aware product-card component, hidden quantity=1 and
  server-side cart behavior as the catalog. No new or parallel cart system.
- A bounded 48-candidate window per product section prefers real images for the
  selected pack. It never substitutes another pack's image or modifies records.
- Checked the real rendered selection: six best-seller cards with six images;
  four Dog food cards with four images; four Cat food cards with four images.
- Brand counts include active canonical listings; uploaded logos are supported,
  with honest text names when no logo has been uploaded.
- IMPORTANT: 6,180 active canonical products were already marked best sellers
  and featured in the imported data. The section uses those existing flags, not
  measured sales. Merchant curation is still needed. If no best-seller flags exist,
  the section uses featured products and is labelled "Featured picks" instead.
- No schema, price, stock, product visibility, review-enforcement, payment,
  email, live Shopify or DNS changes were made.

## Changed application files

- `shop/views.py`, `shop/services/homepage.py`
- `shop/templates/home_new.html`, `shop/templates/base_shared.html`
- `shop/templates/includes/header.html`, `ui_icon.html`,
  `home_product_section.html`, `mobile_shortcuts.html`, `mobile_dock.html`
- `shop/static/css/home-discovery.css`, `mobile-commerce.css`
- `shop/static/js/storefront.js`, `home-discovery.js`, `mobile-commerce.js`
- `shop/test_home_discovery.py`, `shop/test_home_discovery_browser.py`,
  `shop/home_discovery_browser_test.cjs`

## Verification

- Django checks pass; no model/migration drift.
- Initial focused run: 45 tests passed (homepage/catalog/product-card coverage).
- New isolated browser test passed: 320, 360, 375, 390, 412, 430, 768, 1024 and
  1440px. Verified no page overflow, fixed trust row, two/four food columns,
  tabs/keyboard selection, modal/drawer close, reduced-motion slider controls.
- Selected the 6 KG test pack and added it to the cart: correct pack, quantity 1,
  current price 180. This used disposable test data, not the owner's cart.
- All 17 distinct category/brand discovery URLs returned HTTP 200 locally.
- Real-catalog homepage Django-client measurement during the wider test run:
  1.58 seconds, 29 queries. Candidate scans are bounded, not full-catalog Python
  loads. This is not a production load-test result.
- Full `manage.py test shop --noinput` with browser tests enabled: **253 passed,
  no skips**, in 278.448 seconds. Payment and email integrations were mocked;
  commerce actions ran only against disposable test records.

Screenshots/reference captures:
`C:/Users/danyb/Documents/ChatGPT/suryavets-django/homepage-refresh/`.

From the application directory, repeat the functional checks with:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test shop.test_home_discovery shop.test_catalog_performance shop.test_product_cards --noinput
```

Browser test: `manage.py test shop.test_home_discovery_browser --noinput`, with
the existing `SURYA_BROWSER_NODE`, `SURYA_PLAYWRIGHT_MODULE` and
`SURYA_BROWSER_EXECUTABLE` runtime variables configured.

Local preview: http://127.0.0.1:8000/ . Refresh an already-open tab to load the
new styles. Product-data approval and remaining migration launch blockers are
separate work; this refresh does not certify them.

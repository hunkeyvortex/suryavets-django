# SuryaVets — Shopify parity audit

## Owner-directed homepage refresh — 26 September 2026

The owner requested Boww & Meow-style homepage discovery and mobile navigation,
superseding strict Shopify visual parity for these surfaces. Implemented dynamic
pet/need/brand sections, dog/cat food tabs, catalog-flagged best sellers, a mobile
dock/category sheet and accessible slider controls while retaining SuryaVets
branding and the shared variant/cart flow. Compared local reference screenshots
and tested nine widths; full suite: 253 passed with browser tests enabled, no
skips. See `HOMEPAGE_REFRESH.md`. This does not resolve data-verification or launch
blockers; imported best-seller flags still need merchant curation.

## Performance follow-up — 26 September 2026

The local collection/search performance failure has been addressed without changing catalog data or review-only mode. Listings now avoid unnecessary family-price calculations, repeated counts and multiplying joins; price/availability queries use indexed family lookups. The restarted local server returned HTTP 200 in roughly 0.8–1.6 seconds for ordinary Dog/search requests and 1.0–2.2 seconds for the sampled price-controlled requests, versus the prior eight-second timeouts. See `CATALOG_PERFORMANCE.md` for exact samples, query changes and regression coverage. These are local measurements, not production-load certification. The dated audit matrix below remains the historical baseline; all other launch blockers remain open.

## Implementation follow-up — 25 September 2026

The first catalog-integrity increment is implemented in **review-only mode**: CRM review queue, explicit reviewer permission, source/count attestations, validation of exact SKU/price/image requirements, signed stale-form protection, content fingerprints and immutable-in-admin decision history. Migration 0016 adds review metadata only. Existing prices, stock, product visibility, orders and staff assignments were preserved; no real products were auto-approved.

**Publication/purchase enforcement is not implemented or enabled.** The safety review blocked an immediate all-catalog purchase restriction because all existing products would initially be unapproved. Explicit owner approval for that rollout is outstanding. Accordingly the P0 catalog-safety finding remains open; current shopping behavior is unchanged. See `CATALOG_REVIEW_GUIDE.md` for access, verification and rollout boundaries. The 22 September matrix below remains the dated audit baseline, not a claim that this stage resolves every catalog risk.

Audit refreshed: 22 September 2026 (baseline: 13 September 2026). Scope: read-only application/data review, public storefront inspection and isolated automated tests. **Decision: do not leave Shopify yet.**

Actual repository: `C:\Users\danyb\Desktop\suryavets-django` (not the absent `Desktop\suryavets`, and not the separate Documents workspace). Audited HEAD: `263dd90`, plus the existing uncommitted Brevo work. No application features, payment code, inventory, Shopify records, DNS or deployments were changed for this audit.

## Executive assessment

**Estimated overall functional parity: approximately 60% (judgment range 55–65%), not a launch-readiness percentage.** The customer purchase and CRM foundations are substantially implemented, but several business controls, data-quality requirements, SEO and operational capabilities are missing. This is a confidence-qualified engineering estimate across the 21 areas below, not a count of rendered pages or a claim of pixel parity. Numerous small PASS items cannot cancel a P0 failure. Merchant-only Shopify configuration remains unverified.

Matrix coverage: **253 feature rows across 21 areas: 103 PASS, 98 PARTIAL, 40 MISSING, 8 BROKEN, 4 LATER, 0 NOT REQUIRED.** Rows overlap, so these are not 253 independent projects. A simple unweighted cross-check (PASS = 1, PARTIAL = 0.5, excluding LATER) is about 61%; the rounded 60% estimate does not imply that money, security or fulfillment risks can be averaged away.

**Build next: catalog approval/publication safeguards with ledger-aware reconciliation.** The read-only export comparison is now complete; do not repeat it or create another catalog. Extend the existing import/CRM tools so only approved sellable packs, prices, stock and images can be published. Preserve the 6,695 existing stock movements and prevent unapproved zero-price/unverified items from becoming purchasable. Owner approval and a fresh inventory source are prerequisites for applying quantities. A blanket reimport or setting everything to 10 is not a production stock strategy.

### What changed in this refresh

- All **199 existing tests passed** again, including enabled browser tests, with no skips. This verifies their assertions, not untested business rules or production integrations.
- New form-only reproduction: `CheckoutForm` accepts phone `abc`, shipping PIN `not-a-pin` and a different billing PIN `bad` with no errors. No order was created. Saved-address PIN validation does not protect checkout. Delivery-address status is now BROKEN.
- Both imported-data collection/search probes still exceeded eight seconds after the test run completed. Homepage and empty cart responded normally.
- Live/mobile inspection now includes actual measured widths 320, 360, 375, 390, 412, 430 and 768. The previous hidden-browser mobile limitation was overcome for homepage/collection measurements; this does not certify whole-site pixel parity.
- Existing Brevo delivery proof is historical evidence from the earlier setup, not a new email sent by this audit. Provider credentials, sender configuration and inbox delivery were not revalidated here.

### Measured local data

Aggregate-only database inspection; no customer records or secrets included in this document.

| Measurement | Observed value | Interpretation |
| --- | ---: | --- |
| Products / active products | 6,697 / 6,697 | Active does not mean commercially verified |
| Active canonical listings | 6,420 | 277 sibling product records are grouped under canonical listings |
| Variants / active variants | 6,677 / 6,677 | Exact variant architecture exists |
| Variants with stock exactly 10 | 6,676 | Development override, not reconciled live availability |
| Variants with zero stock | 0 | Stock-out behavior is tested with fixtures, not represented realistically in this dataset |
| Variants with explicit selling price zero | 92 | Money-integrity launch blocker unless individually approved as genuinely free |
| Zero-price purchasable options, including simple products | 96 | 92 variants plus 4 simple-product options; all also zero in the supplied export |
| Products with base price zero | 95 | Separate measure; do not add it to the 92 variant count |
| Variants with blank SKU / populated barcode | 130 / 0 | Identity reconciliation gap; barcode may not be used by this merchant |
| Active image records | 2,619 | Several images may belong to one product |
| Products without their own active image | 4,342 | Includes grouped siblings |
| Canonical listings without own OR sibling active image | 4,124 | About 64% of canonical listings lack a real attached family image |
| Missing files among nonempty active image paths | 0 | Existing files are present locally; this is not proof of production persistence or semantic correctness |
| Variants with explicit image assignment | 152 | Product/family fallback is common; verify exact pack artwork |
| Active products with blank description | 2,223 | Content completeness gap |
| Nutrition reviewed/published | 0 | Do not invent medical/nutrition facts to fill this |
| Categories / brands | 170 / 569 | Hierarchical category model and vendor model are populated |
| Local orders | 3, all `pending` | Not an import of Shopify order history |
| Inventory movements | 6,695 | Snapshot import guards intentionally refuse blind overwrite |
| Notification rows | 3, all `pending` | Do not drain this queue as part of an audit |

The live Dog collection and search also exposed zero-priced items. This means some source data itself needs approval; faithfully importing it is not enough. Another visible identity warning: the live Urinary S/O URL ends `1-2kg`, while the displayed pack is `1.5KG`. Local homepage also displayed a product title containing `80g` beside a `70GM` option. Resolve identity against approved packaging/export data; never infer pack identity from a URL alone.

### Export reconciliation already completed

Read-only report: [22 September catalog comparison](C:/Users/danyb/Documents/ChatGPT/suryavets-django/catalog_audit/review-2026-09-22-final/REPORT.md). All 6,697 exported purchase options matched by exact handle/options/SKU equality, with blank SKUs explicitly flagged; there were zero price differences against those historical files. This is source agreement, not price approval. The inventory file covers only 12 entries at one location, with seven quantity differences and no populated SKUs. It is not a full-store stock source. Product exports contain 6,280 nonnegative stock differences and 411 negative balances requiring separate review; missing inventory rows must not become zero, and negative balances must not be silently clamped. All 4,124 image-less canonical listings also lack usable image references in the supplied product export, so reimporting it cannot fill those gaps. Fresh exports, exact-product assets and owner decisions remain necessary. The comparison preserved the database hash, three orders, three order items and all 6,695 stock movements.

## Evidence and limitations

### Public reference pages inspected

| Evidence | Reference URL | What was actually verified |
| --- | --- | --- |
| S1 | [Homepage](https://suryavets.com/) | Whole-page public structure, nested navigation expanded through Cat/Medicine, three slide controls, six pet links, Top Selling, newsletter/footer; current 390px screenshot and all seven requested mobile-width measurements |
| S2 | [Dog collection](https://suryavets.com/collections/dog) | Category tree, price/type/brand/sort controls, 24 first-page products and pagination; zero-price listing observed |
| S3 | [Discounted Royal Canin product](https://suryavets.com/products/rc-urinary-s-o-cat-dry-food-1-2kg) | Vendor, selected pack, current/compare price, Add to Cart, benefits, recommendations and reviews; canonical and JSON-LD present |
| S4 | [Regular-price Condrovet product](https://suryavets.com/products/condrovet-large-dog-tablet-10tab) | Single displayed pack, regular price without discount, vendor, buying control and review area |
| S5 | [Search for royal](https://suryavets.com/search?q=royal) | Current mobile search, Filter and grid controls, 24 first-page cards including a zero-priced item; 232 total was the earlier desktop observation, not re-counted in this refresh |
| S6 | Cart drawer, opened from S5 | Earlier inspection showed empty state, close/login/continue links. Current mobile revisit opened a dialog with only its close control exposed; content did not populate in the observation window. No merchandise added; populated live cart remains unverified |
| S7 | [Account entry](https://suryavets.com/account) | Earlier inspection redirected into Shop/Shopify authentication and upstream `shop.app` timed out. Login completion, Google options and private account contents **not verified**; no new authentication attempt in this refresh |
| S8 | [Shipping policy](https://suryavets.com/pages/shipping-policy) | India shipping, checkout-calculated charges, selected-location COD, processing/delivery guidance |
| S9 | [Returns policy](https://suryavets.com/pages/return-and-refund-policy) | Pre-dispatch cancellation, restricted categories, seven-day request window, inspection, conflicting 2–5 and 5–7 business-day refund wording |
| S10 | [Contact](https://suryavets.com/pages/contact), [About](https://suryavets.com/pages/about-us), [Privacy](https://suryavets.com/pages/privacy-policy), [Terms](https://suryavets.com/pages/terms-and-conditions) | Public main content read in this refresh, including contact fields/hours, store introduction, privacy topics and terms. No form submitted. Approved Django policy wording and operational equivalence remain a review gate |

Public-only means Shopify admin inventory, installed apps, tax settings, gateway settings, actual fulfillment integrations, discounts, automations, customer exports and reports cannot be certified. No live order, payment, signup, marketing subscription or cart mutation was performed. Tests used disposable Django records and mocked payment/email integrations, not real charges.

Platform capability is distinct from merchant usage. Official references: Shopify supports [discount types](https://help.shopify.com/en/manual/discounts/discount-types), including product/collection restrictions and free-shipping promotions; [discount methods](https://help.shopify.com/en/manual/discounts/discount-methods) include codes and automatic application. Shopify provides [sales reports](https://help.shopify.com/en/manual/reports-and-analytics/shopify-reports/report-types/default-reports/sales-report) and [URL redirect management](https://help.shopify.com/en/manual/online-store/menus-and-links/url-redirect). These references establish capability, **not that SuryaVets has configured every option**.

### Code evidence map

Paths below are relative to the actual repository named above.

| Evidence | Files inspected / responsibility |
| --- | --- |
| D1 | `shop/models.py`, `shop/migrations/0001*` through `0015*`: catalog, accounts, cart, orders, events, ledger, coupons, payment attempts, notification outbox |
| D2 | `shop/urls.py`, `shop/crm_urls.py`, `suryavets/urls.py`: active route registration, missing SEO/recovery endpoints |
| D3 | `shop/catalog_views.py`, `shop/services/pricing.py`, `variants.py`, `pack_families.py`, `product_cards.py`, `navigation.py`: discovery, family pricing, selected variants, navigation |
| D4 | `shop/views.py`, `shop/forms.py`, `shop/services/cart.py`, `checkout.py`, `coupons.py`: authentication, cart, checkout, money and stock validation |
| D5 | `shop/account_views.py`, `shop/account_forms.py`, `shop/services/accounts.py`, `reorder.py`: owned account resources, pets, wishlist, support and reorder |
| D6 | `shop/crm_views.py`, `shop/services/crm.py`, `order_tracking.py`, `setup_crm_roles.py`: staff permissions, orders, history, cancellation, reports |
| D7 | `shop/services/payments.py`, payment routes in `shop/views.py`, `reconcile_test_payment.py`: TEST-only payment verification and manual uncertain-create reconciliation |
| D8 | `shop/services/notifications.py`, `shop/mail_backends.py`, `send_order_notifications.py`, `BREVO_EMAIL_SETUP.md`, `brevo_local.py`: existing email integration; secrets not printed |
| D9 | `import_shopify_products.py`, `reconcile_shopify_inventory.py`, `restore_shopify_prices.py`, `audit_product_media.py`: CSV/stock/media migration tools |
| D10 | `shop/templates/base_shared.html`, `home_new.html`, `includes/*`, `catalog/*`, `accounts/*`, `crm/*`, active CSS/JS: presentation. Unused `legacy/base.html` does not provide active canonical/OG tags |
| D11 | `suryavets/settings.py`, `requirements.txt`, `.gitignore`: environment, database, media, static and production security |
| D12 | Existing `shop/test_*.py`, `shop/*_browser_test.cjs`: unit/integration/browser assertions and screenshots |

### Verification results

- `python manage.py check`: PASS, zero issues.
- `python manage.py makemigrations --check --dry-run`: PASS, no changes detected.
- `python manage.py showmigrations shop`: all 15 migrations applied locally.
- Full `python manage.py test shop --noinput` with browser runtime enabled: **199 tests, PASS, no skips, 424.482 seconds** on 22 September. Failure messages printed by mocked email-failure tests are expected test scenarios, not failures of this run. Baseline 13 September run: 199 PASS in 240.914 seconds; these are not comparable performance benchmarks.
- Local `/` returned 200 in 0.244 seconds; empty `/cart/` returned 200 in 0.156 seconds in the refreshed bounded HTTP probe.
- Local `/category/dog/` and `/search/?q=royal` each exceeded an **8-second HTTP timeout** with the imported dataset, repeated after the tests completed. This is a real-data performance failure, not an asserted final response time or evidence of a 500. Profile queries before release and repeat on production-like PostgreSQL. Small-fixture test success does not cover this scale.
- The server subsequently logged a 200 for the timed-out search request; it was slow, not proven broken rendering. The Dog request had no completion recorded before the temporary audit server was stopped. Client timeout does not cancel server-side query work.
- `/sitemap.xml`, `/robots.txt`, `/collections/dog`, `/products/rc-maxi-dermacomfort-dog-dry-food-3kg`, `/pages/shipping-policy`: **404** locally.
- Checkout format reproduction used only `CheckoutForm.is_valid()` with fixture data: invalid phone and both PINs accepted. No checkout POST, payment or email was performed against the real database.
- Baseline desktop comparison was at measured 1280px. The current local desktop screenshot was 1440px, but the live tab retained 390px during the attempted paired desktop resize; that pair is **not matching-desktop evidence**. No fresh desktop pixel-match claim is made.
- Current live/local homepage screenshots were compared at actual **390px**. Broad order and brand assets align; hero presentation, trust-box typography, vertical spacing and selected products differ. Product-card, account, cart and checkout redesigns were explicitly requested by the owner and are not defects merely because they differ from Shopify.
- Live homepage and Dog collection, plus local homepage/login/register, had no document-level horizontal overflow at measured 320/360/375/390/412/430/768px. Live product widths were only reliably recorded at 320/360/375/412/430; two resize readings lagged and are not evidence for 390/768. Local product/checkout/account assertions are covered separately below.
- Current screenshot artifacts: `C:\Users\danyb\Documents\ChatGPT\suryavets-django\parity-audit-2026-09-22`; baseline artifacts remain in `parity-audit-verification`. These are test artifact folders, not additional Django projects. Account-order 320px, checkout 390px and CRM 390px screenshots were visually inspected; generating other artifacts alone is not a visual pass.

## Matrix conventions

PASS = the described local capability is implemented and supported by inspection/tests, within the stated scope. PARTIAL = usable foundation with a material gap or unverified integration. MISSING = no equivalent found in active code. BROKEN = implemented/exposed behavior fails its expected purpose or a measured acceptance check. NOT REQUIRED = not essential to this migration unless the owner changes scope. LATER = optional enhancement explicitly not a current launch requirement.

Priority: P0 before Shopify cutover; P1 shortly after launch (or before launch when an existing campaign/workflow depends on it); P2 improvement; P3 optional. Risk: H high, M medium, L low. Priority on a PASS row describes its business importance, **not an instruction to rebuild it**.

`U` in Shopify column means merchant-private behavior/configuration unverified. `Platform/U` means an enabled-by-platform concept, not confirmed active SuryaVets configuration. Status always describes **Django**, not an upstream timeout. Overlapping rows deliberately show the same risk where it affects multiple customer flows; do not count them as separate projects.

## 1. Storefront

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Homepage | S1 complete branded storefront | D10 same broad sequence; different curated products | PARTIAL | P1 | M | Finish measured visual/content comparison |
| Announcement bar | S1 selected-location free-delivery claim | Shared bar; pricing rule is not location-aware | PARTIAL | P0 | H | Align claim with delivery eligibility |
| Desktop navigation | S1 nested pet menus | Database tree and shared navigation | PASS | P0 | M | Retain; audit all destination mappings |
| Mobile menu | S1 drawer/nested controls exposed | Recursive drawer, expand controls, overlay/keyboard behavior | PARTIAL | P1 | M | Complete real-device/live comparison |
| Nested categories | S1 Cat/Dog/Farm and other trees | Self-FK Category, 170 records, active ancestors | PASS | P0 | M | Preserve tree; reconcile memberships |
| Banners / slider | S1 three slide controls and artwork | Real JS slider, three static fallbacks, optional Banner records | PARTIAL | P1 | M | Audit campaign copy, target links and mobile artwork |
| Trust section | S1 four benefits | SVGs; fixed four-column gold-border mobile CSS | PASS | P1 | L | Retain fixed arrangement; test text scaling |
| Featured products | S1 20 Top Selling entries observed | Database flags, eight selected items | PARTIAL | P1 | M | Owner-approved merchandising order |
| Promotional sections | S1 delivery artwork | Static delivery banner; fallback hero is not a clickable campaign | PARTIAL | P1 | M | Add verified destinations/content ownership later |
| Footer | S1 category/content/contact columns | Shared footer; links rendered | PASS | P1 | L | Retain; review mobile spacing |
| Contact information | S1 public phones/email; S9 support email differs | Hardcoded public contact details | PARTIAL | P1 | M | Confirm one operational support identity |
| Mobile responsiveness | Live mobile parity not certified | Responsive CSS and core-flow tests | PARTIAL | P0 | M | See section 21 |

## 2. Catalog

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Products | S1–S5 sellable catalog | 6,697 imported active records | PARTIAL | P0 | H | Verify scope, publication and current source |
| Variants | S3/S4 pack labels; separate pack URLs also present | 6,677 variants plus verified sibling families | PARTIAL | P0 | H | Reconcile exact pack/formulation identities |
| SKU | Backend/U | Fields/import preserved, 130 variant SKUs blank | PARTIAL | P0 | H | Resolve ambiguous fulfillment identities |
| Barcode | Usage U | Variant field/import supported, zero populated | PARTIAL | P2 | L | Ask if scanning is used; do not fabricate |
| MRP / compare-at | S3 crossed-out price | Decimal regular/override fields | PASS | P0 | H | Verify source prices, not just formatting |
| Selling price | S2/S5 include zero-price records | 96 active zero-price purchase options: 92 variants and 4 simple products; source files agree | BROKEN | P0 | H | Approval/publication safeguard; do not invent replacement prices |
| Sale price | S3 current discounted value | Exact Decimal selling value overrides legacy percentage | PASS | P0 | H | Preserve exact paise in reconciliation |
| Discount percentage | S1/S3 badges | Derived percentage with rounding | PASS | P1 | M | Keep exact prices authoritative |
| Stock data | Backend/U | Almost every variant has development stock 10 | PARTIAL | P0 | H | Fresh stock + ledger-aware reconciliation |
| Product images | S1–S5 imagery | 4,124 canonical families lack attached images | PARTIAL | P0 | H | Verify image identity before publication |
| Variant images | Exact live pack imagery U | 152 explicit assignments, fallback otherwise | PARTIAL | P1 | M | Assign verified pack-specific images |
| Descriptions | Product-specific public content varies | 2,223 blank descriptions | PARTIAL | P1 | M | Import/approve missing content |
| Brands/vendors | S3/S4 vendor label | 569 Brand records plus manufacturer | PASS | P1 | M | Normalize duplicates without losing provenance |
| Categories | S1 navigation/collections | Category + collections M2M | PARTIAL | P0 | H | Reconcile actual collection memberships |
| Subcategories | S1 arbitrary-depth tree | Category parent tree; legacy Subcategory retained | PASS | P1 | M | Do not replace with animal-specific models |
| Tags | Backend/U | Shopify tags JSON imported | PASS | P1 | M | Preserve tags used for collection rules |
| Product status | Published public catalog only | Active field/import exists; every local product active | PARTIAL | P0 | H | Verify publishable set, not just import count |
| Featured flags | S1 Top Selling | Featured/bestseller fields editable | PASS | P1 | L | Retain |
| Prescription / special handling | Live sells medicines; workflow U | `requires_prescription` field; no verified fulfillment gate | PARTIAL | P0 | H | Owner/pharmacist-approved restricted-product workflow |
| Nutrition / ingredients | Exact-label facts must be verified | Draft fields and review flag; zero reviewed | PARTIAL | P2 | H | Publish only approved exact-product facts |

## 3. Product page

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Image gallery | S3/S4 media presentation | Thumbnail switching/zoom and family media tested | PASS | P1 | M | Retain; missing catalog assets separate |
| Variant selector | S3/S4 pack controls | Exact-pack selector; family variants | PASS | P0 | H | Retain; audit data identities |
| Live price updates | Price attached to selected pack | JS updates current price from variant data | PASS | P0 | H | Keep server validation authoritative |
| MRP | S3 compare-at presentation | Selected variant MRP | PASS | P1 | M | Retain |
| Discount display | S3 sale presentation | Selected option badge | PASS | P1 | M | Retain |
| Savings | Sale pricing visible | Exact difference shown | PASS | P1 | M | Retain |
| Stock status | Public purchase state; physical stock U | Active/stock checks; fixture sold-out cases pass | PARTIAL | P0 | H | Reconcile real stock before trusting labels |
| Add to Cart | S3/S4 control | POST adds exact item and redirects to cart | PASS | P0 | H | Retain |
| Buy Now | Not visible in sampled S3/S4 | Exact variant goes to checkout | PASS | P1 | M | Intentional requested enhancement |
| Quantity | Sampled live template simplified | Product-card quantity removed; detail/cart handling tested | PASS | P1 | M | Keep requested card behavior |
| Related products | S3/S4 recommendation heading | Four same-category recommendations | PARTIAL | P2 | L | Refine relevance after catalog cleanup |
| Recommendations | Personalization U | Basic category selection, no recommendation engine | PARTIAL | P2 | L | No need for expensive engine now |
| Recently viewed | Not established in sample | No implementation found | LATER | P3 | L | Only build if useful |
| Product information | Vendor/pack/benefits visible | Description/specifications; approved-nutrition gate | PARTIAL | P1 | M | Fill content, retain safe escaping |
| Mobile buying | Exact live match not verified | Nine-width variant/media fixture checks pass | PASS | P0 | M | Test long real names and missing media too |
| Reviews | S3/S4 review section visible | No verified review model/UI/import | MISSING | P2 | M | Preserve existing reviews if owner supplies export |

## 4. Search and discovery

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Site search | S5 public results | Rich field search; real-data request exceeded 8s | BROKEN | P0 | H | Profile actual catalog queries and benchmark |
| Variant SKU search | Merchant behavior U | Family-child variant SKU included; canonical own variant SKU not explicitly included | PARTIAL | P1 | M | Add focused regression and correct query coverage |
| Autocomplete | Search widget infrastructure seen; prediction interaction not certified | No active suggestion endpoint | MISSING | P2 | M | Confirm need before implementation |
| Category browsing | S2 public collection | Tree-aware route; real Dog request exceeded 8s | BROKEN | P0 | H | Investigate query scale on full dataset |
| Filters overall | S2/S5 facets | GET filters and query-preserving pagination | PARTIAL | P1 | M | Test combinations with real imported data |
| Brand filter | S2 brand control | Brand slug filter | PASS | P1 | M | Retain |
| Price filter | S2/S5 price control | Decimal min/max with invalid-value handling | PASS | P1 | M | Profile correlated family-price expressions |
| Availability filter | S5 availability | Family-aware stock filter | PASS | P1 | M | Works only as well as verified stock |
| Product-type filter | S2 type control | ProductType filter | PASS | P1 | L | Retain |
| Category query filter | S2 tree | `?category=` only primary category; category route also uses descendants/M2M | PARTIAL | P1 | M | Make semantics consistent; test memberships |
| Sorting | S2/S5 controls | Featured/newest/price/name | PASS | P1 | M | Retain; define price-of-family behavior |
| Pagination | S2 pages | Twelve items/page, preserves filters | PASS | P1 | M | Performance test deep pages |

## 5. Cart

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Add to cart | Product controls; live mutation not performed | Session/user cart; add redirect tested | PASS | P0 | H | Retain |
| Exact variant | Platform/U populated cart | Variant FK and separate pack lines | PASS | P0 | H | Retain exact-pack tests |
| Quantity update | Platform/U | Server stock bounds, zero removes | PASS | P0 | H | Retain |
| Remove item | Platform/U | Owned POST removal | PASS | P0 | M | Retain |
| Subtotal | Platform/U | Server current-price Decimal totals | PASS | P0 | H | Retain |
| Discounts | Live campaigns U | Coupon-aware totals; usage lifecycle incomplete | PARTIAL | P1 | M | Define abandoned/cancelled redemption handling |
| Delivery | S8 checkout-calculated | Fixed ₹50 below ₹499; otherwise free | PARTIAL | P0 | H | Replace assumptions with approved rules |
| Total | Platform/U | Server subtotal minus discount plus delivery | PARTIAL | P0 | H | Tax/delivery business rules unresolved |
| Continue shopping | S6 link | Working local link | PASS | P1 | L | Retain |
| Checkout link | Platform/U | Correct cart-to-checkout flow | PASS | P0 | M | Retain |
| Empty/mobile cart | S6 empty drawer | Intentional full-page cart; tested empty/populated layouts | PASS | P1 | M | Keep requested redesign; not exact drawer parity |

## 6. Checkout

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Login/guest behavior | S6 encourages login; checkout U | Both supported; guest receipt session-scoped | PASS | P0 | H | Retain; guest follow-up access needs policy |
| Customer information | Platform/U | Validated contact/name fields | PASS | P0 | M | Add abuse controls before public launch |
| Saved addresses | Private account/U | Owned selection supported | PASS | P0 | H | Retain ownership checks |
| Delivery address | Platform/U | Checkout accepts invalid phone and PIN; six-digit validation exists only on saved addresses | BROKEN | P0 | H | Shared server-side phone/PIN validation with negative tests; serviceability is a separate rule |
| Billing address | Platform/U | Same/different address snapshot works; different billing PIN has the same format-validation gap | PARTIAL | P0 | H | Preserve snapshots; validate billing fields as well as shipping |
| Shipping method | S8 describes fulfillment | One implicit flat/default method | MISSING | P0 | H | Define eligible method/rate contract |
| Payment methods | Private checkout/U | COD + gated TEST online option | PARTIAL | P0 | H | Production gateway acceptance later; no audit changes |
| COD | S8 selected locations | COD accepted without area eligibility rules | PARTIAL | P0 | H | Restrict using approved delivery rules |
| Online payment | Provider/configuration U | TEST-only Razorpay adapter; real production payment unavailable | PARTIAL | P0 | H | Separate payment-readiness phase, not this audit |
| Coupons | Platform/U | Validated server quote, review token, discount snapshot | PASS | P0 | H | Preserve money checks |
| Order summary | Platform/U | Exact pack/prices/totals reviewed before placement | PASS | P0 | H | Retain |
| Tax / GST | Merchant configuration U | No tax rate/HSN/tax-line/invoice snapshot implementation found | MISSING | P0 | H | Accountant-approved inclusive/exclusive and invoice rules; do not assume zero tax |
| Delivery charges | S8 calculated checkout/selected free offers | Global hardcoded threshold/rate | PARTIAL | P0 | H | Approved location/weight rules |
| Order creation | Platform/U | Atomic order, snapshots, stock ledger and events | PASS | P0 | H | Retain; validate on PostgreSQL too |
| Failed/abandoned payment recovery | Merchant workflow U | Failed verification safe; stock remains deducted awaiting payment; no expiry/release flow found | PARTIAL | P0 | H | Design reservation expiry and late-payment reconciliation |
| Duplicate order prevention | Platform/U | Signed cart fingerprint + unique checkout key + transactional checks | PASS | P0 | H | Retain; load-test concurrent PostgreSQL checkout |
| Fulfillment eligibility | Medicine/cold-chain workflow U | No verified prescription/cold-chain serviceability enforcement | MISSING | P0 | H | Business approval before restricted items can ship |

## 7. Customer account

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Registration | S7 external account flow; completion U | Email registration, opaque unique username, safe cart merge | PASS | P0 | H | Add verification/abuse controls |
| Login | S7 Shop authentication redirect | Email/password, generic failures, inactive/ambiguous accounts rejected | PASS | P0 | H | Preserve tests |
| Google login | Not verified on live | Not installed/configured | LATER | P3 | M | Optional; never confuse Gmail address with Google OAuth |
| Password reset | Live recovery mechanism U | Change-password exists, reset/recovery routes absent | MISSING | P0 | H | Secure token-based recovery + email + throttling |
| Profile | Private/U | Name/phone edits; email locked pending verified support change | PASS | P1 | M | Retain safe email-change restriction |
| Saved addresses | Private/U | Add/edit/delete/default; owner-scoped | PASS | P0 | H | Retain |
| Order history | Private/U | Owner-scoped, paginated local orders | PASS | P0 | H | Historical Shopify migration separate |
| Order details | Private/U | Immutable item/address/price snapshots | PASS | P0 | H | Retain |
| Order tracking | S8 promises updates | Shared CRM events, actual timestamps, future states | PASS | P0 | H | Retain; courier sync separate |
| Buy Again | Live availability U | Current price, exact variant, unavailable packs skipped visibly | PASS | P1 | H | Retain |
| Wishlist | Live use U | Owned saved products, variant-choice UI | PASS | P2 | M | Retain |
| My Pets | Not established as Shopify feature | Owned pet profiles with category shopping | PASS | P2 | M | No medical advice; optional photo deferred |
| Support | S1/S9 contacts | Structured owned requests, staff reply | PASS | P0 | M | Keep public contact separate from authenticated tickets |
| Logout | Private/U | POST-only with CSRF | PASS | P0 | M | Retain |
| Mobile account | Live private UI U | Nine-width owned-resource/tracking tests | PASS | P0 | M | Real-device keyboard/zoom check still needed |
| Existing customer/order migration | Shopify history stays on Shopify | No customer/order import pipeline found; only three local orders | MISSING | P0 | H | Retention/access plan, verified identity linking and consent; never import passwords |
| Guest later tracking | Private/U | Session receipt; notification link omitted for guest accountless orders | PARTIAL | P1 | H | Secure verified guest access without email-only ownership matching |

## 8. Order management

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Order number | Private/U | Unique SV number | PASS | P0 | M | Retain; map legacy IDs separately |
| Placed | Platform/U | `pending` label + event; online `awaiting_payment` separate | PASS | P0 | H | Retain separation |
| Confirmed | Platform/U | Controlled transition and event | PASS | P0 | H | Retain |
| Processing | Merchant workflow U | Controlled transition | PASS | P0 | H | Retain |
| Packed | Merchant workflow U | Controlled transition | PASS | P0 | H | Retain |
| Shipped | S8 tracking | Requires courier/AWB; timestamp/actor recorded | PASS | P0 | H | Retain |
| Out for delivery | Courier workflow U | Manual staff transition | PASS | P1 | M | Optional carrier integration later |
| Delivered | Merchant workflow U | Separate from payment state | PASS | P0 | H | Retain |
| Cancelled | S9 pre-dispatch rule | Unpaid early-stage cancellation; paid and awaiting-payment gaps | PARTIAL | P0 | H | Controlled paid cancellation/refund/reservation workflow |
| Returns | S9 restricted | Requested/approved/rejected/received states | PARTIAL | P0 | H | Item-level eligibility/window rules |
| Refunds | S9 original-method promise | Staff records status/reference only; no money movement/amount ledger | PARTIAL | P0 | H | Reconcile external refunds and amounts |
| Tracking number/AWB | S8 tracking details | Stored/displayed | PASS | P0 | M | Retain |
| Courier | S8 delivery | Stored name | PASS | P0 | M | Retain |
| Status history | Private/U | OrderStatusHistory separates order/payment/return events | PASS | P0 | H | Retain; no fabricated legacy timestamps |
| Customer-visible tracking | Private/U | Same order/events as CRM | PASS | P0 | H | Retain |
| Internal notes | Private/U | Permission-protected, excluded from customer views/emails | PASS | P0 | H | Retain negative disclosure tests |

## 9. Inventory

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Variant-level stock | Backend/U | Variant counters and aggregate parent | PASS | P0 | H | Data reconciliation is separate blocker |
| Stock deduction | Backend/U | Conditional decrement, atomic checkout, ledger | PASS | P0 | H | Preserve transactional logic |
| Stock restoration | Backend/U | Once-only cancellation reversal from original movements | PARTIAL | P0 | H | Unpaid online expiry and return restock incomplete |
| Low stock | Backend/U | Threshold filters/CRM display | PASS | P1 | M | Becomes useful after real stock import |
| Out of stock | Public purchase controls; real rule U | Catalog/cart/checkout validation | PASS | P0 | H | Retain fixture tests |
| Adjustment | Backend/U | Permission, reason, stale-value/token checks | PASS | P0 | H | Retain |
| History/audit | Backend/U | InventoryMovement actor/before/after/reversal | PASS | P0 | H | Preserve 6,695 current movements |
| Bulk updates | Backend/U | Exact-location command, read-only default, refuses overwritten live movements | PARTIAL | P0 | H | Add approved movement-aware reconciliation, not guard bypass |
| Overselling protection | Backend/U | Locks + conditional stock checks, duplicate-line tests | PARTIAL | P0 | H | Validate concurrency and reservation lifecycle on PostgreSQL |

## 10. Customers / CRM

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Customer list | Private/U | Groups customers from order emails, not all registered/imported customers | PARTIAL | P1 | M | Unified customer identity without unsafe merging |
| Customer details | Private/U | Order-derived contact and notes | PARTIAL | P1 | M | Include owned profile context where authorized |
| Order history | Private/U | Staff can inspect associated order history | PASS | P0 | H | Retain |
| Addresses | Private/U | Shipping snapshots, not complete saved-address management | PARTIAL | P1 | M | Distinguish historical and current addresses |
| Support information | Private/U | Structured tickets and response state | PASS | P0 | M | Retain |
| Customer search | Private/U | Authorized order/customer email/name/phone search | PASS | P1 | H | Protect/export PII carefully |
| Filters | Private/U | Orders status/payment/returns/date filters | PASS | P1 | M | Retain |
| Customer notes | Private/U | CRMActivity notes | PASS | P1 | H | Retain access restrictions |
| Staff-only information | Private/U | Enforced server-side permissions | PASS | P0 | H | Retain |
| Staff permissions | Private/U | Active staff + access_crm + action permission | PASS | P0 | H | Audit admin routes as well |
| CRM roles | Private/U | Viewer / Operations / Manager groups | PASS | P0 | H | Review actual assignments before launch |
| Audit trail | Private/U | Order, coupon, stock events; not every customer/catalog mutation has a unified audit log | PARTIAL | P1 | M | Extend targeted auditing without duplication |

## 11. Email / notifications

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Order confirmation | Platform/U templates/settings | Event-based HTML/text outbox; automatic delivery disabled | PARTIAL | P0 | H | Enable only after domain/config/worker acceptance |
| Admin new order | Private/U recipients | Separate audience on placed event | PARTIAL | P0 | H | Verify admin recipient and real paired delivery |
| Order confirmed | Platform/U | Event queued, delivery gated | PARTIAL | P1 | M | Use existing architecture |
| Shipped | S8 notification promise | Event + order/tracking links | PARTIAL | P0 | H | Verify actual customer delivery |
| Out for delivery | Courier workflow U | Event supported | PARTIAL | P1 | M | Enable with approved messaging |
| Delivered | Private/U | Event supported | PARTIAL | P1 | M | Enable with approved messaging |
| Cancelled | Private/U | Event supported | PARTIAL | P0 | H | Preserve separate refund wording |
| Refund | S9 refund workflow | Payment-refunded event supported; no actual gateway refund implied | PARTIAL | P0 | H | Send only on reconciled external result |
| Password-reset email | Live account recovery U | No reset flow/template | MISSING | P0 | H | Build with secure account recovery |
| Account emails | Private/U | No verification/welcome lifecycle | MISSING | P1 | M | Verification before identity-sensitive actions |
| Duplicate prevention | Platform/U | Unique event/audience, durable claims and idempotency key | PASS | P0 | H | Retain; do not promise mathematical exactly-once delivery |
| Retry/failure handling | Platform/U | Backoff for safe retry; uncertain outcomes require reconciliation | PARTIAL | P0 | H | Monitored worker, bounce/complaint handling and alerts |
| Brevo connectivity | Not a Shopify parity requirement | One approved real diagnostic was accepted and visibly Delivered before this audit | PASS | P0 | M | Do not rebuild integration or resend during audit |
| Production sender | Store email config U | Verified Gmail sender rewritten to brevosend.com; no authenticated brand domain | PARTIAL | P0 | H | Authenticate SuryaVets sender and test inbox placement |

## 12. Discounts and promotions

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Coupon codes | Platform/U | CRM create/edit/activate and checkout application | PASS | P1 | M | Migrate only approved active campaigns |
| Percentage | Platform/U | Decimal percentage, caps/validation | PASS | P1 | H | Retain |
| Fixed amount | Platform/U | Capped at subtotal; no negative total | PASS | P1 | H | Retain |
| Minimum order | Platform/U | Minimum product subtotal | PASS | P1 | M | Confirm merchant threshold semantics |
| Expiry | Platform/U | Starts/ends timestamps | PASS | P1 | M | Display business timezone clearly |
| Usage limits | Platform/U | Global max/used count; no per-customer or cancellation-release lifecycle | PARTIAL | P1 | H | Prevent abandoned-order consumption abuse |
| Product/category restrictions | Shopify supports; active use U | No restricted-scope fields | MISSING | P1 | H | P0 if any migrated campaign depends on exclusions |
| Automatic discounts | Shopify supports; active use U | No rule engine | LATER | P2 | M | Confirm actual campaigns first |
| Free-shipping discounts | Shopify supports; active use U | Threshold only; not a coupon discount type | MISSING | P2 | M | Add only if used/required |
| Sale pricing | S1–S5 | Exact imported sale/MRP fields | PASS | P0 | H | Validate product data, not only arithmetic |

## 13. Delivery

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Delivery charges | S8 calculated at checkout | Hardcoded ₹50 / free | PARTIAL | P0 | H | Approved rate table and server quote |
| Free-shipping threshold | S1 selected locations above ₹499 | Global >=₹499 before coupon reduction | PARTIAL | P0 | H | Confirm boundary, location and discount treatment |
| PIN serviceability | Exact merchant rules U | Saved addresses validate PIN format; checkout does not; neither checks delivery eligibility | MISSING | P0 | H | Implement serviceability only in a later approved task, separately from basic form validation |
| Different fees by location | S8 variable checkout charges | None | MISSING | P0 | H | Owner/courier source of truth |
| COD by area | S8 selected-location COD | No area restriction | MISSING | P0 | H | Enforce eligibility before order creation |
| Estimated delivery | S8 3–7 business days guidance | Static policy claim, not a quoted ETA | PARTIAL | P1 | M | Avoid unsupported express promises |
| Courier tracking | S8 email/SMS guidance | Manual courier/AWB/HTTPS URL, customer timeline | PARTIAL | P1 | M | Automation optional; manual SOP required |

## 14. Returns / refunds

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Cancellation request | S9 contact before dispatch | Direct cancel for eligible unpaid orders; support otherwise | PARTIAL | P0 | H | Paid-cancellation request/review workflow |
| Cancellation rules | S9 pre-dispatch | Stricter pending/confirmed + unpaid guard | PARTIAL | P0 | H | Owner-approved alignment; never auto-refund |
| Return request | S9 seven-day window | Delivered-order request with reason | PARTIAL | P0 | H | Apply date/item-specific eligibility |
| Return eligibility | S9 edible/medical/hygiene restrictions | No category/window/item rule engine | MISSING | P0 | H | Do not promise universal returns |
| Approval/rejection | S9 inspection/review | Permission-protected return states | PASS | P0 | H | Retain human review |
| Refund status | S9 original-method refund | Pending/partial/refunded status separate from order | PARTIAL | P0 | H | Add amount and external reconciliation controls |
| Refund history | Private/U | Timestamped staff event/reference, no amount ledger | PARTIAL | P0 | H | Record amounts, currency and allocations |
| Returned stock | S9 inspection before approval | Cancellation restoration only; return receipt does not restock | MISSING | P0 | H | Explicit inspected sellable/non-sellable disposition |
| Customer communication | S9 contact/email | Account events; email integration gated | PARTIAL | P0 | M | Publish approved policy and status wording |

## 15. CMS / content

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| About | S10 destination | Static template | PARTIAL | P1 | L | Verify copy; editable content later |
| Contact | S10 destination and public contacts | Static details; form has no handler, defaults to GET | BROKEN | P0 | H | Stop losing enquiries/putting message fields in URLs; build safe delivery or remove misleading form |
| FAQ/help | S1 Help routes to Contact | Static help template | PARTIAL | P1 | M | Approved FAQ content |
| Privacy policy | S10 destination | Static template; Django/Brevo data practices not signed off | PARTIAL | P0 | H | Owner/legal review before public operation |
| Terms | S10 destination | Static template | PARTIAL | P0 | H | Owner-approved replacement terms |
| Shipping policy | S8 actual terms | Static 3–7 day/express wording; eligibility engine missing | PARTIAL | P0 | H | Match actual operational capability |
| Return/refund policy | S9 restrictions and inconsistent timing | Static replacement not verified equivalent | PARTIAL | P0 | H | Resolve source inconsistencies, align workflow |
| Blog/articles | No requirement established | No CMS/blog models found | LATER | P3 | L | Inventory indexed articles before declaring unnecessary |
| Banners | S1 artwork | Banner admin model; static fallback/promotional image | PARTIAL | P1 | M | Admin-manage all active campaigns with safe internal links |
| Editable homepage | Shopify theme settings/U | Flags/Banner editable; section copy/order/images partly code | PARTIAL | P2 | M | Small content model, not a page-builder rewrite |
| Newsletter | S1 visible signup; actual mailing outcome U | Always-success JSON stub, no subscriber persistence | BROKEN | P1 | M | Real opt-in/consent/unsubscribe or disable claim |

## 16. SEO

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Current vs Django URLs | `/products/`, `/collections/`, `/pages/` | Singular `/product/`, `/category/`, flat content paths | PARTIAL | P0 | H | Preserve or explicitly map every indexed path |
| Product slugs | S3/S4 original handles | Imported slugs and family aliases | PARTIAL | P0 | H | Old handle and variant-ID mapping required |
| Collection slugs | S1 original handles | Some renamed, e.g. fish-and-reptiles/pet-grooming | PARTIAL | P0 | H | Use Category.reference_path in approved mapping |
| Page titles | Live titles present | Dynamic product title, page blocks | PASS | P0 | M | Reconcile SEO title export |
| Meta descriptions | Live SEO content varies | Product fallback/field; generic base elsewhere | PARTIAL | P1 | M | Collection/content-specific values |
| Canonical | S3 canonical observed | Missing from active shared base | MISSING | P0 | H | Normalize host/paths/query variants |
| Open Graph | Live theme/share infrastructure | Only unused legacy base has OG tags | MISSING | P1 | M | Dynamic active share metadata |
| Structured data/schema | S3 JSON-LD observed | No active product schema found | MISSING | P0 | H | Verified Product/Offer/Breadcrumb data, no invented ratings |
| sitemap.xml | Shopify SEO capability; full current crawl not performed | Local 404 | MISSING | P0 | H | Generate canonical active-product/category/content sitemap |
| robots.txt | Shopify SEO capability; exact current policy unverified | Local 404 | MISSING | P0 | H | Staging noindex strategy and production crawl policy |
| 404 page | Live custom presentation not inspected | Default Django 404 / debug diagnostic | PARTIAL | P1 | M | Branded safe production page with true 404 status |
| Redirects | Shopify supports redirects; merchant list U | No old-route redirect layer | MISSING | P0 | H | Import/export redirect inventory, test 301 coverage |
| Old Shopify URL preservation | Existing external/bookmark links | Representative old routes return 404 | BROKEN | P0 | H | Prevent organic traffic loss before cutover |
| Image alt text | S1/S3 images | Alt fields/fallbacks; incomplete actual media | PARTIAL | P1 | M | Accurate product/pack descriptions |

## 17. Analytics

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Google Analytics | Merchant setup U | No active GA integration found | MISSING | P1 | M | Obtain verified property/config; no invented IDs |
| Google Tag Manager | S1 GTM iframe observed | No active GTM integration | MISSING | P1 | M | Preserve approved consent-aware setup |
| Meta Pixel | S1 Facebook tracking image observed; full event behavior U | No active Meta integration | MISSING | P1 | M | P0 business gate if paid ads depend on it |
| Ecommerce events | Actual live payloads U | No integrated event layer | MISSING | P1 | M | Versioned event contract and consent rules |
| Product view | U | No analytics event | MISSING | P1 | L | Exact product/variant identity |
| Add to cart | U | No analytics event | MISSING | P1 | M | Emit only on successful add |
| Checkout | U | No analytics event | MISSING | P1 | M | Record review/start, not a purchase |
| Purchase | U | No analytics event | MISSING | P1 | H | Idempotent verified-order event |
| Conversion values | U | No analytics value mapping | MISSING | P1 | H | Define INR, discounts/shipping/tax and COD semantics |

## 18. Reporting

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Revenue | Shopify reports capability/U | Paid-order totals/status sums, not net financial accounting | PARTIAL | P0 | H | Define paid/COD/refund/net reconciliation report |
| Orders | Private/U | Lists/counts/status summaries | PASS | P1 | M | Retain |
| AOV | Shopify reports capability/U | No dedicated calculation/report | MISSING | P2 | M | Define denominator/refund treatment |
| Top products | Shopify reports capability/U | Featured flags are not sales reporting | MISSING | P2 | M | Aggregate purchased snapshots |
| Top variants | Shopify reports capability/U | No report | MISSING | P2 | M | Aggregate exact variant/snapshot SKU |
| Low stock | Private/U | CRM inventory filters | PASS | P1 | M | Retain after reconciliation |
| Customers | Private/U | Order-email grouped counts | PARTIAL | P1 | M | Registered vs buying customers distinct |
| Repeat customers | Shopify reports capability/U | No repeat/cohort report | MISSING | P2 | M | Verified identity rules |
| Cancellations | Private/U | Order state filters, not trend/value analysis | PARTIAL | P1 | M | Add financial/operational reconciliation |
| Refunds | Private/U | Status only; no amount report | PARTIAL | P0 | H | Amount ledger and reconciliation first |
| Date filtering | Private/U | Order-list date filters; reports mostly unbounded | PARTIAL | P1 | M | Business-timezone date ranges and exports |

## 19. Security

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| Authentication | S7 hosted auth | Django hashing/session auth and validators | PASS | P0 | H | Recovery/verification/throttling are separate gaps |
| Authorization | Private/U | Server action permissions | PASS | P0 | H | Preserve negative tests |
| Customer separation | Private/U | Owned order/address/pet/wishlist/support queries | PASS | P0 | H | Do not auto-link orders by unverified email |
| CRM permissions | Private/U | Staff + access + action permission | PASS | P0 | H | Least privilege and role review |
| CSRF | Platform/U | Middleware and POST forms; signed webhook exemption appropriate | PASS | P0 | H | Retain security tests |
| IDOR | Private/U | UUID is not sole protection; owner checks tested | PASS | P0 | H | Retain shared-data boundary tests |
| Secrets | Platform-managed/U | Environment config; private Brevo JSON ignored/restricted | PARTIAL | P0 | H | Production secret store, rotation, history scan before publishing |
| Payment validation | Provider/U | Signature, captured state, order/currency/amount checks in TEST adapter | PARTIAL | P0 | H | Live acceptance/reconciliation remains separate |
| Price manipulation | Platform/U | Server prices, signed fingerprint; no browser-price trust | PASS | P0 | H | Legitimately stored zero prices are separate data risk |
| Stock manipulation | Platform/U | Server bounds, exact pack validation, staff token checks | PASS | P0 | H | Verify PostgreSQL contention/load |
| Rate limiting | Platform/U | No login/signup/checkout/contact throttling found | MISSING | P0 | H | Abuse protection without leaking account existence |
| Admin protection | Platform/U | Django staff/admin auth; no MFA/extra gate. Financial/state fields are read-only, but generic admin can still edit order customer/address fields | PARTIAL | P0 | H | Least privilege and audited correction policy for sensitive historical fields; not evidence of an unauthenticated bypass |
| Secure production settings | Hosted/U | DEBUG/hosts/CSRF/HTTPS/cookie/HSTS config exists | PARTIAL | P0 | H | Validate actual production environment, proxy and deployment checks |
| Public contact privacy | S10 public contact | GET form can expose message/contact fields in URLs/logs | BROKEN | P0 | H | POST/CSRF/minimized storage and real handler |

## 20. Operations

| Feature | Current Shopify/live behavior | Current Django behavior | Status | Business importance | Technical risk | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| PostgreSQL | Managed platform data/U | DATABASE_URL/psycopg available; local SQLite, production can fall back to SQLite | PARTIAL | P0 | H | Require PostgreSQL in production; migration/concurrency rehearsal |
| Render | Shopify remains live | Gunicorn dependency/config foundations; no deployment validated | PARTIAL | P0 | H | Deploy temporary URL only after local gates |
| Environment variables | Hosted config/U | Settings support env; local Brevo wrapper separate | PARTIAL | P0 | H | Ensure normal production entrypoint receives required settings |
| Media storage | Shopify-hosted assets | Local FileSystemStorage; current images on Windows disk | MISSING | P0 | H | Persistent object storage + verified migration; not ephemeral Render filesystem |
| Backups | Platform responsibilities/U | No scheduled backup/restore verification found | MISSING | P0 | H | Database + media backups, retention and restore drill |
| Logging | Platform/U | Basic Django/service logger calls | PARTIAL | P0 | M | Structured redacted production logs/retention |
| Error monitoring | Platform/U | No configured alerting integration found | MISSING | P0 | H | Alert checkout, payment, mail and stock failures |
| Static files | Shopify CDN | WhiteNoise and collectstatic configuration | PARTIAL | P0 | M | Production build/static smoke test; cache versioning |
| Database migrations | Managed platform/U | 15 applied, no model drift, isolated test DB builds | PASS | P0 | H | PostgreSQL migration rehearsal still required |
| Production email | Platform/U | Brevo delivery proven once; automatic order delivery off | PARTIAL | P0 | H | Domain, recipients, worker, monitoring and acceptance |
| Scheduled/background jobs | Platform/U | Notification command/manual reconciliation, no verified scheduler | MISSING | P0 | H | Monitored outbox worker; safe reservation jobs later |
| Cutover/recovery | Existing Shopify operation | No rehearsed final delta/rollback handoff demonstrated | PARTIAL | P0 | H | Freeze window, exports, counts, rollback and support ownership |

## 21. Mobile audit

The table distinguishes **local functional/layout regression** from **live visual equality**. PASS below means existing fixture assertions succeeded at that width. It does not certify every imported product, browser, accessibility setting, hardware keyboard or real payment provider.

| Flow | 320 | 360 | 375 | 390 | 412 | 430 | 768 | Evidence / remaining gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Variant cards + exact-pack buying | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `variant_browser_test.cjs`; selected prices/images, touch controls and overflow |
| Product gallery | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `media_browser_test.cjs`; switching/accessibility controls |
| Populated cart | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `checkout_browser_test.cjs`, `purchase_browser_test.cjs` |
| Checkout form | PARTIAL | PARTIAL | PASS | PASS | PARTIAL | PASS | PASS | Coupon checkout tested at 375/390/430/768; no exact-width form assertion at 320/360/412 in current suite |
| Confirmation/tracking | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Receipt and account tests; TEST payment double, not real gateway |
| Account dashboard/orders/pets/addresses/support | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `account_browser_test.cjs`; ownership and no page overflow |
| Login/register form | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Current measured public-page overflow checks at all seven widths, plus existing fixture interaction tests at 375/390/430/768; no claim of interaction testing at every width |
| Homepage/menu/footer visual parity | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | Current homepage measured at all seven widths without page overflow; 390px live/local screenshot comparison and live nested drawer inspection. Full visual/accessibility acceptance remains |
| Real-data collection/search | BROKEN | BROKEN | BROKEN | BROKEN | BROKEN | BROKEN | BROKEN | Shared server response exceeded 8s; backend issue affects all widths, not a separate mobile layout defect |

Screenshots generated at 320/390/1440 for several flows supplement automated width assertions. These are layout/interaction statuses, not proof of valid business rules: the checkout form-validation defect applies at every width. No iOS Safari, Android device, 200% text scaling, soft-keyboard checkout or slow-network acceptance performed. The four mobile trust boxes use fixed four equal columns (not a sliding strip); small type is an accessibility/readability review item, not a reported overflow failure. The 320px account tracker fits but is very tall; the mobile CRM recent-orders table is a constrained scroll region, so actions/columns need real-device review rather than assuming a page-overflow assertion makes them easily discoverable.

## SEO migration risks — separate launch gate

1. **Old links currently 404.** Preserve `/products/<handle>` or serve tested one-hop 301s to the equivalent canonical product. Preserve `/collections/<handle>`, `/collections/<handle>/products/<handle>`, `/pages/<handle>` and any indexed blog URLs. Map existing Shopify redirects too; never redirect everything to the homepage.
2. **Pack identity in URLs.** Keep a legacy Shopify product/variant-ID mapping. Family grouping must not silently change a customer's selected size. Decide canonical family URL and safe `?variant=` conversion; undocumented grouped aliases create duplicate content.
3. **Collection names differ.** Examples: `fish-reptiles` → `fish-and-reptiles`; `vaccination-for-farm-animals-copy` → `pet-grooming`. Confirm meaning, not string similarity.
4. **Missing crawl/share metadata.** Active templates lack canonical/OG/product structured data; robots/sitemap 404. Legacy template markup does not solve active-page SEO.
5. **Staging indexing.** Keep temporary deployment non-indexable; remove only the appropriate staging restrictions after acceptance. Customer/CRM pages already use private/noindex protections; do not expose them in sitemaps.
6. **Content, image and speed losses.** Missing images/descriptions and slow real-data search/collections can damage usability and discoverability independently of 301 correctness.
7. **Required evidence before cutover.** Obtain Shopify sitemap/redirect export, Search Console landing URLs, indexed content inventory and top campaign links. Verify status/canonical/metadata for every mapped URL; monitor 404s and traffic after launch. This audit did not crawl every indexed URL.

## Prioritized work and acceptance gates

### P0 — must be resolved before leaving Shopify

1. **Truthful sellable catalog:** approve exact variants, prices, real stock, restricted items and primary images; reconcile existing local stock movements. Publish only an approved sellable set, not necessarily all 6,697 records at once.
2. **Catalog/search performance:** investigate full-data timeouts. The family-price correlated subqueries and joins are suspects from code inspection, not a proven root cause. Benchmark on production-like PostgreSQL and set response-time budgets.
3. **Checkout validation and delivery/COD/tax contract:** reject malformed phone/shipping/billing PIN inputs, then implement approved serviceable areas, rates, thresholds, COD eligibility, fulfillment restrictions and tax/invoice treatment. Form validation is not a substitute for serviceability. No PIN implementation was attempted here.
4. **Payment/order recovery:** production payment acceptance, stock reservation expiry/late capture/uncertain payment reconciliation and auditable paid cancellation/refund amounts. TEST payment code was not modified.
5. **Returns:** owner-approved restricted-category/window rules, inspected stock disposition, refund/customer communication. Resolve inconsistent live refund timelines.
6. **SEO continuity:** exact redirects, canonical metadata, schema, sitemap/robots and indexed-content preservation.
7. **Account/security:** password recovery, abuse throttling, privileged-access hardening, verified identity handling and safe customer/history migration. A support-only recovery exception would require an explicit owner-approved policy, not an assumed substitute.
8. **Production reliability:** PostgreSQL guard, persistent media, backup/restore, log/error alerts, monitored jobs, temporary-URL acceptance and rollback rehearsal.
9. **Transactional communication:** production sender/domain, recipients and monitored outbox; real customer/admin pair acceptance. Brevo adapter exists; do not rebuild it.
10. **Contact form:** prevent lost enquiries and private messages in GET query strings. The authenticated support system does not fix the separate public form.

### P1 — near-launch operational/experience gaps

- Newsletter persistence/consent (or remove nonfunctional signup), catalog descriptions/variant images, correct merchandising and promotional targets.
- Search facet consistency and SKU search coverage; same-size live/local mobile/desktop comparison.
- Unified CRM customer context, complete targeted audit trails, date-range operational reporting and clear business timezone.
- Approved active coupon restrictions/usage lifecycle; promote to P0 when a launch campaign relies on them.
- Account verification/notifications and safe guest follow-up access.
- Analytics and consent-aware ecommerce events; promote to a business launch gate when existing paid campaigns depend on them.
- Open Graph, content metadata and a polished real 404 page.

### P2 / P3 — valuable, not reasons to delay safe basics

- Advanced product recommendations, AOV/top-product/top-variant/repeat-customer reporting.
- Reviewed nutrition enrichment, CMS-managed homepage copy, reviews migration, autocomplete and free-shipping promotion types where needed.
- Google OAuth, recently viewed, blogs and advanced campaign engines only after confirming business use. Barcode scanning is not automatically required just because Shopify supports a barcode field.

### Already working — retain, do not duplicate

Database-driven products and category tree; exact Decimal variant pricing; gallery and variant controls; session/user cart and safe merge; exact-pack order snapshots; idempotent transactional checkout; owned account resources; shared CRM/customer order history; controlled order states; private notes; staff permissions; stock movement ledger; coupon basics; event outbox and a proven Brevo connection. These are scoped capabilities, not a declaration that their production configuration or source data is complete.

### Broken/exposed behavior identified

- Zero-selling-price active purchase options lack an approval/publication safeguard (96, including four simple products).
- Checkout accepts malformed phone, shipping PIN and different billing PIN values; saved-address validation does not cover this path.
- Real imported-data Dog/search requests exceed the eight-second probe deadline despite fixture tests passing.
- Public contact form has no backend and uses default GET; newsletter reports success without storage.
- Existing Shopify URLs return 404 in Django.
- No claim that Shopify itself is broken: the Shop login timeout was an inspection limitation. No claim of a currently failing Razorpay charge: production payments are not enabled, and no real charge was attempted.

## Recommended development order

1. **One next major task: catalog approval/publication safeguards with ledger-aware reconciliation.** Reuse the completed 22 September dry-run report keyed by original handle + exact options + SKU. Add a review/approval state and server-enforced publication/purchase checks through existing CRM/services, with tests preventing direct URL/cart/checkout bypass. Obtain fresh full exports and owner-approved corrections before applying stock or prices; use a backup and auditable idempotent adjustments that preserve order history. Require positive approved prices (or explicit free-item approval), verified pack identity, current stock and a real correct image for each published listing. Never replace real stock with a guessed number or manufacture unavailable variants. This is one catalog-integrity workstream, not authorization to apply corrections during this audit.
2. Resolve measured catalog/search query performance with full-size data and production-like PostgreSQL benchmarks.
3. Close checkout phone/address format gaps and implement approved delivery/COD/tax/fulfillment rules.
4. Complete payment lifecycle, reservation recovery, cancellations and refunds in a separately approved payment phase.
5. Close account/contact/email/security and customer-history migration gaps.
6. Finish SEO, content/visual/mobile acceptance and required analytics.
7. Configure persistent production infrastructure, restore-tested backups and monitoring; deploy only to a temporary Render URL.
8. Reconcile final Shopify deltas, exercise rollback and obtain owner sign-off; only then plan domain cutover.

The stages are not permission to implement now. **This deliverable is the audit.** Shopify remains live and untouched.

## Owner information still needed

- Current inventory export/location ownership and approved handling of local test orders/adjustments; do not erase the ledger to make an importer run.
- Correct prices/packs for exceptions and an approved list of intentionally free products, if any.
- Active discounts and their exclusions/usage policies; shipping zones/rates/COD restrictions; tax/invoice requirements; prescription/cold-chain operational rules.
- Customer/order/history and marketing-consent retention plan; authorized exports when needed.
- Existing redirect/sitemap/Search Console/campaign URL inventory; active analytics integrations; reviews/blogs that must migrate.
- Confirm operational support addresses and a single consistent return/refund policy.

## Changes and reproducibility

This refresh updates `SHOPIFY_PARITY_AUDIT.md` only. Existing uncommitted `BREVO_EMAIL_SETUP.md`, `shop/mail_backends.py`, `shop/test_brevo_email.py`, `brevo_local.py` and unrelated files were preserved. Test artifacts were written outside the application repository. No schema migration or source-data import was needed. No application-code fix was required to complete the audit, so none was made. A temporary loopback-only audit server used disabled payment/email flags; this was not a Render deployment.

Final database SHA-256 remained `3e02bf594b82e553578d6f9024c2e41939a26ea7122353c28bbe1118e6e9e265`, matching the read-only reconciliation baseline. Existing application records were unchanged. The final Django check passed. All 253 feature rows have the required seven columns, and all 21 requested areas are present.

Basic checks (PowerShell):

```powershell
Set-Location 'C:\Users\danyb\Desktop\suryavets-django'
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test shop --noinput
```

To include the existing browser tests, set their documented runtime variables first:

```powershell
$env:SURYA_BROWSER_NODE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:SURYA_PLAYWRIGHT_MODULE='C:/Users/danyb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:SURYA_BROWSER_EXECUTABLE='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
$env:SURYA_BROWSER_ARTIFACTS='C:/Users/danyb/Documents/ChatGPT/suryavets-django/parity-audit-2026-09-22'
.\.venv\Scripts\python.exe manage.py test shop --noinput
```

Do not run import `--apply`, drain notification queues, enable live payments or change DNS as part of reproducing this audit.

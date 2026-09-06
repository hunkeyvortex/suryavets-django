# Surya Vets Shopify → Django migration inventory

Audit date: 2026-09-07  
Reference: public pages at `https://suryavets.com/`. This is an audit record, not a claim of visual completion.

## Reference site inventory

The public Shopify storefront is a veterinary ecommerce catalogue organised by pet type and then by collection. Its primary navigation exposes Cat, Dog, Farm Animals, Fish & Reptiles, Vaccination, Pet Grooming, and Contact Us. Cat/Dog/Farm menus each have groups for Medicine, Supplements, Food, Treats and Supplies; the groups contain many treatment-specific collections. The reference uses the green/orange/white Surya Vets identity, a delivery announcement bar, a search-led header, a large category menu, product carousels/cards, a newsletter and a multi-column/footer-policy area.

The exact responsive measurements and every visual state still need side-by-side browser comparisons before marking a row as a match.

| Page / component | Reference URL | Django URL | Desktop match | Mobile match | Functional | Status | Notes |
|---|---|---|---|---|---|---|---|
| Home | `/` | `/` | Partial | Partial | Partial | IN PROGRESS | Django has the major broad sections, but its layout/content/assets have not been side-by-side matched against the current Shopify homepage. |
| Delivery bar | `/` | `/` | Partial | Partial | Yes | IN PROGRESS | Live copy: free delivery over ₹499 in selected locations. |
| Header, search, desktop navigation | `/` | `/` | Partial | Partial | Yes | IN PROGRESS | Search works in Django; mega-menu depth and exact responsive interactions do not yet match. |
| Mobile header / hamburger navigation | `/` at phone widths | `/` at phone widths | N/A | Partial | Yes | NEEDS REVIEW | Requires same-viewport visual comparison. |
| Footer / newsletter / medical disclaimer | `/` | `/` | Partial | Partial | Newsletter local only | IN PROGRESS | Django needs live footer typography, spacing, policy/link treatment and disclaimer verification. |
| Pet landing collections | `/collections/cat`, `/collections/dog`, `/collections/farm-animals`, `/collections/fish-reptiles`, `/collections/vaccination` | `/category/<slug>/` | Partial | Partial | Yes | IN PROGRESS | One dynamic Django template exists; Shopify collection descriptions, hierarchy and handles need importing/mapping. |
| Treatment collections | e.g. `/collections/medicine-for-cats`, `/collections/dog-antibiotic` | `/category/<category>/<subcategory>/` | Partial | Partial | Yes | IN PROGRESS | Django supports two tiers, but live taxonomy and real product assignments are absent. |
| Brand collections | e.g. `/collections/sky-ec` | `/categories/?brand=<slug>` | No | No | Yes | NOT STARTED | Backend filter exists; no Shopify-equivalent brand collection URLs/presentation yet. |
| Product listing, filters, sorting and pagination | public collection pages | `/categories/`, `/search/` | Partial | Partial | Yes | IN PROGRESS | Django supports basic filters/sorting/pagination; reference has product-type/vendor facet presentation to match. |
| Product card | home / collection cards | reusable `includes/product_card.html` | Partial | Partial | Yes | IN PROGRESS | Sale badge, type, prices and add-to-cart exist, but exact image geometry/card states need comparison. |
| Standard product | e.g. `/products/rc-urinary-s-o-cat-dry-food-1-2kg` | `/product/<slug>/` | Partial | Partial | Yes | IN PROGRESS | Django supports variants/images/prices/stock, but live gallery/detail tabs/recommendations need matching and imported data. |
| Prescription-required product | e.g. `/products/arnica-montana-30ml` | none | No | No | No | NOT STARTED | Live product asks for prescription image and doctor name before cart. Django models/checkout lack prescription workflow. |
| Search | `/search?q=…` | `/search/?q=…` | Partial | Partial | Yes | IN PROGRESS | Django searches product fields; predictive/empty/result presentation needs matching. |
| Empty/populated cart | `/cart` | `/cart/` | Partial | Partial | Yes | IN PROGRESS | Django session cart and quantity controls work; live cart/drawer styles and states need comparison. |
| Account login/register | `/account` | `/login/`, `/register/` | Partial | Partial | Yes | IN PROGRESS | Django authentication exists; Shopify customer UI visual comparison remains. |
| Customer profile, addresses, orders | Shopify customer area | `/account/`, `/account/addresses/`, `/account/orders/<uuid>/` | No | No | Yes | FUNCTIONAL COMPLETE | Django implementation exists; it is not yet visually matched. |
| Checkout | Shopify checkout | `/checkout/` | No | No | Partial | IN PROGRESS | Django creates orders and captures addresses. Payment integration, stock-safe ordering and live visual match remain. |
| Content and policy pages | `/pages/about-us`, `/pages/contact`, policies | `/about/`, `/contact/`, `/help/`, `/shipping/`, `/privacy/`, `/terms/`, `/returns/` | Partial | Partial | Partial | IN PROGRESS | Routes/templates exist; page copy/design/SEO mapping require review. |
| Product data import | Shopify product CSV export | management command pending | N/A | N/A | No | NOT STARTED | Only local demonstration products are in the database; no Shopify CSV importer has been built. |
| Images and media | Shopify CDN/store assets | `media/`, `shop/static/` | Partial | Partial | Partial | IN PROGRESS | Some authorised assets and generated category images exist. Production media storage is not configured. |
| SEO migration | Shopify URLs/meta/robots/sitemap | none | No | No | No | NOT STARTED | Need sitemap, robots.txt, canonical metadata and a verified 301 redirect map. |
| Production / Render | Render target | Django settings + requirements | N/A | N/A | Partial | IN PROGRESS | PostgreSQL/WhiteNoise/env foundations exist. Collectstatic production validation and persistent media provider remain. |

## Existing Django project

- Configuration package: `suryavets`; WSGI target: `suryavets.wsgi`.
- App: `shop`.
- Data: SQLite locally (`db.sqlite3`); settings support `DATABASE_URL` for production PostgreSQL.
- Models already cover `Category`, `Subcategory`, `ProductType`, `Brand`, `PetCategory`, `Product`, `ProductVariant`, `ProductImage`, cart, customer address, order and order item.
- Templates: reusable base/includes plus home, catalogue, product, cart, account, checkout and policy templates.
- Static source: `shop/static/css` and `shop/static/js`; local media: `media/`.
- Migrations: `0001`, `0002`, `0003`.
- Current database contains local demonstration catalogue entries only; they must not be mistaken for a Shopify import.
- `python manage.py check` passes on 2026-09-07.

## Gaps that drive the next implementation work

1. Build an exact Shopify taxonomy/handle import plan and Shopify CSV importer before treating the local catalogue as migration-ready.
2. Compare the reference and Django header, navigation, homepage, cards, collection page and product page at equal desktop and mobile viewports; then adjust the shared component system, not individual pages in isolation.
3. Add prescription-required product support or explicitly exclude those products until its safe upload/review flow exists.
4. Match the collection filter facets, product gallery, cart states, customer UI and policy content.
5. Add SEO migration artifacts (metadata, sitemap, robots and a verified redirect spreadsheet) and complete persistent object storage before Render launch.

## Incremental implementation plan

1. Lock the reference measurements and section order for global chrome + homepage using side-by-side desktop/mobile comparisons.
2. Refine reusable announcement, header, navigation, search, footer, card and responsive CSS components.
3. Import taxonomy and products from a Shopify CSV; use the imported data to tune collection and product layouts.
4. Complete the remaining collection filters, product-gallery states, prescription flow decision, cart and checkout refinements.
5. Perform visual comparison passes for every row above, then add SEO and finish production/Render validation.

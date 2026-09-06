# Phase 1: Existing Project Audit

Audit date: 2026-09-06

## Confirmed structure

- Project configuration package: `suryavets`
- Django application: `shop`
- Entry point: `manage.py`
- WSGI module for eventual Gunicorn deployment: `suryavets.wsgi`
- Database: local SQLite (`db.sqlite3`)
- Migrations: `shop.0001_initial` and `shop.0002_alter_productspecification_options_and_more`
- Templates: `shop/templates`
- Static source assets: `shop/static`

## Existing implementation retained

The project already provides models for categories, products, variants, images, banners and carts; Django admin registration; category, product, search, cart and checkout routes; and both legacy and newer storefront templates.

The active `shop.views` module renders the newer `*_new.html` storefront pages. Older templates and `views_new.py` are retained as reference only until the global design is consolidated in Phases 3 and 4.

## Verified baseline

- The local database contains 5 categories and 17 subcategories.
- It does not yet contain products, variants, product images or banners.
- Django was installed only in a virtual environment belonging to another Desktop folder.
- Pillow was absent, so Django checks failed for existing `ImageField` models.
- There are currently no automated tests.

## Phase order

1. Phase 2: extend the catalogue/customer/order schema and admin without discarding existing category/product data.
2. Phases 3-4: consolidate the storefront into reusable includes and recreate the reference global design/homepage.
3. Phases 5-8: implement catalogue browsing, session cart, accounts, orders and checkout.
4. Phase 9: add the Shopify CSV importer.

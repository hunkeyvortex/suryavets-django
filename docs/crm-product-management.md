# CRM product management

Implemented 7 September 2026 in the existing Django project. No live Shopify, DNS or production changes.

## Using it

1. Open `http://127.0.0.1:8007/crm/inventory/` using a superuser or CRM Manager account.
2. **Add product** creates a simple product with name, preserved/unique URL handle, SKU, brand, categories/collections, exact prices, descriptions, photo, merchandising flags and SEO fields.
3. New products start at **zero stock** with inventory tracking enabled. After creating one, choose **Adjust stock**, enter the opening quantity as a positive change and record a reason. This creates the existing stock-ledger entry instead of silently altering inventory.
4. **Edit** changes product details. Products with variants have a **Packs & variants** area and **Edit pack** buttons. Pack prices are independent of the base product price; a shortcut notice at the top links to them. Existing variant names, SKUs, weight and prices can be edited here. Creating new variant structures is not part of this update.
5. **Archive** removes a product from sale after confirmation and a reason. It keeps the product, photos, order references and stock ledger. **Restore** makes it visible again. There is no permanent-delete button.
6. Filters and status cards find Active/Archived products. Mobile uses product cards instead of a horizontally scrolling desktop table.

Manager role now includes Django's `add_product` and `change_product` permissions alongside existing CRM access. Viewer and Operations roles do not gain product-edit permissions. Existing user accounts, passwords and group memberships were not changed.

## Safety and media

- Product editing cannot overwrite stock, tracking settings, ownership or order snapshots using additional POST fields.
- Writes use transactions and product/variant locks. Stale forms are rejected. Existing product handles cannot be changed from this editor.
- Archive/restore uses POST + CSRF + explicit confirmation; an old duplicate POST cannot reverse the action.
- Catalog actions are recorded as staff-only CRMActivity notes with the product UUID, actor and changed field names/reason.
- Uploads accept validated JPEG/PNG/WebP images up to 5 MB and 20 megapixels. A new upload becomes the main photo while retaining older photos. Uses the existing Django media storage; production persistent-media configuration is still required before Render deployment.
- No existing catalog items or stock quantities were changed while developing/testing. Browser and upload fixtures used disposable test databases and temporary media directories.

## Changed files

- `shop/crm_catalog_forms.py`, `shop/crm_catalog_views.py`: product editor, image validation, variant editor and archive/restore.
- `shop/crm_urls.py`, `shop/crm_views.py`: routes, filtered inventory and catalog counts.
- `shop/management/commands/setup_crm_roles.py`: manager add/change product permissions.
- `shop/templates/crm/base.html`: inventory-only stylesheet and edit/archive shortcuts on stock pages.
- `shop/templates/crm/catalog_inventory.html`, `catalog_field.html`, `product_editor.html`, `variant_editor.html`, `product_archive.html`: reusable inventory/editor UI. The older inventory template is retained but inactive.
- `shop/static/css/crm-catalog.css`: scoped responsive design.
- `shop/test_crm_catalog.py`, `shop/test_catalog_browser.py`, `shop/catalog_browser_test.cjs`: regression and real-browser verification.
- `SURYA_MIGRATION_AUDIT.md`, this guide: scope and verification.

## Verification and commands

All **115 tests pass**, including all four enabled browser suites. New coverage includes manager/viewer permissions, duplicate handles, prices, stale forms, archive/restore and order preservation, pack ownership checks, valid/invalid photo uploads, and creation without stock tampering. Inventory and editor checked at 375, 390, 430, 768, 1024 and 1440 px; desktop/mobile screenshots visually reviewed.

```powershell
cd C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

Optional browser suites use the environment variables documented in `docs/cart-redesign.md`. This milestone stored screenshots under `C:/Users/danyb/Documents/ChatGPT/suryavets-django/catalog-verification/`.

No migrations required. `setup_crm_roles` has already been run locally; on another environment run it after migrations to create/update the same groups. Database backup: `tmp/pre-catalog-editor-20260907-234801.sqlite3`. Pre-change Git checkpoint: `codex/checkpoint-before-inventory-editor-20260907` at `01013b6`.

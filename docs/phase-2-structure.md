# Phase 2: Project Structure

SuryaVets now follows the same VS Code-friendly Django layout used by the Boww/Meow project:

```text
suryavets-django/
├── .vscode/                 # Debug configuration for VS Code
├── catalog_exports/         # Raw public scrape now; Shopify CSV imports later
├── docs/                    # Project phase notes
├── media/                   # Local development uploads (not committed)
├── shop/                    # Storefront application
│   ├── management/commands/ # Shopify importer will live here
│   ├── migrations/
│   ├── services/            # Checkout, import and other business services
│   ├── static/
│   └── templates/
├── suryavets/               # Django configuration package
├── tmp/                     # Local transient files (not committed)
├── .env.example
├── manage.py
└── requirements.txt
```

The raw scrape was moved from `scraped_content/` to `catalog_exports/`. Its scraper script was updated to use the new location.

Existing runtime CSS, JavaScript and image files remain under `shop/static/`, so the current storefront continues to use them.

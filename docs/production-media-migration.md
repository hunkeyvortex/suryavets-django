# Production media recovery (4 October 2026)

## Causes and scope

Cloudinary storage interprets the existing database file names as Cloudinary
asset IDs. Changing the backend did not transfer the corresponding local files.
The five category files (Cat, Dog, Farm Animals, Fish & Reptiles, Vaccination)
exist locally under `media/categories/`. Grooming has no Category.image and uses
the existing static reference artwork instead.

Local read-only inventory: 5,245 nonempty database file references, 5,245 local
files found, 5,245 distinct prospective uploads, zero missing paths and zero
errors. This is NOT a production database count or a Cloudinary existence check.
The production-connected dry run is authoritative; already uploaded assets reduce
the number of uploads. Products with no image field reference are outside this
migration: it does not manufacture images for the previously missing catalog.

Homepage: local database has 6,457 bestseller flags (bulk-imported) but ZERO
merchandising_active products. Merely copying that database cannot publish a
curated section. Previously selection also required a generated local audit file
and exact-pack imagery. Missing imagery no longer excludes manually selected
bestsellers/featured picks; existing card placeholders and pack resolver remain.
Top Selling Products is capped at eight, ranked by merchandising_rank/name/ID.
Featured picks remain honestly titled if no eligible bestseller is selected.

Generated audit files are not committed. Where absent, a latest database catalog
review decision of approved AND merchandising_active are required. Known P0
audit blocks, explicit holds, stock, price, activity and canonical-family rules
remain enforced. Staff must approve the intended products in CRM catalog review,
then select them in `/crm/merchandising/`, check Curated for homepage and Best
Seller, and set rank. Select Featured instead if bestseller status is unverified.
No flags, prices or stock have been changed by this fix. The section cannot be
claimed restored in production until these publishing decisions are made.

## Windows runbook

1. Back up the production PostgreSQL database before updating media references.
   Retain the original local media folder. Do not run concurrently with staff
   image edits. Ensure Render has deployed this commit.
2. Open PowerShell on the laptop with the original media. Set process-only
   variables below. Masked prompts keep credentials out of command history:

```powershell
Set-Location C:\Users\danyb\Desktop\suryavets-django
.\.venv\Scripts\python.exe -m pip install -r requirements-media.txt
$env:DEBUG = 'True' # command process only; do NOT change Render DEBUG
$env:MEDIA_STORAGE_BACKEND = 'cloudinary_storage.storage.MediaCloudinaryStorage'
$env:DATABASE_URL = [Net.NetworkCredential]::new('', (Read-Host 'Render EXTERNAL PostgreSQL URL (SSL required)' -AsSecureString)).Password
$env:CLOUDINARY_CLOUD_NAME = Read-Host 'Cloudinary cloud name'
$env:CLOUDINARY_API_KEY = [Net.NetworkCredential]::new('', (Read-Host 'Cloudinary API key' -AsSecureString)).Password
$env:CLOUDINARY_API_SECRET = [Net.NetworkCredential]::new('', (Read-Host 'Cloudinary API secret' -AsSecureString)).Password
```

Use Render's EXTERNAL database URL, with `sslmode=require` as appropriate; not its
internal host. Do not paste credentials into chat, commit them or write them into
scripts. Do not start the local web server in this production-connected shell.

3. Dry run (reads production database and checks remote existence; no uploads or
   writes). Review total_references/local_found/already_cloud_hosted/missing_local/
   would_upload/errors. Remote lookups may take time on a large catalog.

```powershell
.\.venv\Scripts\python.exe manage.py migrate_media_to_cloudinary --dry-run --media-root 'C:\Users\danyb\Desktop\suryavets-django\media'
```

4. Apply only after reviewing the dry run and confirming the backup:

```powershell
.\.venv\Scripts\python.exe manage.py migrate_media_to_cloudinary --media-root 'C:\Users\danyb\Desktop\suryavets-django\media'
```

The command discovers FileField/ImageField references through Django's model
registry, never source_url. It uses the configured Cloudinary backend and a
media-upload subclass with deterministic public IDs and overwrite=False. IDs
include the original path plus content hash, retaining folders under
`media/svm/` with the adapter's default prefix. The short namespace fits existing
100-character thumbnail fields without a schema change. Shared references reuse an upload. Existing remote assets are
skipped. Missing/unsafe/empty files are reported and left unchanged. Each database
update compares the old name so concurrent edits are not overwritten. Provider
errors are redacted. No local file is removed. Interruptions are retryable: an
uploaded deterministic asset is reused even if the database update did not run.

5. Run dry-run again, inspect production homepage/categories/product cards, and
   review any missing/error IDs. Close the credential-bearing shell afterward.

## Deployment / limitations

Deploy the code commit once. Uploading media and changing approved homepage
selections afterward do not require another deployment. Refresh the storefront.
WhiteNoise/static collection, PostgreSQL configuration, models and payment logic
are unchanged. No schema migration is needed. No real production credentials or
uploads were tested during implementation. A successful local dry run does not
certify production assets or permissions. Non-image FileFields, if later added,
need a suitable Cloudinary raw-resource backend rather than this image backend.

Validation: 54 focused migration/homepage/media/purchase-safety tests and six
Cloudinary/WhiteNoise configuration tests passed. Django checks and migration
drift check passed. The final local dry run reported 5,245 prospective uploads,
zero missing references and zero errors. The public Render URL could not be
reached from the implementation environment; live deployment is not certified.

"""Repeatable, SELECT-only catalog review exports. No apply/import mode."""
import csv
import json
import shutil
from pathlib import Path
from time import perf_counter
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from shop.services.catalog_quality import HEADERS, build_report, fingerprint, select_only


def csv_cell(value):
    if isinstance(value, bool):
        return 'YES' if value else 'NO'
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value


class Command(BaseCommand):
    help = 'Read-only catalog/ledger/source audit. Generates nine CSV review files plus summary and integrity manifest.'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', default='catalog_review')
        parser.add_argument('--sources', nargs='+', default=[])
        parser.add_argument('--inventory', help='Historical inventory CSV, evidence only; never applied.')
        parser.add_argument('--archive-existing', action='store_true', help='Preserve previous generated reports before replacing them.')
        parser.add_argument('--profile', action='store_true', help='Measure anonymous rendered GETs, never cart/order writes.')

    def handle(self, *args, **options):
        started = timezone.now()
        root = Path(options['output_dir']).resolve()
        with transaction.atomic():
            with connection.execute_wrapper(select_only):
                before = fingerprint()
                reports, counts, provenance = build_report(options['sources'], options['inventory'])
                measurements = []
                if options['profile']:
                    client = Client(HTTP_HOST='localhost')
                    for url in ['/category/dog/', '/search/?q=royal', '/category/dog/?sort=price_low']:
                        for sample in range(1, 4):
                            with CaptureQueriesContext(connection) as queries:
                                begin = perf_counter()
                                response = client.get(url)
                                seconds = perf_counter() - begin
                            measurements.append({'endpoint': url, 'sample': sample, 'status': response.status_code,
                                'seconds': round(seconds, 4), 'queries': len(queries),
                                'sql_seconds': round(sum(float(q['time']) for q in queries), 4)})
                after = fingerprint()
                if before != after:
                    raise CommandError('Business records changed during the audit; no reports written.')
        files = [*reports, 'catalog_summary.md', 'audit_manifest.json']
        existing = [root / name for name in files if (root / name).exists()]
        if existing and not options['archive_existing']:
            raise CommandError('Reports already exist. Use a new output directory or --archive-existing to preserve them.')
        root.mkdir(parents=True, exist_ok=True)
        if existing:
            archive = root / ('history-' + started.strftime('%Y%m%d-%H%M%S-%f'))
            archive.mkdir()
            for path in existing:
                shutil.copy2(path, archive / path.name)
        empty_headers = {
            'duplicate_or_similar_products.csv': ['Signal', 'Matching Value', 'Confidence', 'Product IDs', 'Variant IDs', 'Products', 'SKUs', 'Packs', 'Already Same Family', 'Recommended Action', 'Owner Decision', 'Owner Evidence'],
            'best_seller_review.csv': ['Product ID', 'Product', 'Family', 'Variant Count', 'Current Best Seller Flag', 'Sales Evidence Available?', 'Local Paid Units', 'Featured?', 'Image Available?', 'Price Valid?', 'Stock Valid?', 'Recommended Status', 'Owner Decision', 'Owner Rank', 'Owner Evidence']}
        for name, rows in reports.items():
            headers = list(rows[0]) if rows else empty_headers.get(name, HEADERS)
            with (root / name).open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=headers)
                writer.writeheader()
                writer.writerows({key: csv_cell(value) for key, value in row.items()} for row in rows)
        manifest = {'generated_at': started.isoformat(), 'source_files': provenance, 'counts': counts,
            'reports': {name: len(rows) for name, rows in reports.items()}, 'before': before, 'after': after,
            'business_data_unchanged': before == after, 'select_only_guard_enabled': True, 'performance': measurements}
        (root / 'audit_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        lines = ['# SuryaVets catalog quality audit', '', f'Generated {started.isoformat()}. Phase 1: read-only review preparation.', '',
            '**Safe to review: yes. Launch-ready: no. No product, stock, ledger, order, approval, image assignment or merchandising flag was changed.**', '',
            '## Counts', '', '| Measure | Count |', '| --- | ---: |']
        lines += [f'| {key.replace("_", " ")} | {value:,} |' for key, value in counts.items()]
        lines += ['', '## Definitions and limitations', '',
            '- Master rows are one per variant, or one per simple product. Inactive records are included. Flag groups overlap and must not be summed.',
            '- Publishable is a diagnostic recommendation, not a live enforcement field or launch certification. Current CRM review records do not gate purchase. No explicit free-item approval rule exists.',
            '- Current checkout rejects negative prices but permits zero; add-to-cart does not enforce positive prices. Phase 2 must protect all purchase entry points, existing carts and atomic checkout. This audit has not enabled that safeguard.',
            '- Missing usable images include missing/corrupt local files and unverified remote references. Local originals were opened and verified with Pillow. Remote URLs and external storage were not fetched. File validity does not prove correct packaging.',
            '- Missing variant assignment is separate from missing displayed image. Existing single-pack product-image fallback is recorded, not newly approved. No images were downloaded or reassigned.',
            '- Ledger-derived stock starts from the first observed quantity_before plus later deltas, not an assumed opening balance of zero. No ledger observation is uncertainty, not proof of corruption. Balanced development adjustments do not prove physical stock.',
            '- Quantity=10 and quantities shared by at least 20 variants and 10% of variants are review signals. Zero stock is legitimate but needs availability review. Stock findings never trigger corrections.',
            '- Title/handle quantity mismatches are candidates: words may refer to animal weight, dose, or a former handle. A slug never determines the correct pack. Missing normalization disables reliable unit-value claims.',
            '- Source matching uses exact handle/options and separately checks SKU. Missing and ambiguous source matches remain visible. Export price differences may be legitimate later edits; exports are historical evidence, not current approval.',
            '- Duplicate report counts candidate groups, not confirmed duplicate products. Existing same-family packs are labelled and may be intentional. No fuzzy-name merges are performed.',
            '- Local paid-order units are not verified historical Shopify sales and may include development orders. Imported best-seller flags are not sales evidence.',
            '- Specialist handling flags are owner-review keywords and existing prescription metadata, not legal, clinical, shipping or cold-chain determinations.',
            '- CSV is UTF-8 with BOM. Import identifier/SKU columns as Text to preserve leading zeros. Dangerous leading formula characters are escaped with an apostrophe; source records are unchanged. Owner Decision/Evidence columns are blank for review.',
            '', '## Existing architecture and gaps', '',
            '- Product/variant/image/category/brand models, canonical variant_family links, normalized quantities and comparison groups already exist; no duplicate models or migration added.',
            '- Exact-price services, same-family selection, stock ledger and permission-controlled stock adjustments already exist. Ordinary product edits do not rewrite stock history.',
            '- CRM supports edit/archive/restore, photos, variant price/SKU edits, missing-image/pack-image/low-stock/review filters and signed approval evidence. Broader quality filters are a later phase.',
            '- Product cards currently preselect the cheapest available pack and show inline choices, not the requested explicit Choose Size bottom sheet. Keep explicit variant IDs in the later UI change.',
            '- Homepage currently selects six best-seller candidates from imported flags (bounded candidate window), with featured fallback. No staff-curated rank or dedicated new-arrival/promotional workflow yet.',
            '', '## Proposed merchandising workflow', '',
            'Reuse existing staff permissions and catalog approval. Add explicit owner-curated placement/rank for Best Seller, Featured, New Arrival and Promotional, separate from legacy imported flags. Require eligible approved packs and exact images. Configure a homepage limit of 8–20; leave selections empty until authorized staff choose products. Do not mass-reset existing flags or invent sales evidence.',
            '', '## Next phases', '',
            '2. Enforce nonpositive/inactive/invalid/held or unreviewed purchase safety consistently, with a controlled local rollout and regression tests.',
            '3–4. Review exact source pack identities and image coverage in CRM. Owner approval precedes any correction or regrouping.',
            '5–6. Implement explicit merchandising placements and missing quality filters, then the mobile Choose Size interaction.',
            '7–8. Recheck performance after purchase gating and complete regression tests. No Render or Shopify changes.',
            '', '## Evidence sources', '']
        lines += [f'- `{source["file"]}` — SHA-256 `{source["sha256"]}`' for source in provenance]
        lines += ['', 'Local database is the primary current-state source. `audit_manifest.json` records matching before/after business-row hashes. No customer details are included in the CSVs.', '',
            '## Current performance (rendered anonymous Django GET, excludes network/assets)', '', '| Endpoint | Sample | HTTP | Queries | Seconds |', '| --- | ---: | ---: | ---: | ---: |']
        lines += [f'| {m["endpoint"]} | {m["sample"]} | {m["status"]} | {m["queries"]} | {m["seconds"]} |' for m in measurements]
        (root / 'catalog_summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        self.stdout.write(json.dumps(counts, indent=2))
        self.stdout.write(f'Reports saved to {root}. Business-row fingerprints unchanged.')

"""SELECT-only pack identity audit. No apply mode and no model saves."""
import csv
import json
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from shop.services.catalog_quality import fingerprint, select_only
from shop.services.pack_identity import HEADERS, build_identity_report
from .audit_catalog_quality import csv_cell


class Command(BaseCommand):
    help = 'Generate exact pack/source identity review evidence without modifying catalog records.'

    def add_arguments(self, parser):
        parser.add_argument('--sources', nargs='+', default=[])
        parser.add_argument('--output-dir', default='catalog_review')
        parser.add_argument('--archive-existing', action='store_true')
        parser.add_argument('--image-observations', help='Optional SHA-256-bound visual observations, evidence only.')

    def handle(self, *args, **options):
        root = Path(options['output_dir']).resolve()
        names = ['variant_pack_review.csv', 'pack_identity_priority.csv', 'pack_identity_manifest.json', 'pack_identity_crm.json']
        existing = [root / name for name in names if (root / name).exists()]
        if existing and not options['archive_existing']:
            raise CommandError('Use --archive-existing or a new output folder; previous reports will not be overwritten silently.')
        with transaction.atomic(), connection.execute_wrapper(select_only):
            before = fingerprint()
            rows, summary, sources = build_identity_report(options['sources'], options['image_observations'])
            after = fingerprint()
            if before != after:
                raise CommandError('Business data changed. Reports not written.')
        created = timezone.now()
        root.mkdir(parents=True, exist_ok=True)
        if existing:
            archive = root / ('identity-history-' + created.strftime('%Y%m%d-%H%M%S-%f'))
            archive.mkdir()
            for path in existing:
                shutil.copy2(path, archive / path.name)
        priority = sorted((r for r in rows if r['Priority']), key=lambda r: (r['Priority'], r['Product Name'], str(r['Variant ID'])))
        for name, output in [('variant_pack_review.csv', rows), ('pack_identity_priority.csv', priority)]:
            with (root / name).open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows({k: csv_cell(v) for k, v in row.items()} for row in output)
        manifest = {'generated_at': created.isoformat(), 'counts': summary, 'sources': sources,
                    'business_data_unchanged': before == after, 'before': before, 'after': after,
                    'select_only_guard': True, 'rules_version': 1,
                    'limitations': ['Candidates are not confirmed identity errors. Hash-bound visual discrepancies are separately labelled.', 'Image pixels not batch verified; only explicit hash-bound observations are applied.',
                        'No dedicated Shopify handle field; exact export handle-to-slug match only.',
                        'Severity counts are unique rows at highest priority; issue-type counts overlap.',
                        'Historical exports are evidence, not approval. No physical stock verification.']}
        (root / names[2]).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        # Fixed-path staff-only snapshot; no public endpoint serves this evidence.
        (root / names[3]).write_text(json.dumps({'generated_at': created.isoformat(), 'rows': priority}), encoding='utf-8')
        self.stdout.write(json.dumps(summary, indent=2))
        self.stdout.write('Reports saved. All business-row fingerprints match; no source corrections applied.')

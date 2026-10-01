"""Dry-run-first recovery with an immutable pre-apply relationship backup."""
import csv
import hashlib
import json
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from shop.models import ProductImage, ProductVariant, CRMActivity
from shop.services.catalog_quality import fingerprint
from shop.services.image_recovery import build_index, validate_file
from shop.services.product_media import download_image


def write_csv(path, headers, rows):
    def safe(value):
        text = str(value if value is not None else '')
        return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream); writer.writerow(headers)
        writer.writerows([[safe(v) for v in row] for row in rows])


def signature(report):
    return hashlib.sha256(json.dumps({'plans': report['plans'], 'sources': report['sources'],
        'validation': report['validation']}, sort_keys=True, default=str).encode()).hexdigest()


class Command(BaseCommand):
    help = 'Validate trusted image sources and plan recovery. Dry-run by default; never changes prices/stock.'

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--dry-run', action='store_true')
        mode.add_argument('--apply', action='store_true')
        parser.add_argument('--sources', nargs='*', default=[])
        parser.add_argument('--output-dir', default='catalog_review')
        parser.add_argument('--validated-plan', help='Required with --apply: JSON plan generated and validated during dry-run.')

    def handle(self, *args, **options):
        folder = Path(options['output_dir']); folder.mkdir(parents=True, exist_ok=True)
        sources = options['sources']
        if not sources:
            previous = Path(settings.BASE_DIR)/'catalog_review'/'image_coverage_data.json'
            if previous.exists():
                sources = [p['file'] for p in json.loads(previous.read_text(encoding='utf-8')).get('sources', []) if Path(p['file']).is_file()]
        before = fingerprint()
        variants_before = list(ProductVariant.objects.order_by('pk').values())
        report = build_index(sources)
        report['generated_at'] = timezone.now().isoformat()
        report['signature'] = signature(report)
        report['catalog_fingerprint'] = before
        changes = []
        historical_changes = []
        if (folder/'image_recovery_applied.csv').exists():
            with (folder/'image_recovery_applied.csv').open(encoding='utf-8-sig', newline='') as stream:
                historical_changes = list(csv.reader(stream))[1:]
        if options['apply']:
            if not options['validated_plan']:
                raise CommandError('--apply requires --validated-plan from a reviewed dry-run.')
            approved = json.loads(Path(options['validated_plan']).read_text(encoding='utf-8'))
            if approved.get('signature') != report['signature'] or approved.get('catalog_fingerprint') != before:
                raise CommandError('Source files or catalog changed. Generate and validate a new dry-run.')
            stamp = timezone.now().strftime('%Y%m%d-%H%M%S-%f')
            backup = folder/f'image-recovery-backup-{stamp}.json'
            backup.write_text(json.dumps({'images': list(ProductImage.all_objects.values()),
                'variants': list(ProductVariant.objects.values('id', 'product_id', 'image_id')),
                'fingerprint': before}, default=str, indent=2), encoding='utf-8')
            log = folder/f'image-recovery-applied-{stamp}.csv'
            headers = ['Product ID', 'Variant ID', 'Old Image', 'New Image', 'Source', 'Action', 'Timestamp']
            write_csv(log, headers, [])
            for candidate in report['plans']:
                if candidate['confidence'] != 'HIGH':
                    continue
                try:
                    photo = ProductImage.all_objects.filter(pk=candidate['photo_id']).first() if candidate['photo_id'] else None
                    full, thumb = (None, None) if photo and validate_file(photo.image)['valid'] else download_image(candidate['url'])
                    with transaction.atomic():
                        variant = ProductVariant.objects.select_for_update().select_related('product').get(pk=candidate['variant_id'])
                        if variant.image_id or str(variant.product_id) != candidate['product_id'] or variant.sku != candidate['sku'] or variant.name != candidate['variant_name'] or variant.product.name != candidate['product_name']:
                            continue
                        if photo:
                            photo = ProductImage.all_objects.select_for_update().get(pk=photo.pk)
                            if not photo.is_active or photo.check_error or photo.product_id != variant.product_id:
                                continue
                        else:
                            photo = ProductImage(product_id=variant.product_id, source_url=candidate['url'], alt_text=f'{variant.product.name} {variant.name}'[:200])
                        if full is not None:
                            # New storage names only. Existing files and verified images are never overwritten.
                            photo.image.save(f'recovered-{stamp}-{variant.pk}.webp', ContentFile(full), save=False)
                            photo.thumbnail.save(f'recovered-{stamp}-{variant.pk}-360.webp', ContentFile(thumb), save=False)
                        photo.checked_at = timezone.now(); photo.save()
                        ProductVariant.objects.filter(pk=variant.pk, image__isnull=True).update(image=photo)
                        CRMActivity.objects.create(kind='note', text=f'Image recovery [{variant.product_id}] variant {variant.pk}: empty assignment -> image {photo.pk}. HIGH source identity. Plan {report["signature"]}. Source {candidate["url"]}')
                        row = [candidate['product_id'], variant.pk, '', photo.pk, candidate['url'], 'HIGH exact recovery', timezone.now().isoformat()]
                        changes.append(row)
                    # Append after each successful transaction so later failures do not lose earlier events.
                    write_csv(log, headers, changes)
                except Exception as exc:
                    report['counts']['failed'] += 1
                    self.stderr.write(f'Variant {candidate["variant_id"]}: {type(exc).__name__}; mapping not applied.')
            # Validation metadata only. Do not clear earlier staff errors or activate rejected images.
            for image_id, checks in report['validation'].items():
                photo = ProductImage.all_objects.get(pk=image_id)
                if photo.check_error:
                    continue
                problem = checks['image']['error'] if photo.image and not checks['image']['valid'] else ''
                if problem and photo.image.name == checks['image_name']:
                    ProductImage.all_objects.filter(pk=image_id, image=photo.image.name, check_error='').update(check_error=problem, checked_at=timezone.now())
                    changes.append([str(photo.product_id), '', image_id, image_id, photo.image.name, 'VALIDATION: '+problem, timezone.now().isoformat()])
                if checks['thumbnail'] and not checks['thumbnail']['valid'] and photo.thumbnail.name == checks['thumbnail_name']:
                    ProductImage.all_objects.filter(pk=image_id, thumbnail=photo.thumbnail.name).update(thumbnail='')
                    changes.append([str(photo.product_id), '', image_id, image_id, photo.thumbnail.name, 'Invalid thumbnail reference cleared; original retained', timezone.now().isoformat()])
            write_csv(log, headers, changes)
            write_csv(folder/'image_recovery_applied.csv', headers, historical_changes + changes)
            report['after_coverage'] = build_index(sources)['coverage']
            # Image metadata/relationships may change; business data must not.
            after = fingerprint()
            for model, value in before.items():
                if model not in ('shop.ProductImage', 'shop.ProductVariant') and after[model] != value:
                    raise CommandError(f'Unexpected concurrent business data change: {model}; inspect backup.')
            def immutable(rows):
                return [{k: v for k, v in row.items() if k != 'image_id'} for row in rows]
            if immutable(variants_before) != immutable(list(ProductVariant.objects.order_by('pk').values())):
                raise CommandError('Variant identity, price or stock changed concurrently; inspect backup.')
        elif fingerprint() != before:
            raise CommandError('Catalog changed during dry-run; rerun when idle.')
        report['applied_count'] = sum(row[5] == 'HIGH exact recovery' for row in changes)
        report['applied_records'] = historical_changes + changes
        if not options['apply'] and (folder/'image_recovery_applied.csv').exists():
            with (folder/'image_recovery_applied.csv').open(encoding='utf-8-sig', newline='') as stream:
                report['applied_records'] = list(csv.reader(stream))[1:]
        recovered = {str(row[1]): row for row in report['applied_records'] if row[5] == 'HIGH exact recovery'}
        for row in report['rows']:
            if row[3] in recovered:
                photo = ProductImage.objects.filter(pk=recovered[row[3]][3]).first()
                if photo and photo.display_url:
                    row[7] = photo.display_url
                    row[14] = 'RECOVERED / PRESERVE'
        write_csv(folder/'image_recovery_candidates.csv', report['headers'], report['rows'])
        unresolved = [r for r in report['rows'] if not r[7] or r[10] != 'HIGH']
        write_csv(folder/'image_recovery_unresolved.csv', report['headers'], unresolved)
        if not options['apply'] and not (folder/'image_recovery_applied.csv').exists():
            write_csv(folder/'image_recovery_applied.csv', ['Product ID', 'Variant ID', 'Old Image', 'New Image', 'Source', 'Action', 'Timestamp'], [])
        (folder/'image_recovery_index.json').write_text(json.dumps(report, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(json.dumps({'counts': report['counts'], 'before': report['coverage'],
            'after': report.get('after_coverage', report['coverage']), 'applied': report['applied_count'],
            'unassigned_files': len(report['unassigned_files']), 'duplicate_groups': len(report['duplicates'])}))

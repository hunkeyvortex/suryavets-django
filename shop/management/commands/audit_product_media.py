"""Application CSV export for image coverage, with optional safe media migration."""
import csv
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from shop.models import Product, ProductImage
from shop.services.product_media import download_image, image_identity, nutrition_sections
from shop.management.commands.import_shopify_products import Command as ShopifyReader


def csv_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text


class Command(BaseCommand):
    help = 'Audit every product; optionally migrate exact exported images and stage nutrition for review. Never modifies stock/prices.'

    def add_arguments(self, parser):
        parser.add_argument('--report', required=True, help='Output CSV audit file.')
        parser.add_argument('--sources', nargs='+', help='Authorized Shopify CSV/ZIP exports, matched by exact handle.')
        parser.add_argument('--apply', action='store_true', help='Stage missing nutrition and add exact export image references.')
        parser.add_argument('--download', action='store_true', help='With --apply, download referenced Shopify images to configured media storage.')
        parser.add_argument('--limit', type=int, default=0, help='Limit download count only; zero means all missing local images.')
        parser.add_argument('--workers', type=int, default=4)

    def handle(self, *args, **options):
        if options['download'] and not options['apply']:
            raise CommandError('--download requires --apply')
        if not 1 <= options['workers'] <= 6 or options['limit'] < 0:
            raise CommandError('Use 1–6 workers and a nonnegative download limit.')
        summary = Counter()
        if options['sources']:
            for handle, rows in ShopifyReader()._product_groups(options['sources']):
                product = Product.objects.filter(slug=handle).first()
                if not product:
                    summary['unmatched_handles'] += 1; continue
                primary = next((row for row in rows if row.get('Title')), rows[0])
                sections = nutrition_sections(primary.get('Body (HTML)', ''))
                if any(sections.values()):
                    summary['nutrition_candidates'] += 1
                if not options['apply']:
                    continue
                with transaction.atomic():
                    product = Product.objects.select_for_update().get(pk=product.pk)
                    # Never overwrite staff edits/reviewed information or re-stage an existing draft.
                    if not product.ingredients and not product.nutrition_information and not product.nutrition_reviewed and any(sections.values()):
                        product.ingredients = sections['ingredients']
                        product.nutrition_information = sections['nutrition_information']
                        product.nutrition_source = 'https://suryavets.com/products/' + handle
                        product.nutrition_source_note = 'Extracted from supplied Shopify product export. Unverified draft; check current manufacturer label and exact pack before publishing.'
                        product.save(update_fields=['ingredients','nutrition_information','nutrition_source','nutrition_source_note','updated_at'])
                        summary['nutrition_drafts_staged'] += 1
                    known = {image_identity(p.source_url) for p in ProductImage.all_objects.filter(product=product) if p.source_url}
                    for row in rows:
                        url = (row.get('Image Src') or '').strip()
                        if not url or image_identity(url) in known:
                            continue
                        try:
                            position = int(row.get('Image Position') or 1)
                        except ValueError:
                            position = 1
                        ProductImage.objects.create(product=product, source_url=url, image='', order=max(0, position-1),
                            alt_text=(row.get('Image Alt Text') or product.name)[:200], is_primary=not known)
                        known.add(image_identity(url)); summary['image_references_added'] += 1
        if options['download']:
            # Only images lacking migrated files. Existing staff uploads are never replaced.
            images = ProductImage.objects.filter(image='').exclude(source_url='').order_by('pk')
            if options['limit']:
                images = images[:options['limit']]
            jobs = list(images.values_list('pk', 'source_url'))
            self.stdout.write(f'Migrating {len(jobs)} image references using {options["workers"]} workers.')
            with ThreadPoolExecutor(max_workers=options['workers']) as executor:
                futures = {executor.submit(download_image, url): (pk, url) for pk, url in jobs}
                for index, future in enumerate(as_completed(futures), 1):
                    pk, url = futures.pop(future)
                    try:
                        full, thumb = future.result()
                    except Exception as exc:
                        ProductImage.objects.filter(pk=pk, image='', source_url=url).update(checked_at=timezone.now(), check_error=f'{type(exc).__name__}: {str(exc)[:190]}')
                        summary['download_failed'] += 1
                    else:
                        with transaction.atomic():
                            record = ProductImage.objects.select_for_update().filter(pk=pk, image='', source_url=url).first()
                            if record:
                                record.image.save(f'shopify-{pk}.webp', ContentFile(full), save=False)
                                record.thumbnail.save(f'shopify-{pk}-360.webp', ContentFile(thumb), save=False)
                                record.checked_at = timezone.now(); record.check_error = ''
                                record.save(update_fields=['image','thumbnail','checked_at','check_error'])
                                summary['images_migrated'] += 1
                    if index % 50 == 0:
                        self.stdout.write(f'Checked {index}/{len(jobs)} images; migrated={summary["images_migrated"]}, failed={summary["download_failed"]}')
                        self.stdout.flush()
        report = Path(options['report']); report.parent.mkdir(parents=True, exist_ok=True)
        with report.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['Product','Handle','SKU','Variant','Image Count','Missing Image','Broken Image','Duplicate References','Source','Local Images','Nutrition Review','Action Required','Missing Variant Images'])
            for product in Product.objects.prefetch_related('images','variants').order_by('slug').iterator(chunk_size=300):
                images = list(product.images.all())
                refs = [image_identity(p.source_url) for p in images if p.source_url]
                local_missing = any(p.image and not p.image.storage.exists(p.image.name) for p in images)
                errors = [p.check_error for p in images if p.check_error]
                usable = [p for p in images if p.image or p.source_url]
                unchecked = any(not p.checked_at and not p.image for p in images)
                confirmed_missing = local_missing or any('HTTP Error 404' in error or 'HTTP Error 410' in error for error in errors)
                status = 'YES' if confirmed_missing else ('CHECK FAILED' if errors else ('UNCHECKED' if unchecked else 'NO'))
                action = 'IMAGE REQUIRED' if not usable else ('CHECK IMAGE SOURCE' if confirmed_missing or errors else ('VERIFY REMOTE IMAGE' if unchecked else ''))
                writer.writerow([csv_cell(x) for x in [product.name, product.slug, product.sku,
                    ' | '.join(v.name for v in product.variants.all()), len(usable), 'YES' if not usable else 'NO', status,
                    len(refs)-len(set(refs)), ' | '.join(p.source_url for p in images if p.source_url),
                    sum(bool(p.image) for p in images), 'Reviewed' if product.nutrition_reviewed else ('Draft' if product.ingredients or product.nutrition_information else 'Not provided'), action,
                    ' | '.join(f'{v.name} [{v.sku}]' for v in product.variants.all() if v.is_active and v.image_id not in {p.pk for p in usable})]])
                summary['products'] += 1
                if not usable: summary['products_missing_images'] += 1
        self.stdout.write(str(dict(summary)))
        self.stdout.write(f'Audit saved: {report}')

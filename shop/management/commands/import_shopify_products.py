"""Import Shopify product CSV files (including CSV files inside ZIP archives)."""

import csv
import io
import zipfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import strip_tags
from django.utils.text import slugify

from shop.models import Brand, Category, PetCategory, Product, ProductImage, ProductType, ProductVariant, Subcategory
from shop.services.pricing import export_prices


PET_RULES = (
    ('Vaccination', ('vaccination', 'vaccine')),
    ('Pet Grooming', ('grooming', 'groom')),
    ('Cat', ('cat',)),
    ('Dog', ('dog',)),
    ('Farm Animals', ('farm animals', 'farm-animal', 'farm animal')),
    ('Fish & Reptiles', ('fish', 'reptile')),
)
SUBCATEGORY_RULES = (
    ('Medicine', ('medicine', 'antibiotic', 'dewormer', 'injectable')),
    ('Supplements', ('supplement', 'vitamin')),
    ('Food', ('food', 'kibble', 'wet-food', 'dry-food', 'can')),
    ('Treats', ('treat', 'chew', 'biscuit')),
    ('Supplies', ('supplies', 'supply', 'accessory', 'shampoo', 'toy', 'grooming')),
)
KNOWN_TYPES = ('tablet', 'syrup', 'kibble', 'can', 'powder', 'spray', 'drops', 'capsule', 'ointment', 'cream', 'liquid', 'vial', 'bolus', 'gel')
CATEGORY_ORDER = {
    'Cat': 1,
    'Dog': 2,
    'Farm Animals': 3,
    'Fish & Reptiles': 4,
    'Vaccination': 5,
    'Pet Grooming': 6,
    'Uncategorized': 99,
}


def decimal_value(value, default=Decimal('0.00')):
    try:
        return Decimal(str(value or '')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return default


def truthy(value):
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'y'}


def clean_text(value):
    return ' '.join(strip_tags(value or '').replace('\xa0', ' ').split())


def option_name(row):
    values = [str(row.get(f'Option{index} Value') or '').strip() for index in range(1, 4)]
    values = [value for value in values if value and value.lower() != 'default title']
    return ' / '.join(values) or 'Default Title'


class Command(BaseCommand):
    help = 'Import one or more Shopify product CSV/ZIP exports into the Django catalogue.'

    def add_arguments(self, parser):
        parser.add_argument('sources', nargs='+', help='Shopify product CSV or ZIP file paths.')
        parser.add_argument('--inventory', help='Optional Shopify inventory CSV, used to override variant stock.')
        parser.add_argument('--dry-run', action='store_true', help='Validate and report counts without changing the database.')
        parser.add_argument('--limit', type=int, help='Import only this many product handles (useful for a trial run).')
        parser.add_argument('--remove-demo', action='store_true', help='Remove only local products whose SKU begins with DEMO-.')

    def _open_csv(self, path):
        path = Path(path)
        if not path.exists():
            raise CommandError(f'File not found: {path}')
        if path.suffix.lower() == '.zip':
            archive = zipfile.ZipFile(path)
            entries = [entry for entry in archive.infolist() if entry.filename.lower().endswith('.csv')]
            if len(entries) != 1:
                archive.close()
                raise CommandError(f'{path.name} must contain exactly one CSV file.')
            stream = io.TextIOWrapper(archive.open(entries[0]), encoding='utf-8-sig', newline='')
            return stream, archive
        return path.open(encoding='utf-8-sig', newline=''), None

    def _inventory(self, path):
        if not path:
            return {}
        inventory = {}
        with Path(path).open(encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source)
            stock_columns = [column for column in reader.fieldnames or [] if column not in {
                'Handle', 'Title', 'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value',
                'Option3 Name', 'Option3 Value', 'SKU', 'HS Code', 'COO',
            }]
            if not stock_columns:
                raise CommandError('Inventory CSV does not contain a location stock column.')
            for row in reader:
                key = (row.get('Handle', '').strip(), option_name(row), row.get('SKU', '').strip())
                quantities = [decimal_value(row.get(column), Decimal('0')) for column in stock_columns]
                inventory[key] = max(0, int(sum(quantities)))
        return inventory

    def _product_groups(self, sources):
        groups = defaultdict(list)
        for source_path in sources:
            stream, archive = self._open_csv(source_path)
            try:
                reader = csv.DictReader(stream)
                if not {'Handle', 'Variant Price'}.issubset(reader.fieldnames or []):
                    raise CommandError(f'{source_path}: expected a Shopify product export with Handle and Variant Price columns.')
                for row in reader:
                    handle = (row.get('Handle') or '').strip()
                    if not handle:
                        continue
                    groups[handle].append(row)
            finally:
                stream.close()
                if archive:
                    archive.close()
        yield from groups.items()

    def _priced_rows(self, handle, rows):
        """Collapse repeated rows, but reject conflicting variant identities/prices."""
        variants = {}
        for row in rows:
            if not (row.get('Variant Price') or row.get('Variant SKU') or option_name(row) != 'Default Title'):
                continue
            name = option_name(row)
            if len(name) > 100:
                raise CommandError(f'{handle}: variant name exceeds 100 characters; do not truncate identity.')
            try:
                prices = export_prices(row)
            except ValueError as error:
                raise CommandError(f'{handle} / {name}: {error}') from error
            if name in variants:
                previous = variants[name]
                if export_prices(previous) != prices or previous.get('Variant SKU') != row.get('Variant SKU'):
                    raise CommandError(f'{handle}: conflicting export rows for variant {name}.')
            else:
                variants[name] = row
        if not variants:
            raise CommandError(f'{handle}: no priced variant rows found.')
        return list(variants.values())

    def _tags(self, row):
        return {tag.strip().lower() for tag in (row.get('Tags') or '').split(',') if tag.strip()}

    def _category_data(self, tags):
        pets = [name for name, terms in PET_RULES if any(any(term in tag for tag in tags) for term in terms)]
        category_name = pets[0] if pets else 'Uncategorized'
        subcategory_name = next((name for name, terms in SUBCATEGORY_RULES if any(any(term in tag for term in terms) for tag in tags)), None)
        return category_name, pets, subcategory_name

    def _product_type(self, row, tags):
        value = (row.get('Type') or '').strip()
        if value:
            return value[:50]
        return next((item.title() for item in KNOWN_TYPES if item in tags), '')

    def _stock_for(self, row, inventory):
        key = ((row.get('Handle') or '').strip(), option_name(row), (row.get('Variant SKU') or '').strip())
        if key in inventory:
            return inventory[key]
        # Shopify leaves the tracker blank for products whose stock is not managed.
        # Our current variant model has no separate tracking flag, so retain availability
        # with a placeholder quantity until a full inventory export is supplied.
        if not (row.get('Variant Inventory Tracker') or '').strip():
            return 1
        return max(0, int(decimal_value(row.get('Variant Inventory Qty'), Decimal('0'))))

    def _import_group(self, handle, rows, inventory, dry_run):
        primary = next((row for row in rows if row.get('Title')), rows[0])
        title = (primary.get('Title') or handle).strip()[:200]
        tags = self._tags(primary)
        category_name, pet_names, subcategory_name = self._category_data(tags)
        product_type_name = self._product_type(primary, tags)
        variant_rows = self._priced_rows(handle, rows)
        regular_price, first_price, discount = export_prices(variant_rows[0])
        total_stock = sum(self._stock_for(row, inventory) for row in variant_rows) if variant_rows else 0
        payload = {
            'shopify_tags': sorted(tags),
            'name': title,
            'description': clean_text(primary.get('Body (HTML)')),
            'short_description': clean_text(primary.get('Body (HTML)'))[:500],
            'sku': (primary.get('Variant SKU') or '')[:100],
            'base_price': regular_price,
            'selling_price': first_price,
            'discount_percentage': max(0, discount),
            'stock_quantity': total_stock,
            'track_inventory': bool(primary.get('Variant Inventory Tracker')),
            'manufacturer': (primary.get('Vendor') or '')[:100],
            'requires_prescription': truthy(primary.get('Prescription Required (product.metafields.suryavets.prescription_required)')),
            'is_featured': 'best-seller' in tags or 'bestsellers' in tags,
            'is_bestseller': 'best-seller' in tags or 'bestsellers' in tags,
            'is_active': (primary.get('Status') or 'active').lower() == 'active' and truthy(primary.get('Published') or 'true'),
            'meta_title': (primary.get('SEO Title') or '')[:200],
            'meta_description': primary.get('SEO Description') or '',
        }
        if dry_run:
            return category_name, pet_names, subcategory_name, product_type_name, len(variant_rows), len({row.get('Image Src') for row in rows if row.get('Image Src')})

        category, _ = Category.objects.get_or_create(
            name=category_name,
            defaults={'order': CATEGORY_ORDER[category_name], 'is_active': category_name != 'Uncategorized'},
        )
        category.order = CATEGORY_ORDER[category_name]
        category.is_active = category_name != 'Uncategorized'
        category.save(update_fields=['order', 'is_active', 'updated_at'])
        subcategory = None
        if subcategory_name:
            subcategory, _ = Subcategory.objects.get_or_create(category=category, name=subcategory_name, defaults={'is_active': True})
        brand = None
        vendor = (primary.get('Vendor') or '').strip()
        if vendor:
            brand = Brand.objects.filter(slug=slugify(vendor)).first()
            if brand is None:
                brand, _ = Brand.objects.get_or_create(name=vendor[:100], defaults={'is_active': True})
        product_type = None
        if product_type_name:
            product_type = ProductType.objects.filter(slug=slugify(product_type_name)).first()
            if product_type is None:
                product_type, _ = ProductType.objects.get_or_create(name=product_type_name)
        product, created = Product.objects.update_or_create(slug=handle, defaults={**payload, 'category': category, 'subcategory': subcategory, 'brand': brand, 'product_type': product_type})
        from shop.services.taxonomy import collection_tag_index, matching_collections
        if not hasattr(self, '_collection_index'):
            self._collection_index = collection_tag_index()
        product.collections.add(*matching_collections(tags, self._collection_index))
        pets = []
        for name in pet_names:
            pet, _ = PetCategory.objects.get_or_create(name=name, defaults={'order': CATEGORY_ORDER[name], 'is_active': True})
            if pet.order != CATEGORY_ORDER[name]:
                pet.order = CATEGORY_ORDER[name]
                pet.save(update_fields=['order', 'updated_at'])
            pets.append(pet)
        product.pet_categories.set(pets)

        for row in variant_rows:
            name = option_name(row)
            if name == 'Default Title' and len(variant_rows) == 1:
                continue
            regular, price, variant_discount = export_prices(row)
            ProductVariant.objects.update_or_create(product=product, name=name, defaults={
                'weight_info': name[:50], 'sku': (row.get('Variant SKU') or '')[:100],
                'barcode': (row.get('Variant Barcode') or row.get('Variant Barcodes') or '')[:100],
                'price_override': regular, 'selling_price': price, 'discount_percentage': variant_discount,
                'stock_quantity': self._stock_for(row, inventory), 'is_active': product.is_active,
            })

        images = []
        seen_urls = set()
        for row in rows:
            image_url = (row.get('Image Src') or '').strip()
            if not image_url or image_url in seen_urls:
                continue
            seen_urls.add(image_url)
            existing_image = product.images.filter(source_url=image_url).first()
            if existing_image is None:
                existing_image = ProductImage(product=product, image='', source_url=image_url)
            existing_image.alt_text = (row.get('Image Alt Text') or title)[:200]
            existing_image.order = len(images)
            existing_image.is_primary = not images
            existing_image.save()
            images.append(existing_image)
        return created, len(variant_rows), len(images)

    def handle(self, *args, **options):
        inventory = self._inventory(options.get('inventory'))
        dry_run = options['dry_run']
        limit = options.get('limit')
        summary = defaultdict(int)
        if options['remove_demo'] and not dry_run:
            removed, _ = Product.objects.filter(sku__startswith='DEMO-').delete()
            self.stdout.write(f'Removed {removed} local demo records.')

        for index, (handle, rows) in enumerate(self._product_groups(options['sources']), start=1):
            if limit and index > limit:
                break
            with transaction.atomic():
                result = self._import_group(handle, rows, inventory, dry_run)
            summary['products'] += 1
            if dry_run:
                category_name, pets, subcategory_name, product_type_name, variants, images = result
                summary['variants'] += variants
                summary['images'] += images
                summary[f'category:{category_name}'] += 1
            else:
                created, variants, images = result
                summary['created' if created else 'updated'] += 1
                summary['variants'] += variants
                summary['images'] += images
            if index % 500 == 0:
                self.stdout.write(f'Processed {index} product handles...')

        mode = 'Dry run complete' if dry_run else 'Import complete'
        self.stdout.write(self.style.SUCCESS(mode + ': ' + ', '.join(f'{key}={value}' for key, value in sorted(summary.items()))))

"""Attach supplied local image files to catalogue categories."""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from shop.models import Category


class Command(BaseCommand):
    help = 'Assign category images. Use --image "Category Name=C:\\path\\image.png" for each image.'

    def add_arguments(self, parser):
        parser.add_argument('--image', action='append', default=[], metavar='CATEGORY=PATH')

    def handle(self, *args, **options):
        for value in options['image']:
            if '=' not in value:
                raise CommandError('Each --image value must use CATEGORY=PATH.')
            category_name, image_path = value.split('=', 1)
            source = Path(image_path)
            if not source.is_file():
                raise CommandError(f'Image file was not found: {source}')
            category = Category.objects.filter(name__iexact=category_name.strip()).first()
            if not category:
                raise CommandError(f'No category named {category_name!r} exists.')
            with source.open('rb') as image_file:
                category.image.save(f'{category.slug}.png', File(image_file), save=True)
            self.stdout.write(self.style.SUCCESS(f'Updated {category.name}'))

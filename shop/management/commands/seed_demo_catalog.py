"""Create a small, clearly labelled local-only catalogue for UI testing."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from shop.models import Brand, Category, PetCategory, Product, ProductType


class Command(BaseCommand):
    help = 'Create local demo products so browsing, cart, and checkout can be tested.'

    def handle(self, *args, **options):
        cat, _ = Category.objects.get_or_create(name='Cat', defaults={'order': 1})
        dog, _ = Category.objects.get_or_create(name='Dog', defaults={'order': 2})
        cat_pet, _ = PetCategory.objects.get_or_create(name='Cat', defaults={'order': 1})
        dog_pet, _ = PetCategory.objects.get_or_create(name='Dog', defaults={'order': 2})
        nutrition, _ = Brand.objects.get_or_create(name='Demo Veterinary Nutrition')
        medicine, _ = Brand.objects.get_or_create(name='Demo Pet Care')
        kibble, _ = ProductType.objects.get_or_create(name='Kibble')
        tablet, _ = ProductType.objects.get_or_create(name='Tablet')

        products = (
            ('DEMO-CAT-001', 'Demo Cat Urinary Care Dry Food', cat, cat_pet, nutrition, kibble, '1863.00', 10),
            ('DEMO-CAT-002', 'Demo Persian Adult Dry Food', cat, cat_pet, nutrition, kibble, '2250.00', 10),
            ('DEMO-DOG-001', 'Demo Dog Tick Protection Tablet', dog, dog_pet, medicine, tablet, '1692.25', 18),
            ('DEMO-DOG-002', 'Demo Joint Support Chews', dog, dog_pet, medicine, tablet, '799.00', 12),
        )
        for sku, name, category, pet, brand, product_type, price, discount in products:
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name, 'category': category, 'brand': brand,
                    'product_type': product_type, 'base_price': Decimal(price),
                    'discount_percentage': discount, 'stock_quantity': 25,
                    'short_description': 'Local demo product for testing the Django storefront.',
                    'is_featured': True, 'is_bestseller': True,
                },
            )
            product.pet_categories.add(pet)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Kept'}: {product.name}"))

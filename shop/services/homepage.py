"""Bounded, database-driven homepage merchandising; no invented sales ranking."""
from django.db.models import Count, Exists, OuterRef, Q
from shop.models import Banner, Brand, Product
from shop.catalog_views import _product_queryset
from .navigation import navigation_tree
from .merchandising import curated


PET_ART = {'cat': 'reference-cat.png', 'dog': 'reference-dog.png',
    'farm-animals': 'reference-farm.jpg', 'fish-and-reptiles': 'reference-reptiles.png',
    'vaccination': 'reference-vaccination.jpg', 'pet-grooming': 'reference-grooming.jpg'}
NEEDS = (
    ('food-for-dogs', 'Daily nutrition', 'bowl'),
    ('food-for-cats', 'Meals for your cat', 'bowl'),
    ('medicine-for-dogs', 'Veterinary care', 'medical'),
    ('medicine-for-cats', 'Veterinary care', 'medical'),
    ('supplements-for-dogs', 'Everyday support', 'heart'),
    ('pet-grooming', 'Clean & comfortable', 'sparkle'),
)


def _flatten(nodes):
    for node in nodes:
        yield node
        yield from _flatten(node.menu_children)


def _in_category(products, category):
    ids = [node.pk for node in _flatten([category])]
    collection = Product.collections.through.objects.filter(product_id=OuterRef('pk'), category_id__in=ids)
    return products.filter(Q(category_id__in=ids) | Exists(collection))


def homepage_context():
    roots = navigation_tree()
    by_slug = {node.slug: node for node in _flatten(roots)}
    pets = [node for node in roots if node.slug != 'uncategorized']
    for category in pets:
        category.reference_image = 'images/' + PET_ART[category.slug] if category.slug in PET_ART else ''
    products = _product_queryset().order_by('-is_featured', '-created_at', 'pk')
    best = curated(products.filter(is_bestseller=True))
    title = 'Best sellers' if best else 'Featured picks'
    if not best:
        best = curated(products.filter(is_featured=True))
    food_tabs = []
    for species in ('dog', 'cat'):
        category = by_slug.get(f'food-for-{species}s')
        if category:
            food_tabs.append({'key': species, 'category': category,
                'products': curated(_in_category(products, category), 4)})
    food_tabs = [tab for tab in food_tabs if tab['products']]
    needs = [{'category': by_slug[slug], 'description': description, 'icon': icon}
             for slug, description, icon in NEEDS if slug in by_slug]
    brands = Brand.objects.filter(is_active=True).annotate(product_count=Count('products',
        filter=Q(products__is_active=True, products__variant_family__isnull=True))).filter(
        product_count__gt=0).order_by('-product_count', 'name')[:6]
    return {'categories': pets, 'banners': Banner.objects.filter(is_active=True).order_by('order', 'pk')[:3],
        'top_products': best, 'home_best_title': title, 'home_food_tabs': food_tabs,
        'home_needs': needs, 'home_brands': brands}

from collections import defaultdict

from .models import Category, ProductType
from .services.cart import cart_items, get_cart

def cart_count(request):
    """Expose the anonymous or authenticated cart count without creating a cart."""
    cart = get_cart(request, create=False)
    return {'cart_count': sum(item.quantity for item in cart_items(cart))}

def get_categories(request):
    """Add categories to context"""
    categories = list(Category.objects.filter(is_active=True).prefetch_related(
        'subcategories'
    ).order_by('order', 'name'))
    product_types_by_category = defaultdict(list)
    product_types = ProductType.objects.filter(
        product__is_active=True,
        product__category__in=categories,
    ).order_by('name').distinct()
    for product_type in product_types:
        category_ids = product_type.product_set.filter(
            is_active=True, category__in=categories
        ).values_list('category_id', flat=True).distinct()
        for category_id in category_ids:
            product_types_by_category[category_id].append(product_type)
    for category in categories:
        category.menu_product_types = product_types_by_category[category.id]
    return {'categories': categories}

def get_banners(request):
    """Add active banners to context"""
    banners = []
    try:
        banners = list(Category.objects.filter(is_active=True).order_by('order')[:5])
    except:
        pass
    return {'banners': banners}

def get_featured_products(request):
    """Add featured products to context"""
    products = []
    try:
        from .models import Product
        products = list(Product.objects.filter(
            is_active=True, 
            is_featured=True
        ).select_related('category', 'product_type').prefetch_related('images', 'variants')[:12])
    except:
        pass
    return {'featured_products': products}

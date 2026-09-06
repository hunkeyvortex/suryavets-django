from .models import Category
from .services.navigation import navigation_tree
from .services.cart import cart_items, get_cart

def cart_count(request):
    """Expose the anonymous or authenticated cart count without creating a cart."""
    cart = get_cart(request, create=False)
    return {'cart_count': sum(item.quantity for item in cart_items(cart))}

def get_categories(request):
    """Add categories to context"""
    tree = navigation_tree()
    return {'categories': tree, 'navigation_categories': tree}

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

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.contrib.auth.decorators import login_required
from .models import (
    Category, Subcategory, Product, ProductVariant, 
    ProductImage, Banner, Cart, CartItem
)

def index(request):
    """Home page view"""
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    top_products = Product.objects.filter(
        is_active=True, 
        is_featured=True
    ).select_related('category', 'subcategory').prefetch_related('images', 'variants')[:8]
    
    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    
    context = {
        'categories': categories,
        'top_products': top_products,
        'cart_count': cart_count,
    }
    return render(request, 'home_new.html', context)

def category_list(request):
    """List all categories"""
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('order', 'name')
    
    context = {
        'categories': categories,
        'total_count': Product.objects.filter(is_active=True).count(),
    }
    return render(request, 'shop_new.html', context)

def category_detail(request, category_slug):
    """Category detail page with products"""
    category = get_object_or_404(Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ), slug=category_slug, is_active=True)
    
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('order', 'name')
    
    products = Product.objects.filter(
        category=category,
        is_active=True
    ).select_related('category', 'subcategory').prefetch_related('images', 'variants')
    
    # Apply filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Apply sorting
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'categories': categories,
        'products': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'total_count': products.count(),
    }
    return render(request, 'shop_new.html', context)

def subcategory_detail(request, category_slug, subcategory_slug):
    """Subcategory detail page with products"""
    category = get_object_or_404(Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ), slug=category_slug, is_active=True)
    
    subcategory = get_object_or_404(Subcategory.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ), slug=subcategory_slug, category=category, is_active=True)
    
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('order', 'name')
    
    products = Product.objects.filter(
        subcategory=subcategory,
        is_active=True
    ).select_related('category', 'subcategory').prefetch_related('images', 'variants')
    
    # Apply filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Apply sorting
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'subcategory': subcategory,
        'categories': categories,
        'products': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'total_count': products.count(),
    }
    return render(request, 'shop_new.html', context)

def product_detail(request, product_slug):
    """Product detail page"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'subcategory', 'product_type')
        .prefetch_related('images', 'variants', 'specifications'),
        slug=product_slug,
        is_active=True
    )
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).select_related('category').prefetch_related('images')[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'product_detail_new.html', context)

@login_required
def cart_detail(request):
    """Shopping cart page"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('product', 'product_variant').prefetch_related('product__images')
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)
        cart_items = []
    
    subtotal = cart.subtotal
    shipping = 0 if subtotal >= 499 else 50
    total = subtotal + shipping
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
        'total_items': cart.total_items,
    }
    return render(request, 'cart_new.html', context)

@login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        variant_id = request.POST.get('variant_id')
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            
            if variant_id:
                variant = ProductVariant.objects.get(id=variant_id, product=product, is_active=True)
            else:
                variant = product.variants.first()
            
            # Check stock
            if variant and variant.stock_quantity < quantity:
                return JsonResponse({'success': False, 'message': 'Not enough stock available'})
            
            # Get or create cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Get or create cart item
            if variant:
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product_variant=variant,
                    defaults={'quantity': quantity}
                )
            else:
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    product_variant__isnull=True,
                    defaults={'quantity': quantity}
                )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            return JsonResponse({
                'success': True,
                'cart_count': cart.total_items,
                'message': 'Product added to cart'
            })
            
        except (Product.DoesNotExist, ProductVariant.DoesNotExist):
            return JsonResponse({'success': False, 'message': 'Product not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def update_cart_item(request, item_id):
    """Update cart item quantity via AJAX"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            quantity = data.get('quantity', 1)
            
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            
            if quantity < 1:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('shop:cart')

@login_required
def checkout(request):
    """Checkout page"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('product', 'product_variant').prefetch_related('product__images')
    except Cart.DoesNotExist:
        return redirect('shop:cart')
    
    if not cart_items:
        return redirect('shop:cart')
    
    subtotal = cart.subtotal
    shipping = 0 if subtotal >= 499 else 50
    total = subtotal + shipping
    
    if request.method == 'POST':
        # Process order (simplified - you'd integrate with payment gateway here)
        # For now, just clear the cart and show success
        cart.items.all().delete()
        return render(request, 'order_success.html')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'checkout_new.html', context)

def search(request):
    """Product search"""
    query = request.GET.get('q', '')
    
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(manufacturer__icontains=query),
            is_active=True
        ).select_related('category', 'subcategory').prefetch_related('images', 'variants')
    else:
        products = Product.objects.none()
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'query': query,
        'products': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    return render(request, 'search.html', context)

def login_view(request):
    """Login page"""
    if request.method == 'POST':
        from django.contrib.auth import authenticate, login
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'shop:index')
            return redirect(next_url)
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'login.html')

def logout_view(request):
    """Logout view"""
    from django.contrib.auth import logout
    logout(request)
    return redirect('shop:index')

def about(request):
    """About page"""
    return render(request, 'about.html')

def contact(request):
    """Contact page"""
    return render(request, 'contact.html')

def help(request):
    """Help center page"""
    return render(request, 'help.html')

def shipping(request):
    """Shipping policy page"""
    return render(request, 'shipping.html')

def privacy(request):
    """Privacy policy page"""
    return render(request, 'privacy.html')

def terms(request):
    """Terms and conditions page"""
    return render(request, 'terms.html')

def returns(request):
    """Return and refund policy page"""
    return render(request, 'returns.html')

def newsletter_signup(request):
    """Newsletter signup"""
    if request.method == 'POST':
        email = request.POST.get('email')
        # Here you would typically save to a newsletter model
        # For now, just return success
        return JsonResponse({'success': True, 'message': 'Thank you for subscribing!'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})
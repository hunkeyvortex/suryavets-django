from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.db import OperationalError
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .services.checkout import CheckoutError, place_order, review_token
from .models import (
    Category, Subcategory, Product, ProductVariant, 
    ProductImage, Banner, Cart, CartItem
)
from .services.cart import cart_items, cart_totals, get_cart
from .forms import AddressForm, CheckoutForm, RegistrationForm
from .models import CustomerAddress, Order, OrderItem

def index(request):
    """Home page view"""
    categories = Category.objects.filter(is_active=True, parent__isnull=True).order_by('order', 'name')
    reference_images = {'cat': 'reference-cat.png', 'dog': 'reference-dog.png', 'farm-animals': 'reference-farm.jpg', 'fish-and-reptiles': 'reference-reptiles.png', 'vaccination': 'reference-vaccination.jpg', 'pet-grooming': 'reference-grooming.jpg'}
    categories = list(categories)
    for category in categories:
        category.reference_image = 'images/' + reference_images[category.slug] if category.slug in reference_images else ''
    banners = Banner.objects.filter(is_active=True).order_by('order')[:3]
    top_products = Product.objects.filter(
        is_active=True
    ).filter(
        Q(is_bestseller=True) | Q(is_featured=True)
    ).select_related(
        'category', 'subcategory', 'brand', 'product_type'
    ).prefetch_related('images', 'variants')[:8]
    
    context = {
        'categories': categories,
        'banners': banners,
        'top_products': top_products,
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
        products = products.filter(base_price__gte=min_price)
    if max_price:
        products = products.filter(base_price__lte=max_price)
    
    # Apply sorting
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('base_price')
    elif sort == 'price_desc':
        products = products.order_by('-base_price')
    elif sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')
    
    # Add computed properties to products
    for product in products:
        product.price = product.base_price
        product.is_on_sale = product.discount_percentage > 0
        product.discount_percent = product.discount_percentage
        product.stock_quantity = product.variants.first().stock_quantity if product.variants.first() else 0
    
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
        products = products.filter(base_price__gte=min_price)
    if max_price:
        products = products.filter(base_price__lte=max_price)
    
    # Apply sorting
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('base_price')
    elif sort == 'price_desc':
        products = products.order_by('-base_price')
    elif sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')
    
    # Add computed properties to products
    for product in products:
        product.price = product.base_price
        product.is_on_sale = product.discount_percentage > 0
        product.discount_percent = product.discount_percentage
        product.stock_quantity = product.variants.first().stock_quantity if product.variants.first() else 0
    
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
    
    # Add computed properties
    product.price = product.base_price
    product.is_on_sale = product.discount_percentage > 0
    product.discount_percent = product.discount_percentage
    product.stock_quantity = product.variants.first().stock_quantity if product.variants.first() else 0
    product.sku = str(product.id)[:8].upper()
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).select_related('category').prefetch_related('images')[:4]
    
    # Add computed properties to related products
    for related in related_products:
        related.price = related.base_price
        related.is_on_sale = related.discount_percentage > 0
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'product_detail_new.html', context)

@never_cache
def cart_detail(request):
    """Display the current cart for an anonymous or authenticated shopper."""
    cart = get_cart(request, create=False)
    items = cart_items(cart)
    context = {'cart': cart, 'cart_items': items, **cart_totals(items)}
    return render(request, 'cart_new.html', context)

def _cart_return_url(request):
    target = request.POST.get('next', '')
    return target if url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()) else reverse('shop:cart')


@require_POST
@transaction.atomic
def add_to_cart(request, product_id):
    """Add a product to a session cart, respecting variant and stock choices."""
    cart = Cart.objects.select_for_update().get(pk=get_cart(request).pk)
    try:
        quantity = int(request.POST.get('quantity', 1))
        if not 1 <= quantity <= 10000:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, 'Please enter a quantity between 1 and 10000.')
        return redirect(_cart_return_url(request))
    product = get_object_or_404(Product, id=product_id, is_active=True)
    variant_id = request.POST.get('variant_id')
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product, is_active=True)
    else:
        active_variants = list(product.variants.filter(is_active=True))
        if len(active_variants) > 1:
            messages.info(request, 'Please choose a pack or variant before adding this product.')
            return redirect('shop:product_detail', product_slug=product.slug)
        variant = active_variants[0] if active_variants else None

    available_quantity = variant.stock_quantity if variant else product.stock_quantity
    if (variant or product.track_inventory) and available_quantity < quantity:
        messages.error(request, 'The requested quantity is not currently available.')
        return redirect(_cart_return_url(request))

    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, product_variant=variant, defaults={'quantity': quantity}
    )
    if not created:
        desired_quantity = item.quantity + quantity
        if (variant or product.track_inventory) and desired_quantity > available_quantity:
            messages.error(request, 'There is not enough stock to add more of this item.')
            return redirect(_cart_return_url(request))
        item.quantity = desired_quantity
        item.save(update_fields=['quantity'])
    messages.success(request, f'{product.name} was added to your cart.')
    return redirect(_cart_return_url(request))

@require_POST
@transaction.atomic
def update_cart_item(request, item_id):
    """Change a cart quantity through a normal CSRF-protected form post."""
    cart = get_cart(request, create=False)
    cart = get_object_or_404(Cart.objects.select_for_update(), pk=cart.pk if cart else None)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    try:
        quantity = int(request.POST.get('quantity', 1))
        if not 0 <= quantity <= 10000:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, 'Please enter a quantity between 0 and 10000.')
        return redirect('shop:cart')
    if quantity < 1:
        item.delete()
    else:
        available_quantity = item.product_variant.stock_quantity if item.product_variant else item.product.stock_quantity
        if (item.product_variant or item.product.track_inventory) and quantity > available_quantity:
            messages.error(request, 'The requested quantity is not currently available.')
        else:
            item.quantity = quantity
            item.save(update_fields=['quantity'])
    return redirect('shop:cart')

@require_POST
@transaction.atomic
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart = get_cart(request, create=False)
    cart = get_object_or_404(Cart.objects.select_for_update(), pk=cart.pk if cart else None)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    return redirect('shop:cart')

@never_cache
def checkout(request):
    """Review and submit an idempotent, stock-checked order."""
    cart = get_cart(request, create=False)
    if not cart:
        return redirect('shop:cart')
    items = list(cart_items(cart))
    if not items and request.method != 'POST':
        return redirect('shop:cart')
    initial = {'email': request.user.email} if request.user.is_authenticated else {}
    address = request.user.addresses.filter(is_default_shipping=True).first() if request.user.is_authenticated else None
    if address:
        initial.update({
            'phone': address.phone, 'shipping_name': address.full_name,
            'shipping_address_line_1': address.address_line_1,
            'shipping_address_line_2': address.address_line_2, 'shipping_city': address.city,
            'shipping_state': address.state, 'shipping_postal_code': address.postal_code,
        })
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(cart, request.user, request.POST.get('checkout_token'), form.cleaned_data)
            except CheckoutError as error:
                form.add_error(None, str(error))
            except OperationalError:
                form.add_error(None, 'Checkout is busy. Please retry in a moment; do not change your cart.')
                return render(request, 'checkout_new.html', {'form': form, 'cart_items': items,
                    'checkout_token': request.POST.get('checkout_token', ''), **cart_totals(items)}, status=503)
            else:
                return redirect('shop:order_confirmation', order_id=order.pk)
    else:
        form = CheckoutForm(initial=initial)
    items = list(cart_items(cart))
    return render(request, 'checkout_new.html', {'form': form, 'cart_items': items,
        'checkout_token': review_token(cart, items), **cart_totals(items)})


def order_confirmation(request, order_id):
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user)
    else:
        cart = get_cart(request, create=False)
        orders = Order.objects.filter(user__isnull=True, checkout_cart=cart) if cart else Order.objects.none()
    order = get_object_or_404(orders, pk=order_id)
    response = render(request, 'order_success.html', {'order': order})
    response['Cache-Control'] = 'private, no-store'
    return response

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

def register_view(request):
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('shop:profile')
    return render(request, 'register.html', {'form': form})

@login_required
def profile_view(request):
    return render(request, 'profile.html', {'orders': request.user.orders.prefetch_related('items')[:10]})

@login_required
def addresses_view(request):
    form = AddressForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        if address.is_default_shipping:
            request.user.addresses.update(is_default_shipping=False)
        address.save()
        messages.success(request, 'Address saved.')
        return redirect('shop:addresses')
    return render(request, 'addresses.html', {'form': form, 'addresses': request.user.addresses.all()})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(request.user.orders.prefetch_related('items'), id=order_id)
    return render(request, 'order_detail.html', {'order': order})

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

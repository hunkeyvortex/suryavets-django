from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
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

def cart_detail(request):
    """Display the current cart for an anonymous or authenticated shopper."""
    cart = get_cart(request)
    items = cart_items(cart)
    context = {'cart': cart, 'cart_items': items, **cart_totals(items)}
    return render(request, 'cart_new.html', context)

def add_to_cart(request, product_id):
    """Add a product to a session cart, respecting variant and stock choices."""
    if request.method != 'POST':
        return redirect('shop:product_detail', product_slug='')
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except (TypeError, ValueError):
        quantity = 1
    product = get_object_or_404(Product, id=product_id, is_active=True)
    variant_id = request.POST.get('variant_id')
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product, is_active=True)
    elif product.variants.filter(is_active=True).exists():
        variant = product.variants.filter(is_active=True, stock_quantity__gt=0).first()

    available_quantity = variant.stock_quantity if variant else product.stock_quantity
    if (variant or product.track_inventory) and available_quantity < quantity:
        messages.error(request, 'The requested quantity is not currently available.')
        return redirect(request.POST.get('next') or 'shop:cart')

    cart = get_cart(request)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, product_variant=variant, defaults={'quantity': quantity}
    )
    if not created:
        desired_quantity = item.quantity + quantity
        if (variant or product.track_inventory) and desired_quantity > available_quantity:
            messages.error(request, 'There is not enough stock to add more of this item.')
            return redirect(request.POST.get('next') or 'shop:cart')
        item.quantity = desired_quantity
        item.save(update_fields=['quantity'])
    messages.success(request, f'{product.name} was added to your cart.')
    return redirect(request.POST.get('next') or 'shop:cart')

def update_cart_item(request, item_id):
    """Change a cart quantity through a normal CSRF-protected form post."""
    if request.method != 'POST':
        return redirect('shop:cart')
    item = get_object_or_404(CartItem, id=item_id, cart=get_cart(request))
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
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

def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart=get_cart(request))
    cart_item.delete()
    return redirect('shop:cart')

def checkout(request):
    """Create a pending order from an anonymous or authenticated shopper's cart."""
    cart = get_cart(request)
    items = cart_items(cart)
    if not items:
        return redirect('shop:cart')

    totals = cart_totals(items)
    initial = {'email': request.user.email} if request.user.is_authenticated else {}
    address = request.user.addresses.filter(is_default_shipping=True).first() if request.user.is_authenticated else None
    if address:
        initial.update({
            'phone': address.phone, 'shipping_name': address.full_name,
            'shipping_address_line_1': address.address_line_1,
            'shipping_address_line_2': address.address_line_2,
            'shipping_city': address.city, 'shipping_state': address.state,
            'shipping_postal_code': address.postal_code,
        })
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            checkout_data = form.cleaned_data.copy()
            if checkout_data['billing_same_as_shipping']:
                checkout_data.update({
                    'billing_name': checkout_data['shipping_name'],
                    'billing_address_line_1': checkout_data['shipping_address_line_1'],
                    'billing_address_line_2': checkout_data['shipping_address_line_2'],
                    'billing_city': checkout_data['shipping_city'],
                    'billing_state': checkout_data['shipping_state'],
                    'billing_postal_code': checkout_data['shipping_postal_code'],
                })
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    payment_method=checkout_data['payment_method'],
                    subtotal=totals['subtotal'], shipping_cost=totals['shipping'], total=totals['total'],
                    **{key: checkout_data[key] for key in (
                        'email', 'phone', 'shipping_name', 'shipping_address_line_1',
                        'shipping_address_line_2', 'shipping_city', 'shipping_state',
                        'shipping_postal_code', 'billing_same_as_shipping', 'billing_name',
                        'billing_address_line_1', 'billing_address_line_2', 'billing_city',
                        'billing_state', 'billing_postal_code', 'notes',
                    )},
                )
                for item in items:
                    unit_price = item.product_variant.current_price if item.product_variant else item.product.current_price
                    OrderItem.objects.create(order=order, product=item.product, product_variant=item.product_variant, product_name=item.product.name, sku=item.product_variant.sku if item.product_variant else item.product.sku, variant_name=item.product_variant.name if item.product_variant else '', unit_price=unit_price, quantity=item.quantity)
                if form.cleaned_data['save_address'] and request.user.is_authenticated:
                    CustomerAddress.objects.update_or_create(user=request.user, is_default_shipping=True, defaults={'label': 'Home', 'full_name': form.cleaned_data['shipping_name'], 'phone': form.cleaned_data['phone'], 'address_line_1': form.cleaned_data['shipping_address_line_1'], 'address_line_2': form.cleaned_data['shipping_address_line_2'], 'city': form.cleaned_data['shipping_city'], 'state': form.cleaned_data['shipping_state'], 'postal_code': form.cleaned_data['shipping_postal_code']})
                cart.items.all().delete()
            return render(request, 'order_success.html', {'order': order})
    else:
        form = CheckoutForm(initial=initial)
    return render(request, 'checkout_new.html', {'form': form, 'cart_items': items, **totals})

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

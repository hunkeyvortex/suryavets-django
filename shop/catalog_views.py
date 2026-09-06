"""Catalogue browsing, search, filtering, and product-detail views."""

from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, render

from .models import Brand, Category, PetCategory, Product, ProductType, ProductVariant, Subcategory


CATALOG_PAGE_SIZE = 12


def _categories_with_counts():
    return Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).prefetch_related('subcategories').order_by('order', 'name')


def _product_queryset():
    return Product.objects.filter(is_active=True).select_related(
        'category', 'subcategory', 'brand', 'product_type'
    ).prefetch_related('images', 'pet_categories', 'variants').order_by('-created_at')


def _valid_decimal(value):
    try:
        return Decimal(value) if value else None
    except (InvalidOperation, TypeError):
        return None


def _apply_catalog_controls(request, products, *, category=None, subcategory=None):
    """Apply safe query-string controls shared by browsing and search."""
    selected_category = request.GET.get('category', '')
    selected_brand = request.GET.get('brand', '')
    selected_product_type = request.GET.get('product_type', '')
    selected_pet = request.GET.get('pet', '')
    availability = request.GET.get('availability', '')
    minimum_price = _valid_decimal(request.GET.get('min_price'))
    maximum_price = _valid_decimal(request.GET.get('max_price'))
    sort = request.GET.get('sort', 'featured')

    if not category and selected_category:
        products = products.filter(category__slug=selected_category)
    if selected_brand:
        products = products.filter(brand__slug=selected_brand)
    if selected_product_type:
        products = products.filter(product_type__slug=selected_product_type)
    if selected_pet:
        products = products.filter(pet_categories__slug=selected_pet)
    if minimum_price is not None:
        products = products.filter(base_price__gte=minimum_price)
    if maximum_price is not None:
        products = products.filter(base_price__lte=maximum_price)
    if availability == 'in_stock':
        products = products.filter(
            Q(track_inventory=False)
            | Q(stock_quantity__gt=0)
            | Q(variants__is_active=True, variants__stock_quantity__gt=0)
        )
    elif availability == 'out_of_stock':
        products = products.exclude(
            Q(track_inventory=False)
            | Q(stock_quantity__gt=0)
            | Q(variants__is_active=True, variants__stock_quantity__gt=0)
        )

    ordering = {
        'newest': ('-created_at',),
        'price_low': ('base_price', 'name'),
        'price_high': ('-base_price', 'name'),
        'name': ('name',),
        'featured': ('-is_featured', '-is_bestseller', '-created_at'),
    }
    return products.order_by(*ordering.get(sort, ordering['featured'])).distinct(), {
        'category': selected_category,
        'brand': selected_brand,
        'product_type': selected_product_type,
        'pet': selected_pet,
        'availability': availability,
        'min_price': request.GET.get('min_price', ''),
        'max_price': request.GET.get('max_price', ''),
        'sort': sort if sort in ordering else 'featured',
    }


def _render_product_list(request, products, *, category=None, subcategory=None, title=None, search_query=''):
    products, selected_filters = _apply_catalog_controls(
        request, products, category=category, subcategory=subcategory
    )
    total_count = products.count()
    paginator = Paginator(products, CATALOG_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    querystring = request.GET.copy()
    querystring.pop('page', None)
    return render(request, 'catalog/product_list.html', {
        'categories': _categories_with_counts(),
        'brands': Brand.objects.filter(is_active=True).order_by('name'),
        'product_types': ProductType.objects.order_by('name'),
        'pet_categories': PetCategory.objects.filter(is_active=True).order_by('order', 'name'),
        'category': category,
        'subcategory': subcategory,
        'products': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_count': total_count,
        'selected_filters': selected_filters,
        'catalog_title': title,
        'search_query': search_query,
        'querystring': querystring.urlencode(),
    })


def product_list(request):
    """Browse every active product."""
    return _render_product_list(request, _product_queryset())


def category_detail(request, category_slug):
    """Browse products assigned to one category."""
    category = get_object_or_404(
        _categories_with_counts(), slug=category_slug
    )
    return _render_product_list(
        request, _product_queryset().filter(category=category), category=category
    )


def subcategory_detail(request, category_slug, subcategory_slug):
    """Browse products assigned to one category and subcategory."""
    category = get_object_or_404(_categories_with_counts(), slug=category_slug)
    subcategory = get_object_or_404(
        Subcategory.objects.filter(is_active=True),
        category=category,
        slug=subcategory_slug,
    )
    return _render_product_list(
        request,
        _product_queryset().filter(subcategory=subcategory),
        category=category,
        subcategory=subcategory,
    )


def product_search(request):
    """Search the catalogue across product and merchandising fields."""
    query = request.GET.get('q', '').strip()
    products = _product_queryset()
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(description__icontains=query)
            | Q(short_description__icontains=query)
            | Q(manufacturer__icontains=query)
            | Q(brand__name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(subcategory__name__icontains=query)
            | Q(product_type__name__icontains=query)
        )
    else:
        products = Product.objects.none()
    return _render_product_list(
        request,
        products,
        title='Search results',
        search_query=query,
    )


def product_detail(request, product_slug):
    """Display a product, its active variants, and related category products."""
    product = get_object_or_404(
        Product.objects.select_related('category', 'subcategory', 'brand', 'product_type')
        .prefetch_related(
            'images', 'pet_categories', 'specifications',
            Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True)),
        ),
        slug=product_slug,
        is_active=True,
    )
    related_products = _product_queryset().filter(
        category=product.category
    ).exclude(pk=product.pk)[:4]
    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'related_products': related_products,
    })

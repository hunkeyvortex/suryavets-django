"""Catalogue browsing, search, filtering, and product-detail views."""

from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Exists, OuterRef
from django.shortcuts import get_object_or_404, render

from .models import Brand, Category, PetCategory, Product, ProductType, ProductVariant, Subcategory
from .services.navigation import descendant_ids
from .services.pricing import catalog_price_expression


CATALOG_PAGE_SIZE = 12


def _categories_with_counts():
    return Category.objects.filter(is_active=True, parent__isnull=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).prefetch_related('subcategories').order_by('order', 'name')


def _product_queryset():
    return Product.objects.filter(is_active=True, variant_family__isnull=True).select_related(
        'category', 'subcategory', 'brand', 'product_type'
    ).prefetch_related('images', 'pet_categories', 'variants', 'family_members__variants', 'family_members__images').order_by('-created_at')


def _valid_decimal(value):
    try:
        amount = Decimal(value) if value else None
        return amount if amount is not None and amount.is_finite() and amount >= 0 else None
    except (InvalidOperation, TypeError):
        return None


def _apply_catalog_controls(request, products, *, category=None, subcategory=None):
    """Apply safe query-string controls shared by browsing and search."""
    products = products.annotate(catalog_price=catalog_price_expression())
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
        products = products.filter(catalog_price__gte=minimum_price)
    if maximum_price is not None:
        products = products.filter(catalog_price__lte=maximum_price)
    if availability in ('in_stock', 'out_of_stock'):
        family_match=Q(product_id=OuterRef('pk')) | Q(product__variant_family_id=OuterRef('pk'))
        products = products.annotate(has_pack=Exists(ProductVariant.objects.filter(family_match)),
            has_stock_pack=Exists(ProductVariant.objects.filter(family_match, product__is_active=True, is_active=True, stock_quantity__gt=0)))
        stock_filter = Q(has_stock_pack=True) | (Q(has_pack=False) & (Q(track_inventory=False) | Q(stock_quantity__gt=0)))
        products = products.filter(stock_filter) if availability == 'in_stock' else products.exclude(stock_filter)

    ordering = {
        'newest': ('-created_at',),
        'price_low': ('catalog_price', 'name'),
        'price_high': ('-catalog_price', 'name'),
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
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    if any(not ancestor.is_active for ancestor in category.get_ancestors()):
        from django.http import Http404
        raise Http404('Category unavailable')
    ids = descendant_ids(category)
    return _render_product_list(
        request, _product_queryset().filter(Q(category_id__in=ids) | Q(collections__id__in=ids)).distinct(), category=category
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
            | Q(family_members__name__icontains=query)
            | Q(family_members__sku__icontains=query)
            | Q(family_members__variants__sku__icontains=query)
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
            'variants', 'family_members__variants', 'family_members__images',
        ),
        slug=product_slug,
        is_active=True,
    )
    related_products = _product_queryset().filter(
        category=product.category
    ).exclude(pk=product.variant_family_id or product.pk)[:4]
    from .services.pack_families import buying_variants, family_products
    requested_product = product
    if product.variant_family_id:
        product = get_object_or_404(_product_queryset(), pk=product.variant_family_id)
    members = family_products(product)
    family_photos = [photo for member in members for photo in member.images.all()]
    product._prefetched_objects_cache['images'] = family_photos
    variants = sorted(buying_variants(product), key=lambda v:(v.display_order,v.name,v.pk))
    from .services.variants import variant_options
    options = variant_options(product, variants)
    selected_variant = next((variant for variant in variants if variant.is_in_stock), variants[0] if variants else None)
    if requested_product.pk != product.pk:
        selected_variant = next((v for v in variants if v.product_id == requested_product.pk and v.is_in_stock), selected_variant)
    priced_item = selected_variant or product
    saving = max(Decimal(0), priced_item.original_price - priced_item.current_price)
    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'selected_variant': selected_variant,
        'buying_in_stock': any(v.is_in_stock for v in variants) if variants else product.is_in_stock,
        'variant_options': options,
        'selected_option': next((o for o in options if o['variant'] == selected_variant), {'saving': saving, 'discount': int(saving * 100 / priced_item.original_price) if priced_item.original_price > 0 else 0, 'unit_price': None}),
        'display_price': priced_item.current_price,
        'display_regular_price': priced_item.original_price,
        'related_products': related_products,
    })

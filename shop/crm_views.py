"""Private CRM pages; use the same database as the storefront without duplicating customers."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView, redirect_to_login
from django.core import signing
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Count, F, Max, Q, Sum
from django.db.models.functions import Lower
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .crm_forms import CouponForm, NoteForm, StaffLoginForm, StatusForm, StockAdjustmentForm
from .models import Coupon, CRMActivity, InventoryMovement, Order, Product, ProductVariant, ProductImage
from django.utils import timezone
from django.utils.dateparse import parse_date
from .services.order_tracking import tracker
from .services.crm import CRMError, TRANSITIONS, add_note, adjustment_token, adjust_inventory, require_staff, transition_order


def staff_page(permission='access_crm'):
    def decorator(view):
        @wraps(view)
        @never_cache
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                response = redirect_to_login(request.get_full_path(), reverse('crm:login'))
            else:
                require_staff(request.user, permission)
                response = view(request, *args, **kwargs)
            response['Cache-Control'] = 'private, no-store'
            response['X-Robots-Tag'] = 'noindex, nofollow'
            return response
        return wrapped
    return decorator


class StaffLoginView(LoginView):
    template_name = 'crm/login.html'
    authentication_form = StaffLoginForm
    next_page = reverse_lazy('crm:dashboard')

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response


class StaffLogoutView(LogoutView):
    next_page = reverse_lazy('crm:login')


def page_context(request, queryset):
    query = request.GET.copy()
    query.pop('page', None)
    return {'page': Paginator(queryset, 30).get_page(request.GET.get('page')), 'query': query.urlencode(), 'q': request.GET.get('q', '')[:150]}


def customer_groups():
    return Order.objects.exclude(email='').annotate(contact=Lower('email')).values('contact').annotate(
        order_count=Count('pk'), last_order=Max('created_at')).order_by('-last_order')


@staff_page()
def dashboard(request):
    return render(request, 'crm/dashboard.html', {
        'section': 'dashboard', 'title': 'Overview',
        'new_orders': Order.objects.filter(status='pending').count(),
        'to_pack': Order.objects.filter(status__in=['confirmed', 'processing']).count(),
        'shipped_orders': Order.objects.filter(status__in=['shipped', 'out_for_delivery']).count(),
        'delivered_today': Order.objects.filter(events__kind='order', events__status='delivered', events__timestamp__date=timezone.localdate()).distinct().count(),
        'open_orders': Order.objects.filter(status__in=['pending', 'processing']).count(),
        'paid_total': Order.objects.filter(payment_status='paid').aggregate(total=Sum('total'))['total'] or 0,
        'product_count': Product.objects.filter(is_active=True).count(),
        'customer_count': customer_groups().count(),
        'orders': Order.objects.all()[:8], 'activity': CRMActivity.objects.select_related('actor', 'order')[:8],
    })


@staff_page()
def orders(request):
    qs = Order.objects.prefetch_related('items')
    q = request.GET.get('q', '').strip()[:150]
    if q:
        qs = qs.filter(Q(order_number__icontains=q) | Q(email__icontains=q) | Q(shipping_name__icontains=q) | Q(phone__icontains=q))
    status, payment = request.GET.get('status', ''), request.GET.get('payment', '')
    if status in Order.Status.values:
        qs = qs.filter(status=status)
    elif status == 'to_pack': qs = qs.filter(status__in=['confirmed', 'processing'])
    elif status == 'in_transit': qs = qs.filter(status__in=['shipped', 'out_for_delivery'])
    elif status == 'returns': qs = qs.exclude(return_status='')
    elif status == 'delivered_today': qs = qs.filter(events__kind='order', events__status='delivered', events__timestamp__date=timezone.localdate()).distinct()
    for param, lookup in [('from', 'created_at__date__gte'), ('to', 'created_at__date__lte')]:
        try: value = parse_date(request.GET.get(param, ''))
        except ValueError: value = None
        if value: qs = qs.filter(**{lookup: value})
    if payment in Order.PaymentStatus.values:
        qs = qs.filter(payment_status=payment)
    return render(request, 'crm/orders.html', {**page_context(request, qs), 'section': 'orders', 'title': 'Orders',
        'status': status, 'payment': payment, 'statuses': Order.Status.choices, 'payments': Order.PaymentStatus.choices})


@staff_page()
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=pk)
    status_form = StatusForm(initial={'expected': order.status})
    status_form.fields['status'].choices = [(s, Order.Status(s).label) for s in TRANSITIONS.get(order.status, ())]
    return render(request, 'crm/order_detail.html', {'section': 'orders', 'title': order.order_number, 'order': order,
        'status_form': status_form, 'can_transition': bool(status_form.fields['status'].choices), 'note_form': NoteForm(),
        'events': order.events.select_related('changed_by'), 'stages': tracker(order),
        'activity': order.crm_activity.select_related('actor'), 'movements': order.stock_movements.select_related('product', 'variant', 'actor'),
        'customer_key': signing.dumps(order.email.lower(), salt='surya.crm.customer')})


@staff_page('manage_crm_orders')
@require_POST
def order_status(request, pk):
    get_object_or_404(Order, pk=pk)
    form = StatusForm(request.POST)
    form.fields['status'].choices = Order.Status.choices
    if form.is_valid():
        try:
            transition_order(request.user, pk, **form.cleaned_data)
            messages.success(request, 'Order status saved. Payment status was not changed.')
        except (CRMError, OperationalError) as exc:
            messages.error(request, str(exc) if isinstance(exc, CRMError) else 'The record is busy. Reload and review before retrying.')
    else:
        messages.error(request, 'Choose a valid status and enter a reason of 3–500 characters.')
    return redirect('crm:order_detail', pk=pk)


@staff_page('write_crm_notes')
@require_POST
def order_note(request, pk):
    order = get_object_or_404(Order, pk=pk)
    form = NoteForm(request.POST)
    if form.is_valid():
        add_note(request.user, form.cleaned_data['text'], order=order)
        messages.success(request, 'Internal note added.')
    else:
        messages.error(request, 'Write a note of 3–2,000 characters.')
    return redirect('crm:order_detail', pk=pk)


@staff_page()
def customers(request):
    qs = customer_groups()
    q = request.GET.get('q', '').strip()[:150]
    if q:
        # Filter contacts, not their orders, so displayed counts remain complete.
        matching = Order.objects.filter(Q(email__icontains=q) | Q(shipping_name__icontains=q) | Q(phone__icontains=q)).annotate(e=Lower('email')).values('e')
        qs = qs.filter(contact__in=matching)
    context = page_context(request, qs)
    for contact in context['page']:
        contact['key'] = signing.dumps(contact['contact'], salt='surya.crm.customer')
    return render(request, 'crm/customers.html', {**context, 'section': 'customers', 'title': 'Customers'})


def customer_email(key):
    try:
        email = signing.loads(key, salt='surya.crm.customer')
        if not isinstance(email, str) or not Order.objects.filter(email__iexact=email).exists():
            raise Http404
        return email
    except signing.BadSignature:
        raise Http404


@staff_page()
def customer_detail(request, key):
    email = customer_email(key)
    orders = Order.objects.filter(email__iexact=email)
    return render(request, 'crm/customer_detail.html', {**page_context(request, orders), 'section': 'customers', 'title': 'Customer contact',
        'email': email, 'key': key, 'latest': orders.first(), 'note_form': NoteForm(),
        'paid_total': orders.filter(payment_status='paid').aggregate(total=Sum('total'))['total'] or 0,
        'activity': CRMActivity.objects.filter(customer_email=email).select_related('actor')})


@staff_page('write_crm_notes')
@require_POST
def customer_note(request, key):
    email = customer_email(key)
    form = NoteForm(request.POST)
    if form.is_valid():
        add_note(request.user, form.cleaned_data['text'], email=email)
        messages.success(request, 'Internal contact note added.')
    else:
        messages.error(request, 'Write a note of 3–2,000 characters.')
    return redirect('crm:customer_detail', key=key)


@staff_page()
def inventory(request):
    qs = Product.objects.select_related('brand', 'category').prefetch_related('images').order_by('name', 'pk')
    review_filter = request.GET.get('review', '')
    safety_filter = request.GET.get('safety', '')
    identity_filter = request.GET.get('identity', '')
    from .services.pack_review_snapshot import snapshot
    identity = snapshot() if identity_filter else {'generated_at': '', 'by_product': {}}
    if identity_filter:
        ids = [pk for pk, rows in identity['by_product'].items() if identity_filter == 'review' or any(r['Priority'] == identity_filter for r in rows)]
        qs = qs.filter(pk__in=ids)
    from .services.purchasing import effective_price
    from .services.pricing import catalog_price_expression
    from django.db.models import Exists, OuterRef
    if safety_filter == 'zero':
        zero = ProductVariant.objects.filter(product_id=OuterRef('pk')).alias(value=effective_price(variant=True)).filter(value__lte=0)
        qs = qs.alias(zero_pack=Exists(zero), simple_price=effective_price()).filter(Q(zero_pack=True) | Q(variants__isnull=True, simple_price__lte=0))
    elif safety_filter == 'blocked':
        qs = qs.alias(purchasable_price=catalog_price_expression()).filter(purchasable_price__isnull=True)
    if review_filter == 'pending':
        qs = qs.filter(catalog_approved_digest='')
    elif review_filter == 'recorded':
        qs = qs.exclude(catalog_approved_digest='')
    visibility = request.GET.get('visibility', '')
    media_filter = request.GET.get('media', '')
    if media_filter in ('placeholder', 'review', 'recovered'):
        from .services.image_coverage_snapshot import matching_products
        qs = qs.filter(pk__in=matching_products(media_filter))
    if media_filter == 'missing':
        qs = qs.exclude(pk__in=ProductImage.objects.filter(Q(image__gt='') | Q(source_url__gt='')).values('product_id'))
    elif media_filter == 'broken':
        qs = qs.filter(images__check_error__gt='').distinct()
    elif media_filter == 'nutrition':
        qs = qs.filter(nutrition_reviewed=False).exclude(ingredients='', nutrition_information='')
    elif media_filter == 'variant':
        qs = qs.filter(variants__is_active=True, variants__image__isnull=True).distinct()
    if visibility in ('active', 'archived'):
        qs = qs.filter(is_active=visibility == 'active')
    q = request.GET.get('q', '').strip()[:150]
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(variants__sku__icontains=q) | Q(brand__name__icontains=q)).distinct()
    stock = request.GET.get('stock', '')
    if stock == 'low':
        qs = qs.filter(Q(variants__is_active=True, variants__stock_quantity__lte=F('variants__low_stock_threshold')) |
                       Q(variants__isnull=True, track_inventory=True, stock_quantity__lte=10)).distinct()
    elif stock == 'out':
        qs = qs.filter(Q(variants__is_active=True, variants__stock_quantity=0) |
                       Q(variants__isnull=True, track_inventory=True, stock_quantity=0)).distinct()
    stats = Product.objects.aggregate(total=Count('pk'), active=Count('pk', filter=Q(is_active=True)),
        archived=Count('pk', filter=Q(is_active=False)))
    context = page_context(request, qs)
    for product in context['page']:
        product.identity_review = identity['by_product'].get(str(product.pk), [])
    return render(request, 'crm/catalog_inventory.html', {**context, 'section': 'inventory',
        'identity_filter': identity_filter, 'identity_generated_at': identity['generated_at'],
        'title': 'Products & inventory', 'stock': stock, 'visibility': visibility, 'stats': stats, 'media_filter': media_filter, 'review_filter': review_filter, 'safety_filter': safety_filter})


@staff_page()
def inventory_detail(request, pk, variant_id=None):
    product = get_object_or_404(Product, pk=pk)
    variant = get_object_or_404(ProductVariant, pk=variant_id, product=product) if variant_id else None
    variants = product.variants.all().order_by('name')
    adjustable = bool(variant or (product.track_inventory and not variants.exists()))
    form = StockAdjustmentForm(initial={'token': adjustment_token(request.user, product, variant)})
    if request.method == 'POST':
        require_staff(request.user, 'adjust_crm_inventory')
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                adjust_inventory(request.user, product.pk, variant.pk if variant else None, **form.cleaned_data)
                messages.success(request, 'Stock adjustment saved with an audit record.')
                return redirect(request.path)
            except (CRMError, OperationalError) as exc:
                form.add_error(None, str(exc) if isinstance(exc, CRMError) else 'Stock is busy. Reload and review before retrying.')
    movements = product.stock_movements.select_related('actor', 'variant', 'order')
    if variant:
        movements = movements.filter(variant=variant)
    return render(request, 'crm/inventory_detail.html', {**page_context(request, movements), 'section': 'inventory', 'title': product.name,
        'product': product, 'variant': variant, 'variants': variants, 'target': variant or product, 'form': form, 'adjustable': adjustable})


@staff_page()
def reports(request):
    return render(request, 'crm/reports.html', {'section': 'reports', 'title': 'Reports',
        'payment_totals': Order.objects.order_by().values('payment_status').annotate(count=Count('pk'), amount=Sum('total')).order_by('payment_status'),
        'status_totals': Order.objects.order_by().values('status').annotate(count=Count('pk')).order_by('status'),
        'movements': InventoryMovement.objects.select_related('actor', 'product', 'variant', 'order')[:50]})


@staff_page()
def coupons(request):
    qs = Coupon.objects.all()
    q = request.GET.get('q', '').strip()[:120]
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
    return render(request, 'crm/coupons.html', {**page_context(request, qs), 'title': 'Coupons', 'section': 'coupons', 'now': timezone.now()})


@staff_page('manage_crm_coupons')
def coupon_edit(request, pk=None):
    instance = get_object_or_404(Coupon, pk=pk) if pk else Coupon()
    form = CouponForm(instance=instance)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                instance = get_object_or_404(Coupon.objects.select_for_update(), pk=pk) if pk else Coupon()
                form = CouponForm(request.POST, instance=instance)
                if form.is_valid():
                    changes = ', '.join(name for name in form.changed_data if name != 'version')
                    coupon = form.save()
                    CRMActivity.objects.create(actor=request.user, coupon=coupon, kind='coupon',
                        text=f'{"Updated" if pk else "Created"} coupon {coupon.code}. Fields: {changes or "no rule changes"}.')
                    messages.success(request, 'Coupon saved. Previous orders keep their original discount.')
                    return redirect('crm:coupon_edit', pk=coupon.pk)
        except (IntegrityError, OperationalError):
            form.add_error(None, 'This code already exists or the record is busy. Reload and review before retrying.')
    return render(request, 'crm/coupon_edit.html', {'title': 'Edit coupon' if pk else 'Create coupon', 'section': 'coupons',
        'form': form, 'coupon': instance if pk else None, 'timezone_name': timezone.get_current_timezone_name(),
        'activity': instance.activity.select_related('actor')[:30] if pk else []})

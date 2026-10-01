from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from .crm_views import staff_page
from .models import Product, CRMActivity
from .catalog_views import _product_queryset
from .services.merchandising import eligibility
from .services.pack_review_snapshot import snapshot
from .services.crm import require_staff


FLAGS = {'best': 'is_bestseller', 'featured': 'is_featured', 'new': 'is_new_arrival', 'promo': 'is_promotional'}


class SelectionForm(forms.Form):
    products = forms.ModelMultipleChoiceField(queryset=Product.objects.filter(variant_family__isnull=True))
    merchandising_active = forms.BooleanField(required=False, label='Curated for homepage')
    is_bestseller = forms.BooleanField(required=False, label='Best Seller')
    is_featured = forms.BooleanField(required=False, label='Featured')
    is_new_arrival = forms.BooleanField(required=False, label='New Arrival')
    is_promotional = forms.BooleanField(required=False, label='Promotional')
    merchandising_rank = forms.IntegerField(min_value=0, max_value=1000000, initial=100, label='Rank (lower first)')


@staff_page('view_product')
def index(request):
    form = SelectionForm(request.POST or None)
    if request.method == 'POST':
        require_staff(request.user, 'change_product')
        if form.is_valid():
            ids = list(form.cleaned_data['products'].values_list('pk', flat=True))
            if len(ids) > 50:
                form.add_error('products', 'Select at most 50 families per update.')
            else:
                fields = {k: v for k, v in form.cleaned_data.items() if k != 'products'}
                with transaction.atomic():
                    for product in Product.objects.select_for_update().filter(pk__in=ids):
                        before = {field: getattr(product, field) for field in fields}
                        Product.objects.filter(pk=product.pk).update(**fields)
                        CRMActivity.objects.create(actor=request.user, kind='note', text=f'Merchandising {product.pk}: {before} -> {fields}')
                messages.success(request, f'Updated manual merchandising for {len(ids)} families. Purchase safety still applies.')
                return redirect('crm:merchandising')
    products = _product_queryset()
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    mode = request.GET.get('filter', '')
    if mode in FLAGS:
        products = products.filter(merchandising_active=True, **{FLAGS[mode]: True})
    evidence = snapshot()
    if mode in ('eligible', 'missing', 'blocked'):
        if products.count() > 200:
            messages.info(request, 'For live safety/image filters, narrow the name or SKU search to 200 families or fewer. This avoids scanning the whole catalog on every page load.')
            products = products.none()
        ids = []
        for start in range(0, products.count(), 100):
            for product in products[start:start + 100]:
                reason = eligibility(product, evidence)
                if (mode == 'eligible' and not reason or mode == 'missing' and reason == 'Missing exact-pack image'
                        or mode == 'blocked' and reason == 'Blocked from purchase'):
                    ids.append(product.pk)
        products = products.filter(pk__in=ids)
    page = Paginator(products.order_by('merchandising_rank', 'name', 'pk'), 30).get_page(request.GET.get('page'))
    for product in page:
        product.merchandising_reason = eligibility(product, evidence)
    return render(request, 'crm/merchandising.html', {'title': 'Homepage merchandising', 'section': 'inventory',
        'page': page, 'form': form, 'query': query, 'mode': mode})

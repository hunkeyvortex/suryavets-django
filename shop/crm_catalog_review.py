from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .models import Product
from .crm_views import staff_page
from .services.catalog_approval import status, issues, review_token, decide


class ReviewForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput)
    decision = forms.ChoiceField(choices=[('held', 'Hold — block purchases pending review'), ('approved', 'Approve review')])
    evidence = forms.CharField(min_length=15, max_length=2000, widget=forms.Textarea(attrs={'rows': 3}),
        label='Source / stock-count reference and review notes',
        help_text='Record supplier/export reference, stock-count time and location. No customer data or secrets.')
    identity = forms.BooleanField(required=False, label='I verified every exact pack, SKU and matching image.')
    prices = forms.BooleanField(required=False, label='I verified current selling prices and MRP against an approved source.')
    inventory = forms.BooleanField(required=False, label='I verified stock against a dated count, including later order/stock movements.')

    def clean(self):
        data = super().clean()
        if data.get('decision') == 'approved' and not all(data.get(key) for key in ('identity', 'prices', 'inventory')):
            raise ValidationError('Complete all three checks. Do not approve old stock=10 defaults without evidence.')
        return data


@staff_page('approve_catalog')
@require_http_methods(['GET', 'POST'])
def review(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ReviewForm(request.POST if request.method == 'POST' else None,
                      initial={'token': review_token(request.user, product)})
    if request.method == 'POST' and form.is_valid():
        try:
            decide(request.user, product.pk, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        except OperationalError:
            form.add_error(None, 'This record is busy. Reload before trying again.')
        else:
            messages.success(request, 'Review recorded. An explicit hold blocks purchases; approval never overrides price or stock safety. Stock, prices and orders were not changed.')
            return redirect('crm:catalog_review', pk=product.pk)
    from .services.pack_review_snapshot import snapshot
    identity = snapshot()
    return render(request, 'crm/catalog_review.html', {'title': 'Catalog approval', 'section': 'inventory',
        'identity_rows': identity['by_product'].get(str(product.pk), []), 'identity_generated_at': identity['generated_at'],
        'product': product, 'review_status': status(product), 'problems': issues(product), 'form': form,
        'packs': product.variants.all(), 'photos': product.images.all(),
        'events': product.catalog_reviews.select_related('actor')[:20]})

"""Catalog editing shares the storefront database and preserves the stock ledger."""
from django.contrib import messages
from django.db import transaction, IntegrityError, OperationalError
from django.db.models import Min
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.files.base import ContentFile
from uuid import uuid4
from .services.product_media import optimize_image
from .crm_views import staff_page
from .crm_catalog_forms import ProductEditorForm, VariantEditorForm, ArchiveProductForm, ImageEditorForm
from .models import Product, ProductVariant, ProductImage, CRMActivity
from .services.pack_families import family_products


def record_product_activity(user, product, message):
    CRMActivity.objects.create(actor=user, kind='note', text=f'Catalog [{product.pk}] {message}')


@staff_page('change_product')
@require_http_methods(['GET', 'POST'])
def product_edit(request, pk):
    return edit_product(request, pk)


@staff_page('add_product')
@require_http_methods(['GET', 'POST'])
def product_create(request):
    return edit_product(request)


def edit_product(request, pk=None):
    instance = get_object_or_404(Product, pk=pk) if pk else Product()
    form = ProductEditorForm(instance=instance)
    uploaded = []
    if request.method == 'POST':
        try:
            with transaction.atomic():
                instance = get_object_or_404(Product.objects.select_for_update(), pk=pk) if pk else Product()
                form = ProductEditorForm(request.POST, request.FILES, instance=instance)
                if form.is_valid():
                    product = form.save(commit=False)
                    product.discount_percentage = 0  # Exact selling_price is authoritative.
                    product.save()
                    form.save_m2m()
                    if form.cleaned_data.get('image'):
                        first_order = product.images.aggregate(first=Min('order'))['first']
                        photo = ProductImage(product=product, order=(first_order - 1) if first_order is not None else 0,
                            is_primary=True, alt_text=form.cleaned_data.get('image_alt') or product.name)
                        upload = form.cleaned_data['image']; upload.seek(0)
                        full, thumb = optimize_image(upload.read())
                        filename = f'upload-{uuid4().hex}'
                        photo.image.save(filename + '.webp', ContentFile(full), save=False)
                        uploaded.append((photo.image.storage, photo.image.name))
                        photo.thumbnail.save(filename + '-360.webp', ContentFile(thumb), save=False)
                        uploaded.append((photo.thumbnail.storage, photo.thumbnail.name))
                        product.images.update(is_primary=False)
                        photo.save()
                    fields = ', '.join(f for f in form.changed_data if f != 'version')
                    record_product_activity(request.user, product, f'{"Updated" if pk else "Created"} {product.name}. Fields: {fields or "no changes"}.')
                    messages.success(request, 'Product saved. Stock and previous order prices were not changed.' if pk else 'Product created. Use Adjust stock to record its opening quantity before selling.')
                    return redirect('crm:product_edit' if request.user.has_perm('shop.change_product') else 'crm:inventory_detail', pk=product.pk)
        except (IntegrityError, OperationalError):
            for storage, name in uploaded:
                storage.delete(name)  # Only new files created by this failed save.
            form.add_error(None, 'This handle or record changed during saving. Reload and check for duplicates before retrying.')
    return render(request, 'crm/product_editor.html', {'title': 'Edit product' if pk else 'Add a product', 'section': 'inventory',
        'form': form, 'product': instance if pk else None, 'variants': instance.variants.all() if pk else [],
        'photos': ProductImage.all_objects.filter(product=instance) if pk else [],
        'pack_sources': family_products(instance) if pk else [],
        'activity': CRMActivity.objects.filter(text__startswith=f'Catalog [{instance.pk}]').select_related('actor')[:20] if pk else []})


@staff_page('change_product')
@require_http_methods(['GET', 'POST'])
def product_archive(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ArchiveProductForm(initial={'version': product.updated_at.isoformat()})
    if request.method == 'POST':
        try:
            with transaction.atomic():
                product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
                form = ArchiveProductForm(request.POST)
                if form.is_valid():
                    if form.cleaned_data['version'] != product.updated_at.isoformat():
                        form.add_error(None, 'This product changed. Reload and review its current status before continuing.')
                    else:
                        product.is_active = not product.is_active
                        product.save(update_fields=['is_active', 'updated_at'])
                        action = 'Restored' if product.is_active else 'Archived'
                        record_product_activity(request.user, product, f'{action} {product.name}. Reason: {form.cleaned_data["reason"]}')
                        messages.success(request, f'{action} product. Order history and stock records are preserved.')
                        return redirect('crm:inventory')
        except OperationalError:
            form.add_error(None, 'This product is busy. Reload and try again.')
    return render(request, 'crm/product_archive.html', {'title': 'Archive product' if product.is_active else 'Restore product',
        'section': 'inventory', 'product': product, 'form': form})


@staff_page('change_product')
@require_http_methods(['GET', 'POST'])
def variant_edit(request, pk, variant_id=None):
    product = get_object_or_404(Product, pk=pk)
    variant = get_object_or_404(ProductVariant, pk=variant_id, product=product) if variant_id else ProductVariant(product=product)
    form = VariantEditorForm(instance=variant)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
                variant = get_object_or_404(ProductVariant.objects.select_for_update(), pk=variant_id, product=product) if variant_id else ProductVariant(product=product)
                form = VariantEditorForm(request.POST, instance=variant)
                if form.is_valid():
                    if not variant_id and not product.variants.exists() and product.stock_quantity:
                        form.add_error(None, 'Reconcile existing base-product stock to zero through Adjust stock before creating its first pack. No stock is transferred automatically.')
                        return render(request, 'crm/variant_editor.html', {'title': 'Add pack', 'section': 'inventory', 'product': product, 'variant': variant, 'form': form})
                    variant = form.save(commit=False)
                    variant.discount_percentage = 0
                    variant.save()
                    Product.objects.filter(pk=product.pk).update(updated_at=timezone.now())
                    record_product_activity(request.user, product, f'Edited pack {variant.pk} ({variant.name}). Fields: {", ".join(f for f in form.changed_data if f != "version")}.')
                    messages.success(request, 'Pack details saved. Stock and past orders are unchanged.')
                    return redirect('crm:product_edit', pk=product.pk)
        except (IntegrityError, OperationalError):
            form.add_error(None, 'A pack with this name already exists or the record is busy. Reload and review.')
    return render(request, 'crm/variant_editor.html', {'title': 'Edit pack' if variant_id else 'Add pack', 'section': 'inventory', 'product': product, 'variant': variant, 'form': form})


@staff_page('change_product')
@require_http_methods(['GET', 'POST'])
def image_edit(request, pk, image_id):
    product = get_object_or_404(Product, pk=pk)
    photo = get_object_or_404(ProductImage.all_objects, pk=image_id, product=product)
    form = ImageEditorForm(instance=photo)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
                photo = get_object_or_404(ProductImage.all_objects.select_for_update(), pk=image_id, product=product)
                photo.product = product
                form = ImageEditorForm(request.POST, instance=photo)
                if form.is_valid():
                    photo = form.save(commit=False)
                    if photo.is_primary and photo.is_active:
                        ProductImage.all_objects.filter(product=product).exclude(pk=photo.pk).update(is_primary=False)
                        first = product.images.exclude(pk=photo.pk).aggregate(first=Min('order'))['first']
                        photo.order = min(photo.order, first - 1) if first is not None else photo.order
                    photo.save()
                    if not photo.is_active:
                        ProductVariant.objects.filter(product=product, image=photo).update(image=None, updated_at=timezone.now())
                    Product.objects.filter(pk=product.pk).update(updated_at=timezone.now())
                    record_product_activity(request.user, product, f'Updated photo {photo.pk}; visible={photo.is_active}; order={photo.order}. {form.cleaned_data.get("reason", "")}')
                    messages.success(request, 'Photo updated. Removed photos remain available to restore here; files were not deleted.')
                    return redirect('crm:product_edit', pk=product.pk)
        except (IntegrityError, OperationalError):
            form.add_error(None, 'This image is busy. Reload before retrying.')
    return render(request, 'crm/image_editor.html', {'title': 'Manage product photo', 'section': 'inventory', 'product': product, 'photo': photo, 'form': form})

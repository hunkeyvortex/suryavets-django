"""Explicit catalog fields: never accept stock or ownership fields from a product edit."""
from django import forms
from django.utils.text import slugify
from .models import Product, ProductVariant, ProductImage


class ProductEditorForm(forms.ModelForm):
    version = forms.CharField(required=False, widget=forms.HiddenInput)
    image = forms.ImageField(required=False, label='Add a product photo',
        widget=forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}))
    image_alt = forms.CharField(required=False, max_length=200, label='Photo description')

    class Meta:
        model = Product
        fields = ['name', 'slug', 'sku', 'brand', 'category', 'collections', 'pet_categories',
                  'short_description', 'description', 'base_price', 'selling_price',
                  'ingredients', 'nutrition_information', 'nutrition_source', 'nutrition_source_note', 'nutrition_reviewed',
                  'is_featured', 'is_bestseller', 'requires_prescription', 'meta_title', 'meta_description']
        labels = {'base_price': 'Regular price (₹)', 'selling_price': 'Selling price (₹)', 'slug': 'URL handle',
                  'category': 'Primary category', 'collections': 'Additional collections'}
        widgets = {name: forms.Textarea(attrs={'rows': 3}) for name in ['short_description', 'description', 'meta_description', 'ingredients', 'nutrition_information']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['selling_price'].required = True
        self.fields['selling_price'].help_text = 'Enter the exact price customers pay. For products with packs, edit each pack price below.'
        self.fields['collections'].help_text = 'Optional. Hold Ctrl (Windows) or Command (Mac) to select multiple collections.'
        self.fields['image'].help_text = 'JPEG, PNG or WebP, up to 5 MB and 20 megapixels. Adds a new main image; existing photos are kept.'
        if not self.instance._state.adding:
            self.fields['slug'].disabled = True
            self.fields['slug'].help_text = 'Existing URLs are preserved for SEO.'
            self.fields['version'].initial = self.instance.updated_at.isoformat()
            self.fields['selling_price'].initial = self.instance.current_price
        self.groups = [('Product details', [self[name] for name in ['name', 'slug', 'sku', 'brand']]),
                       ('Pricing', [self[name] for name in ['base_price', 'selling_price']]),
                       ('Where it belongs', [self[name] for name in ['category', 'collections', 'pet_categories']]),
                       ('Tell its story', [self[name] for name in ['short_description', 'description']]),
                       ('Product photo', [self[name] for name in ['image', 'image_alt']]),
                       ('Ingredients & nutrition review', [self[name] for name in ['ingredients', 'nutrition_information', 'nutrition_source', 'nutrition_source_note', 'nutrition_reviewed']]),
                       ('Merchandising & SEO', [self[name] for name in ['is_featured', 'is_bestseller', 'requires_prescription', 'meta_title', 'meta_description']])]

    def clean_slug(self):
        value = self.cleaned_data['slug'] or slugify(self.cleaned_data.get('name', ''))
        if not value:
            raise forms.ValidationError('Enter a URL handle using letters, numbers or hyphens.')
        return value

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and (image.size > 5 * 1024 * 1024 or image.image.width * image.image.height > 20000000
                      or image.image.format not in {'JPEG', 'PNG', 'WEBP'}):
            raise forms.ValidationError('Use a JPEG, PNG or WebP up to 5 MB and 20 megapixels.')
        return image

    def clean(self):
        data = super().clean()
        if data.get('nutrition_reviewed') and (not data.get('nutrition_source') or not (data.get('ingredients') or data.get('nutrition_information'))):
            self.add_error('nutrition_reviewed', 'Provide product-specific information and its source URL before approving it for display.')
        if not self.instance._state.adding and data.get('version') != self.instance.updated_at.isoformat():
            raise forms.ValidationError('This product changed since you opened it. Reload before saving.')
        if data.get('base_price') is not None and data.get('selling_price') is not None and data['selling_price'] > data['base_price']:
            self.add_error('selling_price', 'Selling price cannot exceed the regular price.')
        sku = data.get('sku')
        if sku and (self.instance._state.adding or 'sku' in self.changed_data):
            if Product.objects.exclude(pk=self.instance.pk).filter(sku__iexact=sku).exists() or ProductVariant.objects.exclude(product_id=self.instance.pk).filter(sku__iexact=sku).exists():
                self.add_error('sku', 'This SKU is already used by another product or pack.')
        return data


class VariantEditorForm(forms.ModelForm):
    version = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = ProductVariant
        fields = ['name', 'sku', 'price_override', 'selling_price', 'weight_info', 'quantity', 'unit',
                  'comparison_group', 'attributes', 'display_order', 'image', 'is_active']
        labels = {'price_override': 'Regular pack price (₹)', 'selling_price': 'Selling pack price (₹)', 'weight_info': 'Pack size / weight'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['version'].initial = self.version_value()
        self.fields['image'].queryset = ProductImage.objects.filter(product_id=self.instance.product_id)
        self.fields['display_order'].required = False
        self.fields['attributes'].widget = forms.Textarea(attrs={'rows': 2})
        self.fields['price_override'].required = True
        self.fields['price_override'].initial = self.instance.original_price
        self.fields['selling_price'].required = True
        self.fields['selling_price'].initial = self.instance.current_price

    def clean(self):
        data = super().clean()
        data['display_order'] = data.get('display_order') or 0
        data['attributes'] = data.get('attributes') or {}
        if data.get('version') != self.version_value():
            raise forms.ValidationError('This pack changed. Reload before saving.')
        regular, sale = data.get('price_override'), data.get('selling_price')
        if regular is not None and regular < 0:
            self.add_error('price_override', 'Price cannot be negative.')
        if regular is not None and sale is not None and sale > regular:
            self.add_error('selling_price', 'Selling price cannot exceed the regular price.')
        if data.get('sku') and 'sku' in self.changed_data and (
            ProductVariant.objects.exclude(pk=self.instance.pk).filter(sku__iexact=data['sku']).exists()
            or Product.objects.exclude(pk=self.instance.product_id).filter(sku__iexact=data['sku']).exists()):
            self.add_error('sku', 'This SKU is already in use.')
        return data

    def version_value(self):
        return (self.instance.product.updated_at if self.instance._state.adding else self.instance.updated_at).isoformat()


class ImageEditorForm(forms.ModelForm):
    version = forms.CharField(widget=forms.HiddenInput)
    reason = forms.CharField(required=False, max_length=500, help_text='Required when removing a photo from the storefront. The file remains recoverable.')

    class Meta:
        model = ProductImage
        fields = ['alt_text', 'order', 'is_primary', 'is_active']
        labels = {'is_active': 'Show photo in storefront', 'order': 'Display order (lowest first)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['version'].initial = self.instance.product.updated_at.isoformat()

    def clean(self):
        data = super().clean()
        if data.get('version') != self.instance.product.updated_at.isoformat():
            raise forms.ValidationError('This product changed. Reload before saving.')
        if not data.get('is_active') and not data.get('reason'):
            self.add_error('reason', 'Explain why this photo should be removed.')
        return data


class ArchiveProductForm(forms.Form):
    version = forms.CharField(widget=forms.HiddenInput)
    reason = forms.CharField(min_length=3, max_length=500, widget=forms.Textarea(attrs={'rows': 3}),
                             help_text='Saved to staff history. No products or order records will be deleted.')

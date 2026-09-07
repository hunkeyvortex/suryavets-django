from django.contrib import admin
from .models import (
    Category, Subcategory, ProductType, Brand, PetCategory, Product, ProductVariant,
    ProductImage, ProductSpecification, Banner, ContactInfo,
    Cart, CartItem, CustomerAddress, Order, OrderItem, CRMActivity, InventoryMovement, Coupon
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'product_count']
    autocomplete_fields = ['parent']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'order', 'is_active', 'product_count']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'product_count']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(PetCategory)
class PetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'product_count']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'source_url', 'alt_text', 'order', 'is_primary']


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1
    fields = ['name', 'value', 'order']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    readonly_fields = ['stock_quantity']
    fields = ['name', 'sku', 'barcode', 'size_code', 'weight_info', 'price_override', 'selling_price', 'discount_percentage',
              'stock_quantity', 'low_stock_threshold', 'quantity', 'unit', 'comparison_group', 'display_order', 'image', 'is_active']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'brand', 'category', 'base_price', 'current_price', 'is_featured', 'is_bestseller', 'is_active']
    list_filter = ['category', 'subcategory', 'product_type', 'brand', 'pet_categories', 'is_featured', 'is_bestseller', 'is_active', 'requires_prescription']
    search_fields = ['name', 'sku', 'description', 'short_description', 'manufacturer', 'brand__name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductSpecificationInline, ProductVariantInline]
    list_editable = ['is_featured', 'is_bestseller', 'is_active']
    readonly_fields = ['current_price', 'original_price', 'is_in_stock', 'availability_label', 'stock_quantity']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'short_description', 'description', 'brand', 'category', 'collections', 'shopify_tags', 'subcategory', 'pet_categories', 'product_type')
        }),
        ('Pricing', {
            'fields': ('base_price', 'selling_price', 'discount_percentage', 'current_price', 'original_price')
        }),
        ('Ingredients and nutrition (verify before publishing)', {
            'fields': ('ingredients', 'nutrition_information', 'nutrition_source', 'nutrition_source_note', 'nutrition_reviewed')
        }),
        ('Product Details', {
            'fields': ('manufacturer', 'stock_quantity', 'track_inventory', 'is_in_stock', 'availability_label', 'requires_prescription', 'is_featured', 'is_bestseller', 'is_active')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )

    def current_price(self, obj):
        return f"₹{obj.current_price}"
    current_price.short_description = 'Current Price'

    def original_price(self, obj):
        return f"₹{obj.original_price}"
    original_price.short_description = 'Original Price'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'size_code', 'weight_info', 'current_price', 
                   'stock_quantity', 'is_in_stock', 'is_active']
    list_filter = ['product__category', 'size_code', 'is_active']
    search_fields = ['product__name', 'sku', 'barcode', 'name', 'weight_info']
    list_editable = ['is_active']
    readonly_fields = ['current_price', 'original_price', 'is_in_stock', 'is_low_stock', 'stock_quantity']

    def current_price(self, obj):
        return f"₹{obj.current_price}"
    current_price.short_description = 'Current Price'

    def original_price(self, obj):
        return f"₹{obj.original_price}"
    original_price.short_description = 'Original Price'

    def is_in_stock(self, obj):
        return obj.is_in_stock
    is_in_stock.boolean = True
    is_in_stock.short_description = 'In Stock'

    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True
    is_low_stock.short_description = 'Low Stock'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'alt_text', 'order', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['product__name', 'alt_text']
    list_editable = ['order', 'is_primary']


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'value', 'order']
    search_fields = ['product__name', 'name', 'value']
    list_editable = ['order']


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'subtitle', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'subtitle']
    list_editable = ['order', 'is_active']


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ['phone', 'email', 'city', 'state', 'country']


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'product_variant', 'quantity', 'total_price', 'added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_items', 'total_price', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'total_items', 'total_price', 'created_at', 'updated_at']
    inlines = [CartItemInline]

    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Total Items'

    def total_price(self, obj):
        return f"₹{obj.total_price}"
    total_price.short_description = 'Total Price'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'product_variant', 'quantity', 'total_price', 'added_at']
    list_filter = ['added_at']
    search_fields = ['cart__user__username', 'product__name', 'product_variant__name']
    readonly_fields = ['total_price', 'added_at']

    def total_price(self, obj):
        return f"₹{obj.total_price}"
    total_price.short_description = 'Total Price'


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'label', 'city', 'state', 'is_default_shipping', 'is_default_billing']
    list_filter = ['country', 'state', 'is_default_shipping', 'is_default_billing']
    search_fields = ['full_name', 'phone', 'user__username', 'user__email', 'city', 'postal_code']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_variant', 'product_name', 'sku', 'variant_name', 'unit_price', 'quantity', 'line_total', 'image_reference']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ['order_number', 'email', 'status', 'payment_status', 'total', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'email', 'phone', 'user__username', 'payment_reference']
    readonly_fields = ['id', 'order_number', 'created_at', 'updated_at', 'checkout_key', 'checkout_cart',
                       'stock_deducted', 'inventory_recorded', 'subtotal', 'shipping_cost', 'discount_amount', 'total',
                       'status', 'payment_status', 'payment_method', 'payment_reference', 'coupon', 'coupon_code',
                       'return_status', 'courier', 'tracking_number', 'tracking_url']
    inlines = [OrderItemInline]


class ImmutableAuditAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InventoryMovement)
class InventoryMovementAdmin(ImmutableAuditAdmin):
    list_display = ['created_at', 'product', 'variant', 'kind', 'delta', 'quantity_before', 'quantity_after', 'actor']
    list_filter = ['kind', 'created_at']
    search_fields = ['product__name', 'product__sku', 'variant__sku', 'order__order_number', 'reason']


@admin.register(CRMActivity)
class CRMActivityAdmin(ImmutableAuditAdmin):
    list_display = ['created_at', 'actor', 'order', 'kind']
    list_filter = ['kind', 'created_at']
    search_fields = ['order__order_number', 'customer_email', 'text']


@admin.register(Coupon)
class CouponAdmin(ImmutableAuditAdmin):
    list_display = ['code', 'kind', 'value', 'is_active', 'used_count', 'max_uses', 'ends_at']
    search_fields = ['code', 'name']
    list_filter = ['is_active', 'kind']


from .models import OrderStatusHistory, OrderNotification


@admin.register(OrderStatusHistory)
class OrderEventAdmin(ImmutableAuditAdmin):
    list_display = ['order', 'kind', 'status', 'timestamp', 'changed_by', 'customer_visible']
    list_filter = ['kind', 'status', 'customer_visible']
    search_fields = ['order__order_number']


@admin.register(OrderNotification)
class OrderNotificationAdmin(ImmutableAuditAdmin):
    list_display = ['event', 'channel', 'state', 'sent_at', 'attempts']
    list_filter = ['channel', 'state']

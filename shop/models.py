from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.text import slugify
import uuid
from .services.pricing import selling_price, discount_percent


class Category(models.Model):
    """Main pet categories (Cat, Dog, Farm Animals, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    reference_path = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


    def clean(self):
        super().clean()
        seen = {self.pk} if self.pk else set()
        node = self.parent
        while node:
            if node.pk in seen:
                raise ValidationError({'parent': 'A category cannot contain itself or one of its ancestors.'})
            seen.add(node.pk)
            node = node.parent

    def get_absolute_url(self):
        return reverse('shop:category_detail', args=[self.slug])

    def get_ancestors(self):
        ancestors, seen, node = [], {self.pk}, self.parent
        while node and node.pk not in seen:
            ancestors.append(node)
            seen.add(node.pk)
            node = node.parent
        return list(reversed(ancestors))


class Subcategory(models.Model):
    """Product subcategories (Medicine, Supplements, Food, etc.)"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Subcategories"
        ordering = ['order', 'name']
        unique_together = ['category', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.category.name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class ProductType(models.Model):
    """Product types (Tablet, Syrup, Powder, Kibble, Can, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    """A product manufacturer or retail brand."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='brands/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class PetCategory(models.Model):
    """Animal groups to which a product can apply, such as Cat or Dog."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='pet-categories/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Pet categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Main product model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, blank=True, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    collections = models.ManyToManyField(Category, related_name='collection_products', blank=True)
    shopify_tags = models.JSONField(default=list, blank=True)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name='products', blank=True, null=True)
    product_type = models.ForeignKey(ProductType, on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    pet_categories = models.ManyToManyField(PetCategory, related_name='products', blank=True)
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)], help_text='Exact selling price. Blank uses the legacy percentage calculation.')
    discount_percentage = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    track_inventory = models.BooleanField(default=True)
    
    # Product details
    manufacturer = models.CharField(max_length=100, blank=True)
    requires_prescription = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def current_price(self):
        return selling_price(self.base_price, self.discount_percentage, self.selling_price)

    @property
    def is_on_sale(self):
        return self.current_price < self.base_price

    @property
    def display_discount_percentage(self):
        return discount_percent(self.base_price, self.current_price)

    @property
    def original_price(self):
        """Return base price (original price before discount)"""
        return self.base_price

    @property
    def regular_price(self):
        """Explicit ecommerce alias for the undiscounted price."""
        return self.base_price

    @property
    def sale_price(self):
        """Explicit ecommerce alias for the calculated selling price."""
        return self.current_price

    @property
    def has_variants(self):
        return any(variant.is_active for variant in self.variants.all())

    @property
    def needs_variant_selection(self):
        return sum(variant.is_active for variant in self.variants.all()) > 1

    @property
    def is_in_stock(self):
        active_variants = [variant for variant in self.variants.all() if variant.is_active]
        if active_variants:
            return any(variant.is_in_stock for variant in active_variants)
        return not self.track_inventory or self.stock_quantity > 0

    @property
    def availability_label(self):
        return 'In stock' if self.is_in_stock else 'Out of stock'

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    """Product variants (sizes, weights, etc.)"""
    SIZE_CHOICES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)  # e.g., "10-20KG", "Small", "Large"
    size_code = models.CharField(max_length=10, choices=SIZE_CHOICES, blank=True)
    weight_info = models.CharField(max_length=50, blank=True)  # e.g., "10-20KG"
    sku = models.CharField(max_length=100, blank=True, db_index=True)
    barcode = models.CharField(max_length=100, blank=True)
    
    # Variant-specific pricing
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    discount_percentage = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Stock
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['product', 'name']

    @property
    def current_price(self):
        return selling_price(self.original_price, self.discount_percentage, self.selling_price)

    @property
    def original_price(self):
        """Return original price for this variant"""
        return self.price_override if self.price_override is not None else self.product.base_price

    @property
    def is_in_stock(self):
        """Check if variant is in stock"""
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        """Check if variant has low stock"""
        return self.stock_quantity <= self.low_stock_threshold

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductImage(models.Model):
    """Product images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    source_url = models.URLField(blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-is_primary']

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"

    @property
    def display_url(self):
        """Use locally stored media when present, otherwise the imported Shopify URL."""
        return self.image.url if self.image else self.source_url


class ProductSpecification(models.Model):
    """Product specifications/key features"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=100, blank=True)  # e.g., "Ingredients", "Dosage"
    value = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ['product', 'name']

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class Banner(models.Model):
    """Homepage banners"""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='banners/')
    link = models.URLField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class ContactInfo(models.Model):
    """Contact information for the site"""
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    
    class Meta:
        verbose_name_plural = "Contact Information"

    def __str__(self):
        return f"{self.city}, {self.state}"


class Cart(models.Model):
    """Shopping cart"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.id}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    """Items in shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'product', 'product_variant']

    @property
    def total_price(self):
        if self.product_variant:
            return self.product_variant.current_price * self.quantity
        return self.product.current_price * self.quantity

    def __str__(self):
        if self.product_variant:
            return f"{self.product.name} ({self.product_variant.name}) x {self.quantity}"
        return f"{self.product.name} x {self.quantity}"


class CustomerAddress(models.Model):
    """Saved customer shipping and billing addresses."""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=50, default='Home')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default_shipping', '-updated_at']
        verbose_name_plural = 'Customer addresses'

    def __str__(self):
        return f"{self.full_name} — {self.label}"


class Order(models.Model):
    """Checkout snapshot; payment confirmation is a separate operation."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    checkout_key = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    checkout_cart = models.ForeignKey(Cart, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders', editable=False)
    stock_deducted = models.BooleanField(default=False, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=150, blank=True)
    shipping_name = models.CharField(max_length=150)
    shipping_address_line_1 = models.CharField(max_length=255)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default='India')
    billing_same_as_shipping = models.BooleanField(default=True)
    billing_name = models.CharField(max_length=150, blank=True)
    billing_address_line_1 = models.CharField(max_length=255, blank=True)
    billing_address_line_2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_postal_code = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=100, default='India')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"SV-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    """Snapshot of a purchased product so history survives later catalogue edits."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, blank=True)
    variant_name = models.CharField(max_length=100, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

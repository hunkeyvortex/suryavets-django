from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.text import slugify
import uuid
from decimal import Decimal
from .services.pricing import selling_price, discount_percent


class Category(models.Model):
    """Main pet categories (Cat, Dog, Farm Animals, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    reference_path = models.CharField(max_length=255, blank=True)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
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


class ContactSubmission(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    consent_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

class RequestThrottle(models.Model):
    key = models.CharField(max_length=64, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)

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
    variant_family = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='family_members', help_text='Canonical listing for verified sibling packs. Existing stock and orders stay on this product.')
    family_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    nutrition_information = models.TextField(blank=True)
    nutrition_source = models.URLField(blank=True)
    nutrition_source_note = models.CharField(max_length=500, blank=True)
    nutrition_reviewed = models.BooleanField(default=False, help_text='Publish only after checking the exact product and current packaging/manufacturer information.')
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
    merchandising_active = models.BooleanField(default=False, db_index=True, help_text='Explicit manual homepage selection; imported flags alone never publish.')
    merchandising_rank = models.PositiveIntegerField(default=100)
    is_new_arrival = models.BooleanField(default=False)
    is_promotional = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    catalog_approved_digest = models.CharField(max_length=64, blank=True, editable=False)

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.slug])

    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [('approve_catalog', 'Can approve catalog products for sale')]
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
        variants = list(self.variants.all())
        if variants:
            return any(variant.is_active and variant.is_in_stock for variant in variants)
        return not self.track_inventory or self.stock_quantity > 0

    @property
    def availability_label(self):
        return 'In stock' if self.is_in_stock else 'Out of stock'

    def __str__(self):
        return self.name


class CatalogReviewEvent(models.Model):
    """Append-only staff decision; stock and purchased history are never rewritten."""
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='catalog_reviews')
    actor = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    decision = models.CharField(max_length=10, choices=[('approved', 'Approved'), ('held', 'Held for review')])
    created_at = models.DateTimeField(auto_now_add=True)
    digest = models.CharField(max_length=64, blank=True)
    evidence = models.TextField()
    snapshot = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at', '-pk']


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
    quantity = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(Decimal('0.001'))], help_text='Verified net pack quantity, not animal weight or shipping weight.')
    unit = models.CharField(max_length=10, blank=True, choices=[('g', 'g'), ('kg', 'kg'), ('ml', 'ml'), ('L', 'L'), ('count', 'count')])
    comparison_group = models.CharField(max_length=100, blank=True, help_text='Only identical formulations/items may share a comparison group. Blank disables value comparisons.')
    attributes = models.JSONField(default=dict, blank=True, help_text='Other exact options, such as flavour or colour.')
    display_order = models.PositiveIntegerField(default=0, blank=True)
    image = models.ForeignKey('ProductImage', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_variants')
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
        ordering = ['display_order', 'name', 'pk']
        unique_together = ['product', 'name']

    def clean(self):
        super().clean()
        errors = {}
        if bool(self.quantity) != bool(self.unit):
            errors['quantity'] = 'Supply both a verified quantity and its unit, or leave both blank.'
        if self.quantity is not None and self.quantity <= 0:
            errors['quantity'] = 'Pack quantity must be positive.'
        if not isinstance(self.attributes, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in self.attributes.items()):
            errors['attributes'] = 'Use a JSON object with text option names and values.'
        if self.image_id and (self.image.product_id != self.product_id or not self.image.is_active):
            errors['image'] = 'Choose an active image belonging to this exact product.'
        if self.price_override is not None and self.price_override < 0:
            errors['price_override'] = 'MRP cannot be negative.'
        if self.product_id and self.selling_price is not None and self.selling_price > self.original_price:
            errors['selling_price'] = 'Selling price cannot exceed MRP.'
        if errors:
            raise ValidationError(errors)

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


class ActiveImageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ProductImage(models.Model):
    """Product images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    source_url = models.URLField(max_length=500, blank=True)
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    check_error = models.CharField(max_length=250, blank=True)
    family_reference_for = models.ForeignKey('Product', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='approved_family_artwork', help_text='Staff-approved generic reference for this canonical family, never an exact-pack assignment.')
    family_reference_note = models.CharField(max_length=500, blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    objects = ActiveImageManager()
    all_objects = models.Manager()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-is_primary']

    def clean(self):
        super().clean()
        if self.family_reference_for_id:
            root = self.family_reference_for
            if root.variant_family_id or not root.is_active or (self.product.variant_family_id or self.product_id) != root.pk:
                raise ValidationError({'family_reference_for': 'Choose this product’s active canonical family only.'})
            if not self.family_reference_note.strip() or self.check_error:
                raise ValidationError({'family_reference_note': 'Approval evidence and a valid image are required.'})

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"

    @property
    def display_url(self):
        """Use locally stored media when present, otherwise the imported Shopify URL."""
        if not self.is_active or self.check_error:
            return ''
        return self.image.url if self.image else self.source_url

    @property
    def thumbnail_url(self):
        if not self.display_url:
            return ''
        return self.thumbnail.url if self.thumbnail else self.display_url


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
    def display_image(self):
        if self.product_variant:
            from .services.pack_images import pack_photos
            return next(iter(pack_photos(self.product_variant)), None)
        from .services.pack_images import product_photos
        return next(iter(product_photos(self.product)), None) if self.product else None

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


class Coupon(models.Model):
    class Kind(models.TextChoices):
        PERCENT = 'percent', 'Percentage off'
        FIXED = 'fixed', 'Fixed amount off (₹)'

    code = models.CharField(max_length=40, unique=True, validators=[RegexValidator(r'^[A-Z0-9][A-Z0-9_-]{2,39}$', 'Use 3–40 letters, numbers, hyphens or underscores.')])
    name = models.CharField(max_length=120, help_text='Internal campaign name.')
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PERCENT)
    value = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    minimum_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    maximum_discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    used_count = models.PositiveIntegerField(default=0, editable=False)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(value__gt=0), name='coupon_positive_value'),
            models.CheckConstraint(condition=~models.Q(kind='percent') | models.Q(value__lte=100), name='coupon_percent_maximum'),
            models.CheckConstraint(condition=models.Q(minimum_subtotal__gte=0), name='coupon_nonnegative_minimum'),
        ]

    def clean(self):
        super().clean()
        if self.kind == self.Kind.PERCENT and self.value is not None and self.value > 100:
            raise ValidationError({'value': 'A percentage discount cannot exceed 100%.'})
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'End time must be after start time.'})
        if self.max_uses is not None and self.max_uses < self.used_count:
            raise ValidationError({'max_uses': 'The limit cannot be lower than the number already used.'})

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class Order(models.Model):
    """Checkout snapshot; payment confirmation is a separate operation."""
    class Status(models.TextChoices):
        AWAITING_PAYMENT = 'awaiting_payment', 'Awaiting payment'
        PENDING = 'pending', 'Placed'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        PACKED = 'packed', 'Packed'
        SHIPPED = 'shipped', 'Shipped'
        OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for delivery'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        REFUND_PENDING = 'refund_pending', 'Refund pending'
        PARTIALLY_REFUNDED = 'partially_refunded', 'Partially refunded'
        REFUNDED = 'refunded', 'Refunded'

    class ReturnStatus(models.TextChoices):
        NONE = '', 'No return'
        REQUESTED = 'requested', 'Return requested'
        APPROVED = 'approved', 'Return approved'
        REJECTED = 'rejected', 'Return rejected'
        RECEIVED = 'received', 'Returned'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    checkout_key = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    checkout_cart = models.ForeignKey(Cart, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders', editable=False)
    stock_deducted = models.BooleanField(default=False, editable=False)
    inventory_recorded = models.BooleanField(default=False, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=150, blank=True)
    return_status = models.CharField(max_length=20, choices=ReturnStatus.choices, blank=True, default='')
    courier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=150, blank=True)
    tracking_url = models.URLField(max_length=500, blank=True)
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
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.PROTECT, related_name='orders', editable=False)
    coupon_code = models.CharField(max_length=40, blank=True, editable=False)
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

    @property
    def payment_method_label(self):
        return {'cash_on_delivery': 'Cash on Delivery', 'online': 'Online payment'}.get(self.payment_method, self.payment_method or 'Not recorded')


class OrderItem(models.Model):
    """Snapshot of a purchased product so history survives later catalogue edits."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, blank=True)
    variant_name = models.CharField(max_length=100, blank=True)
    image_reference = models.CharField(max_length=1000, blank=True, help_text='Image URL captured at purchase; never inferred for old orders.')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"


class InventoryMovement(models.Model):
    """Append-only stock history from CRM adjustments and checkout, not opening balances."""
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_movements')
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name='stock_movements')
    actor = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=20, choices=[('checkout', 'Checkout'), ('cancellation', 'Cancellation'), ('adjustment', 'Adjustment')])
    delta = models.IntegerField()
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=500)
    request_key = models.UUIDField(unique=True, null=True, blank=True, editable=False)
    reversal_of = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='reversal')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.CheckConstraint(condition=~models.Q(delta=0), name='stock_movement_nonzero'),
            models.CheckConstraint(condition=models.Q(quantity_after=models.F('quantity_before') + models.F('delta')), name='stock_movement_balances'),
        ]


class CRMActivity(models.Model):
    """Internal notes and immutable operational history; never shown on the storefront."""
    actor = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name='crm_activity')
    customer_email = models.EmailField(blank=True, db_index=True)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.PROTECT, related_name='activity')
    kind = models.CharField(max_length=20, choices=[('note', 'Internal note'), ('status', 'Order status'), ('coupon', 'Coupon change')])
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        permissions = [
            ('access_crm', 'Access customer and order CRM'),
            ('manage_crm_orders', 'Process and cancel orders in CRM'),
            ('manage_crm_payments', 'Record externally verified payment and refund outcomes'),
            ('adjust_crm_inventory', 'Adjust stock through audited CRM workflow'),
            ('write_crm_notes', 'Write internal CRM notes'),
            ('manage_crm_coupons', 'Create and edit checkout coupons'),
        ]


class OrderStatusHistory(models.Model):
    """Append-only event shared by staff and customers. Notes have explicit audiences."""
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='events')
    kind = models.CharField(max_length=12, choices=[('order', 'Order'), ('return', 'Return'), ('payment', 'Payment')], default='order')
    status = models.CharField(max_length=24)
    timestamp = models.DateTimeField(null=True, blank=True, help_text='Null means the legacy milestone time is unknown.')
    recorded_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    customer_visible = models.BooleanField(default=True)
    internal_note = models.TextField(blank=True, max_length=2000)
    customer_note = models.TextField(blank=True, max_length=1000)

    class Meta:
        ordering = ['recorded_at', 'pk']

    @property
    def label(self):
        choices = {'order': Order.Status.choices, 'payment': Order.PaymentStatus.choices, 'return': Order.ReturnStatus.choices}
        return dict(choices.get(self.kind, [])).get(self.status, self.status)


class OrderNotification(models.Model):
    event = models.ForeignKey(OrderStatusHistory, on_delete=models.PROTECT, related_name='notifications')
    channel = models.CharField(max_length=20, default='email')
    audience = models.CharField(max_length=10, default='customer', choices=[('customer', 'Customer'), ('admin', 'Admin')])
    recipient = models.EmailField(blank=True)
    state = models.CharField(max_length=12, default='pending', choices=[('pending', 'Pending'), ('sending', 'Sending'), ('sent', 'Provider accepted'), ('failed', 'Failed'), ('preview', 'Sandbox preview only')])
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=200, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    retryable = models.BooleanField(default=False)
    next_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['event', 'channel', 'audience'], name='one_notification_per_event_audience')]


class PaymentAttempt(models.Model):
    """One gateway order per checkout. Unknown network outcomes require reconciliation."""
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='payment_attempt')
    gateway_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    gateway_payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    amount = models.PositiveBigIntegerField(help_text='Server-calculated INR paise')
    currency = models.CharField(max_length=3, default='INR')
    state = models.CharField(max_length=12, default='new', choices=[('new', 'Not started'), ('creating', 'Creating'), ('ready', 'Ready'), ('uncertain', 'Needs reconciliation'), ('paid', 'Verified paid')])
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CustomerProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True)


class CustomerPet(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=80)
    pet_type = models.ForeignKey(PetCategory, on_delete=models.PROTECT)
    breed = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True, choices=[('', 'Not specified'), ('female', 'Female'), ('male', 'Male')])
    weight = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    # Photos deliberately omitted until private media delivery is available.


class WishlistItem(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='unique_customer_wishlist_product')]
        ordering = ['-created_at']


class SupportRequest(models.Model):
    CATEGORIES = [('order', 'Order issue'), ('delivery', 'Delivery issue'), ('payment', 'Payment issue'), ('product', 'Product issue'), ('return', 'Return/refund'), ('other', 'Other')]
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='support_requests')
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name='support_requests')
    category = models.CharField(max_length=12, choices=CATEGORIES)
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=3000)
    state = models.CharField(max_length=12, default='open', choices=[('open', 'Open'), ('resolved', 'Resolved')])
    response = models.TextField(max_length=3000, blank=True, help_text='Customer-visible reply.')
    responded_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

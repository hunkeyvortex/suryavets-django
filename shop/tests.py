from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Brand, Category, Order, OrderItem, PetCategory, Product, ProductVariant, Subcategory


class CategoryHierarchyTests(TestCase):
    def setUp(self):
        self.root = Category.objects.create(name='Cat')
        self.group = Category.objects.create(name='Medicine For Cats', parent=self.root)
        self.leaf = Category.objects.create(name='Allergy Relief For Cats', parent=self.group)
        self.deep = Category.objects.create(name='Deeper category', parent=self.leaf)
        self.product = Product.objects.create(name='Category test item', category=self.root, base_price=Decimal('100'), stock_quantity=2)
        self.product.collections.add(self.deep, self.leaf)

    def test_descendants_are_included_once_in_each_parent_listing(self):
        for node in (self.root, self.group, self.leaf, self.deep):
            response = self.client.get(node.get_absolute_url())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['total_count'], 1)
            self.assertEqual(list(response.context['products']), [self.product])

    def test_cycles_are_rejected_and_ancestors_are_ordered(self):
        from django.core.exceptions import ValidationError
        self.assertEqual(self.deep.get_ancestors(), [self.root, self.group, self.leaf])
        self.root.parent = self.deep
        with self.assertRaises(ValidationError):
            self.root.full_clean()

    def test_inactive_ancestor_hides_descendants(self):
        self.group.is_active = False
        self.group.save()
        response = self.client.get(self.leaf.get_absolute_url())
        self.assertEqual(response.status_code, 404)
        response = self.client.get('/')
        self.assertNotContains(response, 'Expand Medicine For Cats')

    def test_exact_tag_matching_does_not_guess_medical_classification(self):
        from shop.services.taxonomy import collection_tag_index, matching_collections
        self.leaf.reference_path = '/collections/allergy-relief-for-cats'
        self.leaf.save()
        index = collection_tag_index()
        self.assertEqual(matching_collections(['allergy-relief-for-cats'], index), {self.leaf.pk})
        self.assertEqual(matching_collections(['allergy'], index), set())


class CatalogueAndOrderModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Nutrition')
        self.brand = Brand.objects.create(name='Royal Canin')
        self.pet_category = PetCategory.objects.create(name='Dog')
        self.product = Product.objects.create(
            name='Veterinary Diet',
            sku='SV-DIET-001',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('1000.00'),
            discount_percentage=10,
            stock_quantity=5,
        )
        self.product.pet_categories.add(self.pet_category)

    def test_product_prices_and_availability(self):
        self.assertEqual(self.product.regular_price, Decimal('1000.00'))
        self.assertEqual(self.product.sale_price, Decimal('900.00'))
        self.assertTrue(self.product.is_in_stock)
        self.assertEqual(self.product.availability_label, 'In stock')

    def test_active_variants_control_availability(self):
        ProductVariant.objects.create(
            product=self.product,
            name='2 kg',
            sku='SV-DIET-001-2KG',
            stock_quantity=0,
        )
        self.assertFalse(self.product.is_in_stock)

    def test_order_number_and_line_total_are_preserved(self):
        user = get_user_model().objects.create_user(username='customer', password='safe-password')
        order = Order.objects.create(
            user=user,
            email='customer@example.com',
            phone='9999999999',
            shipping_name='Test Customer',
            shipping_address_line_1='1 Test Street',
            shipping_city='Mumbai',
            shipping_state='Maharashtra',
            shipping_postal_code='400001',
            subtotal=Decimal('900.00'),
            total=Decimal('900.00'),
        )
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            sku=self.product.sku,
            unit_price=Decimal('900.00'),
            quantity=2,
        )
        self.assertTrue(order.order_number.startswith('SV-'))
        self.assertEqual(item.line_total, Decimal('1800.00'))


class StorefrontLayoutTests(TestCase):
    def test_homepage_uses_the_shared_storefront_chrome(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base_shared.html')
        self.assertContains(response, 'Free delivery on orders above ₹499')
        self.assertContains(response, 'id="primary-navigation"')
        self.assertContains(response, 'Join our email list')
        self.assertContains(response, 'data-hero-slider')
        self.assertContains(response, 'Genuine Products')
        self.assertContains(response, 'Our catalogue is being prepared')
        self.assertNotContains(response, 'Why Choose Surya Vets?')


class CatalogViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Dog Care')
        self.subcategory = Subcategory.objects.create(name='Supplements', category=self.category)
        self.brand = Brand.objects.create(name='Surya Nutrition')
        self.pet_category = PetCategory.objects.create(name='Dog')
        self.product = Product.objects.create(
            name='Joint Support Chews',
            sku='SV-JOINT-001',
            category=self.category,
            subcategory=self.subcategory,
            brand=self.brand,
            base_price=Decimal('799.00'),
            stock_quantity=8,
            is_featured=True,
        )
        self.product.pet_categories.add(self.pet_category)

    def test_all_products_page_is_database_backed(self):
        response = self.client.get(reverse('shop:category_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/product_list.html')
        self.assertContains(response, self.product.name)

    def test_category_and_subcategory_pages_filter_the_catalogue(self):
        category_response = self.client.get(
            reverse('shop:category_detail', args=[self.category.slug])
        )
        subcategory_response = self.client.get(
            reverse('shop:subcategory_detail', args=[self.category.slug, self.subcategory.slug])
        )

        self.assertContains(category_response, self.product.name)
        self.assertContains(subcategory_response, self.product.name)

    def test_product_detail_uses_the_product_slug(self):
        response = self.client.get(reverse('shop:product_detail', args=[self.product.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/product_detail.html')
        self.assertContains(response, self.product.sku)

    def test_catalogue_filters_and_sorting_are_applied(self):
        response = self.client.get(reverse('shop:category_list'), {
            'brand': self.brand.slug,
            'pet': self.pet_category.slug,
            'availability': 'in_stock',
            'min_price': '700',
            'max_price': '900',
            'sort': 'price_low',
        })

        self.assertContains(response, self.product.name)
        self.assertEqual(list(response.context['products']), [self.product])

    def test_searches_product_name_sku_brand_and_category(self):
        for query in (self.product.name, self.product.sku, self.brand.name, self.category.name):
            response = self.client.get(reverse('shop:search'), {'q': query})
            self.assertContains(response, self.product.name)

    def test_anonymous_shopper_can_add_update_and_remove_cart_items(self):
        add_response = self.client.post(
            reverse('shop:add_to_cart', args=[self.product.id]),
            {'quantity': 2, 'next': reverse('shop:cart')},
        )
        self.assertRedirects(add_response, reverse('shop:cart'))

        cart_response = self.client.get(reverse('shop:cart'))
        self.assertContains(cart_response, self.product.name)
        self.assertContains(cart_response, '₹1598.00')
        item = cart_response.context['cart_items'].get()

        update_response = self.client.post(
            reverse('shop:update_cart_item', args=[item.id]), {'quantity': 3}
        )
        self.assertRedirects(update_response, reverse('shop:cart'))
        self.assertEqual(item.__class__.objects.get(pk=item.pk).quantity, 3)

        remove_response = self.client.post(reverse('shop:remove_from_cart', args=[item.id]))
        self.assertRedirects(remove_response, reverse('shop:cart'))
        self.assertFalse(item.__class__.objects.filter(pk=item.pk).exists())

    def test_guest_checkout_creates_a_pending_order_and_clears_the_cart(self):
        self.client.post(reverse('shop:add_to_cart', args=[self.product.id]), {'quantity': 2})
        response = self.client.post(reverse('shop:checkout'), {
            'email': 'guest@example.com', 'phone': '9999999999', 'shipping_name': 'Guest Customer',
            'shipping_address_line_1': '1 Test Street', 'shipping_city': 'Mumbai',
            'shipping_state': 'Maharashtra', 'shipping_postal_code': '400001',
            'billing_same_as_shipping': 'on', 'payment_method': 'cash_on_delivery', 'terms': 'on',
        })

        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(email='guest@example.com')
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertEqual(order.payment_method, 'cash_on_delivery')
        self.assertEqual(order.items.get().quantity, 2)
        self.assertEqual(response.context['order'], order)

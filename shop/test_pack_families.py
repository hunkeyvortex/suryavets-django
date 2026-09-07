import io
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import TestCase
from django.core.management import call_command
from django.urls import reverse
from .models import Product,ProductVariant,Category,CartItem,InventoryMovement,CRMActivity,OrderItem
from .services.pack_families import candidates
from .test_checkout import CHECKOUT_DATA


class PackFamilyTests(TestCase):
    def setUp(self):
        category=Category.objects.create(name='Dog')
        self.small=Product.objects.create(name='Recipe food (S)',slug='recipe-food-s-500gm',category=category,base_price=120,selling_price=100,stock_quantity=2)
        self.large=Product.objects.create(name='Recipe food (L)',slug='recipe-food-l-2kg',category=category,base_price=400,selling_price=300,stock_quantity=3)
        self.a=ProductVariant.objects.create(product=self.small,name='500GM',sku='SMALL',price_override=120,selling_price=100,stock_quantity=2)
        self.b=ProductVariant.objects.create(product=self.large,name='2KG',sku='LARGE',price_override=400,selling_price=300,stock_quantity=3)

    def group(self, apply=True):
        with TemporaryDirectory() as tmp:
            call_command('group_existing_packs',apply=apply,report=str(Path(tmp)/'report.json'),stdout=io.StringIO())

    def test_grouping_preserves_product_and_variant_identities(self):
        self.group(False); self.large.refresh_from_db(); self.assertIsNone(self.large.variant_family_id)
        self.group(); self.group()
        self.large.refresh_from_db(); self.assertEqual(self.large.variant_family_id,self.small.pk)
        self.a.refresh_from_db(); self.b.refresh_from_db()
        self.assertEqual(self.b.product_id,self.large.pk)
        self.assertEqual(self.b.current_price,300); self.assertEqual(self.b.stock_quantity,3)
        self.assertEqual(self.a.quantity,500); self.assertEqual(self.a.unit,'g')
        self.assertEqual(Product.objects.count(),2); self.assertEqual(ProductVariant.objects.count(),2)
        self.assertEqual(CRMActivity.objects.count(),1)

    def test_family_choice_adds_correct_original_product_and_preserves_order(self):
        self.group()
        url=reverse('shop:product_detail',args=[self.small.slug])
        response=self.client.get(url)
        self.assertContains(response,'500GM'); self.assertContains(response,'2KG')
        self.assertEqual(len(response.context['variant_options']),2)
        self.assertContains(self.client.get(reverse('shop:category_list')),'Choose size')
        add=reverse('shop:add_to_cart',args=[self.small.pk])
        self.client.post(add,{'variant_id':self.b.pk})
        item=CartItem.objects.get(); self.assertEqual(item.product_id,self.large.pk); self.assertEqual(item.product_variant_id,self.b.pk)
        token=self.client.get(reverse('shop:checkout')).context['checkout_token']
        self.client.post(reverse('shop:checkout'),{**CHECKOUT_DATA,'checkout_token':token})
        line=OrderItem.objects.get(); self.assertEqual(line.product_id,self.large.pk); self.assertEqual(line.unit_price,300)
        response=self.client.get(reverse('shop:product_detail',args=[self.large.slug]))
        self.assertEqual(response.status_code,200); self.assertEqual(response.context['selected_variant'].pk,self.b.pk)

    def test_unrelated_pack_injection_and_silent_default_are_blocked(self):
        self.group()
        self.client.post(reverse('shop:add_to_cart',args=[self.small.pk]),{})
        self.assertFalse(CartItem.objects.exists())
        other=Product.objects.create(name='Other',category=self.small.category,base_price=1)
        self.assertEqual(self.client.post(reverse('shop:add_to_cart',args=[other.pk]),{'variant_id':self.b.pk}).status_code,404)

    def test_conflicting_pack_sizes_are_reviewed_not_linked(self):
        self.b.name='1.5KG'; self.b.save()
        self.group(); self.large.refresh_from_db(); self.assertIsNone(self.large.variant_family_id)

    def test_stock_reset_is_audited_idempotent_and_does_not_change_prices(self):
        batch=uuid.uuid4(); out=io.StringIO()
        options={'quantity':10,'batch':batch,'reason':'Owner requested test stock','stdout':out}
        call_command('set_catalog_stock',**options)
        self.a.refresh_from_db(); self.assertEqual(self.a.stock_quantity,2)
        self.assertFalse(InventoryMovement.objects.exists())
        call_command('set_catalog_stock',apply=True,**options)
        self.a.refresh_from_db(); self.b.refresh_from_db(); self.small.refresh_from_db()
        self.assertEqual(self.a.stock_quantity,10); self.assertEqual(self.b.stock_quantity,10); self.assertEqual(self.small.stock_quantity,10)
        self.assertEqual(self.a.current_price,100)
        self.assertEqual(InventoryMovement.objects.count(),2)
        self.a.stock_quantity=9; self.a.save()
        call_command('set_catalog_stock',apply=True,**options)
        self.a.refresh_from_db(); self.assertEqual(self.a.stock_quantity,9)
        self.assertEqual(InventoryMovement.objects.count(),2)

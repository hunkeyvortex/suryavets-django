import base64
import io
import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from PIL import Image
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .models import Category, Product, ProductImage, ProductVariant


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set SURYA_BROWSER_NODE for buying UI verification.')
class VariantBrowserTests(StaticLiveServerTestCase):
    def test_mobile_buying_journey(self):
        self.run_buying_fixture(False)

    def test_linked_source_pack_buying_journey(self):
        self.run_buying_fixture(True)

    def run_buying_fixture(self, linked):
        category=Category.objects.create(name='Dog')
        product=Product.objects.create(name='Complete Chicken Nutrition',slug='variant-test-food',category=category,base_price=1200)
        if linked:
            product.family_name=product.name; product.save()
        for index, (name,qty,price,mrp,stock,color) in enumerate([
            ('1.5 kg','1.5',1050,1200,100,'#dbead4'), ('4 kg','4',2500,2800,100,'#d7e9ea'),
            ('5 kg','5',2950,3500,100,'#efddb9'), ('10 kg','10',6500,7000,0,'#dddddd')]):
            buffer=io.BytesIO(); Image.new('RGB',(120,170),color).save(buffer,format='PNG')
            source=Product.objects.create(name=f'Complete Chicken Nutrition {name}',slug=f'linked-pack-{index}',category=category,base_price=mrp,variant_family=product) if linked and index else product
            photo=ProductImage.objects.create(product=source,source_url='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode(),alt_text=f'{name} test fixture',order=index)
            ProductVariant.objects.create(product=source,name=name,quantity=qty,unit='kg',comparison_group='same chicken',sku=f'FOOD-{index}',
                price_override=mrp,selling_price=price,stock_quantity=stock,display_order=index,image=photo)
        result=subprocess.run([os.environ['SURYA_BROWSER_NODE'],str(Path(__file__).with_name('variant_browser_test.cjs')),self.live_server_url],capture_output=True,text=True,timeout=200)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

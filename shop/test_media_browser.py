import base64
import io
import os
import subprocess
from pathlib import Path
from unittest import skipUnless
from PIL import Image
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .models import Category, Product, ProductImage


@skipUnless(os.environ.get('SURYA_BROWSER_NODE'), 'Set SURYA_BROWSER_NODE for gallery verification.')
class MediaBrowserTests(StaticLiveServerTestCase):
    def test_gallery_and_nutrition_at_phone_widths(self):
        product=Product.objects.create(name='Gallery test product', slug='gallery-test-product', category=Category.objects.create(name='Dog'), base_price=100, selling_price=90, stock_quantity=3,
            nutrition_information='Fixture nutrition text', nutrition_reviewed=True, nutrition_source='https://example.com/test-label')
        for index,color in enumerate(['#dbead4','#efddb9']):
            buffer=io.BytesIO(); Image.new('RGB',(100,160),color).save(buffer,format='PNG')
            ProductImage.objects.create(product=product, source_url='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode(), alt_text=f'Test photo {index+1}', order=index)
        result=subprocess.run([os.environ['SURYA_BROWSER_NODE'], str(Path(__file__).with_name('media_browser_test.cjs')),self.live_server_url],capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

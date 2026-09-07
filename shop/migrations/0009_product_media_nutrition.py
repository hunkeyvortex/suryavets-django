from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shop', '0008_checkout_coupons')]
    operations = [
        migrations.AddField(model_name='product', name='ingredients', field=models.TextField(blank=True)),
        migrations.AddField(model_name='product', name='nutrition_information', field=models.TextField(blank=True)),
        migrations.AddField(model_name='product', name='nutrition_source', field=models.URLField(blank=True)),
        migrations.AddField(model_name='product', name='nutrition_source_note', field=models.CharField(blank=True, max_length=500)),
        migrations.AddField(model_name='product', name='nutrition_reviewed', field=models.BooleanField(default=False, help_text='Publish only after checking the exact product and current packaging/manufacturer information.')),
        migrations.AddField(model_name='productimage', name='thumbnail', field=models.ImageField(blank=True, upload_to='products/thumbnails/')),
        migrations.AddField(model_name='productimage', name='checked_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='productimage', name='check_error', field=models.CharField(blank=True, max_length=250)),
    ]

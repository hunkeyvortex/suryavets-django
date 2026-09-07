from django.db import migrations


def seed_history(apps, schema_editor):
    Order = apps.get_model('shop', 'Order')
    Event = apps.get_model('shop', 'OrderStatusHistory')
    db = schema_editor.connection.alias
    for order in Order.objects.using(db).iterator():
        Event.objects.using(db).create(order_id=order.pk, kind='order', status='pending', timestamp=order.created_at,
                                      internal_note='Known creation time from the existing order record.')
        if order.status != 'pending':
            Event.objects.using(db).create(order_id=order.pk, kind='order', status=order.status, timestamp=None,
                                          internal_note='Observed legacy status; original transition time was not recorded.')
    # No notifications for historical backfills.


class Migration(migrations.Migration):
    dependencies = [('shop', '0012_alter_crmactivity_options_order_courier_and_more')]
    operations = [migrations.RunPython(seed_history, migrations.RunPython.noop)]

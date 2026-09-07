from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create scoped CRM roles without assigning users or changing passwords.'

    def handle(self, *args, **options):
        roles = {
            'Surya CRM Viewer': ['access_crm'],
            'Surya CRM Operations': ['access_crm', 'manage_crm_orders', 'write_crm_notes'],
            'Surya CRM Manager': ['access_crm', 'manage_crm_orders', 'manage_crm_payments', 'write_crm_notes', 'adjust_crm_inventory', 'manage_crm_coupons', 'add_product', 'change_product'],
        }
        for name, codes in roles.items():
            group, _ = Group.objects.get_or_create(name=name)
            permissions = Permission.objects.filter(content_type__app_label='shop', codename__in=codes)
            group.permissions.add(*permissions)
            self.stdout.write(f'{name}: CRM permissions ensured (existing permissions preserved).')
        self.stdout.write('Assign a group and Staff status to an existing user in Django Admin. No users were granted access automatically.')

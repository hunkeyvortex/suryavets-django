from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from shop.models import RequestThrottle, OrderNotification

class Command(BaseCommand):
    help = 'Read-only operational readiness; optional cleanup of expired throttle counters only.'
    def add_arguments(self, parser):
        parser.add_argument('--clean-expired-throttles', action='store_true')
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        pending = MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes())
        self.stdout.write(f'Database reachable. Pending migrations: {len(pending)}')
        self.stdout.write(f"Outbox requiring reconciliation: {OrderNotification.objects.filter(state='sending').count()}")
        expired = RequestThrottle.objects.filter(expires_at__lt=timezone.now())
        self.stdout.write(f'Expired throttle counters: {expired.count()}')
        if options['clean_expired_throttles']:
            expired.delete()
            self.stdout.write('Expired throttle counters removed; no business records changed.')

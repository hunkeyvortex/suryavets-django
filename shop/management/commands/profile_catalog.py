import json
import re
import time
from collections import Counter
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext


class Command(BaseCommand):
    help = 'Read-only local catalog request timings and SQL diagnostics. No network calls.'

    def handle(self, *args, **options):
        with override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False):
            client = Client()
            for path in ['/category/dog/', '/search/?q=royal', '/category/dog/?sort=price_low']:
                for run in range(2):
                    start = time.perf_counter()
                    with CaptureQueriesContext(connection) as queries:
                        response = client.get(path)
                    normalized = Counter(re.sub(r"'[^']*'|\b\d+\b", '?', q['sql']) for q in queries)
                    self.stdout.write(json.dumps({'path': path, 'run': run, 'status': response.status_code,
                        'seconds': round(time.perf_counter()-start, 3), 'queries': len(queries),
                        'sql_seconds': round(sum(float(q['time']) for q in queries), 3),
                        'repeated_shapes': [(q[:150], n) for q, n in normalized.items() if n > 1],
                        'slowest': [{'time': q['time'], 'sql': q['sql'][:160]} for q in sorted(queries, key=lambda q: float(q['time']), reverse=True)[:3]]}))

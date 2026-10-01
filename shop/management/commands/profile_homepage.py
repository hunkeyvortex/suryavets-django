"""Read-only before/after template benchmark against the task checkpoint."""
import copy
import json
import statistics
import subprocess
import time
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext


class Command(BaseCommand):
    def handle(self, *args, **options):
        names = ['base_shared.html', 'includes/product_card_v2.html', 'includes/card_variant.html', 'includes/product_gallery.html']
        old = {name: subprocess.check_output(['git', '-c', 'safe.directory='+str(settings.BASE_DIR).replace('\\','/'),
            'show', 'codex/image-polish-checkpoint-20260929:shop/templates/'+name], cwd=settings.BASE_DIR).decode('utf-8') for name in names}
        for label, templates in [('checkpoint', old), ('current', {})]:
            configuration = copy.deepcopy(settings.TEMPLATES)
            configuration[0]['APP_DIRS'] = False
            configuration[0]['OPTIONS']['loaders'] = [('django.template.loaders.locmem.Loader', templates),
                'django.template.loaders.filesystem.Loader', 'django.template.loaders.app_directories.Loader']
            with override_settings(TEMPLATES=configuration, ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False):
                samples = []
                client = Client()
                for run in range(5):
                    start = time.perf_counter()
                    with CaptureQueriesContext(connection) as queries:
                        response = client.get('/')
                    samples.append(time.perf_counter()-start)
                    if response.status_code != 200:
                        raise RuntimeError('Homepage did not render')
                self.stdout.write(json.dumps({'version': label, 'median_seconds': round(statistics.median(samples),4),
                    'queries': len(queries), 'samples': [round(s,4) for s in samples]}))

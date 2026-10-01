"""Read-only staff filters from the generated image audit, not purchasing approval."""
import json
from functools import lru_cache
from pathlib import Path
from django.conf import settings


@lru_cache(maxsize=2)
def _read(path, modified, size):
    report = json.loads(Path(path).read_text(encoding='utf-8'))
    return [dict(zip(report['headers'], row)) for row in report['rows']]


def matching_products(kind):
    recovery = Path(settings.BASE_DIR)/'catalog_review'/'image_recovery_index.json'
    if recovery.exists():
        try:
            info = recovery.stat()
            rows = _read(str(recovery), info.st_mtime_ns, info.st_size)
            if kind == 'recovered':
                data = _recovery_changes(str(recovery), info.st_mtime_ns, info.st_size)
                return list({row[0] for row in data if row[5] == 'HIGH exact recovery'})
            return list({row['Product ID'] for row in rows if not row['Current Image'] or (kind == 'review' and row['Confidence'] != 'HIGH')})
        except (OSError, ValueError, KeyError, TypeError):
            pass
    path = Path(settings.BASE_DIR)/'catalog_review'/'image_coverage_data.json'
    try:
        info = path.stat()
        rows = _read(str(path), info.st_mtime_ns, info.st_size)
    except (OSError, ValueError, KeyError, TypeError):
        return []
    field, value = {'placeholder': ('Missing Image', 'YES'), 'review': ('Needs Review', 'YES'),
                    'recovered': ('Recovered Image', None)}[kind]
    return list({row['Product ID'] for row in rows if (bool(row[field]) if value is None else row[field] == value)})


@lru_cache(maxsize=2)
def _recovery_changes(path, modified, size):
    return json.loads(Path(path).read_text(encoding='utf-8')).get('applied_records', [])

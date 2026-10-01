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
    path = Path(settings.BASE_DIR)/'catalog_review'/'image_coverage_data.json'
    try:
        info = path.stat()
        rows = _read(str(path), info.st_mtime_ns, info.st_size)
    except (OSError, ValueError, KeyError, TypeError):
        return []
    field, value = {'placeholder': ('Missing Image', 'YES'), 'review': ('Needs Review', 'YES'),
                    'recovered': ('Recovered Image', None)}[kind]
    return list({row['Product ID'] for row in rows if (bool(row[field]) if value is None else row[field] == value)})

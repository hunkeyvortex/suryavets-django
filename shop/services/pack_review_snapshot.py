"""Staff-only cached read of generated evidence. Never auto-approves a record."""
import json
from functools import lru_cache
from pathlib import Path
from django.conf import settings


@lru_cache(maxsize=2)
def _read(path, modified, size):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    by_product = {}
    for row in data.get('rows', []):
        by_product.setdefault(row['Product ID'], []).append(row)
    return {'generated_at': data['generated_at'], 'by_product': by_product}


def snapshot():
    path = Path(settings.BASE_DIR) / 'catalog_review' / 'pack_identity_crm.json'
    try:
        info = path.stat()
        return _read(str(path), info.st_mtime_ns, info.st_size)
    except (OSError, ValueError, KeyError, TypeError):
        return {'generated_at': '', 'by_product': {}}

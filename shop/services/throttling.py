"""Shared fixed-window limits. Hash identifiers; never trust forwarded IPs."""
import hashlib
import time
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from shop.models import RequestThrottle

def allowed(request, scope, limit=5, seconds=900, identity=None):
    identity = identity if identity is not None else request.META.get('REMOTE_ADDR', '')
    key = hashlib.sha256(f'{settings.SECRET_KEY}:{scope}:{identity}:{int(time.time())//seconds}'.encode()).hexdigest()
    with transaction.atomic():
        row, _ = RequestThrottle.objects.get_or_create(key=key, defaults={'expires_at': timezone.now()+timedelta(seconds=seconds)})
        return bool(RequestThrottle.objects.filter(pk=row.pk, attempts__lt=limit).update(attempts=F('attempts')+1))

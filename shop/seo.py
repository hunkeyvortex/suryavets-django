"""Technical metadata only; no invented marketing copy or external requests."""
import json
from pathlib import Path
from functools import lru_cache
from xml.etree.ElementTree import Element, SubElement, tostring
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse, Http404, HttpResponsePermanentRedirect
from django.urls import reverse
from django.views.decorators.http import require_safe
from .models import Product, Category

PRIVATE = ('/account/', '/accounts/', '/crm/', '/admin/', '/cart/', '/checkout/', '/login/', '/register/', '/password-reset/', '/reset/', '/search/')

class IndexingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.method == 'POST' and request.path in ('/login/', '/crm/login/', '/admin/login/'):
            from .services.throttling import allowed
            identity = (request.POST.get('email') or request.POST.get('username') or '').strip().lower()
            ip_ok = allowed(request, 'login-ip', limit=100)
            identity_ok = allowed(request, 'login-identity', limit=20, identity=identity)
            if not ip_ok or not identity_ok:
                response = HttpResponse('Too many sign-in attempts. Please try again later.', status=429)
                response['Cache-Control'] = 'private, no-store'
                response['X-Robots-Tag'] = 'noindex, nofollow'
                return response
        response = self.get_response(request)
        if settings.SITE_NOINDEX or request.path.startswith(PRIVATE) or response.status_code >= 400:
            response['X-Robots-Tag'] = 'noindex, nofollow'
        if request.path.startswith(PRIVATE) and 'no-store' not in response.get('Cache-Control', ''):
            response['Cache-Control'] = 'private, no-store'
        return response

def origin(request):
    return settings.PUBLIC_SITE_URL or request.build_absolute_uri('/').rstrip('/')

@require_safe
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})

@require_safe
def robots(request):
    if settings.SITE_NOINDEX:
        body = 'User-agent: *\nDisallow: /\n'
    else:
        body = 'User-agent: *\n' + ''.join(f'Disallow: {path}\n' for path in PRIVATE)
        body += f'Sitemap: {origin(request)}/sitemap.xml\n'
    return HttpResponse(body, content_type='text/plain')

@require_safe
def sitemap(request):
    root = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    paths = [('/', None), (reverse('shop:contact'), None), (reverse('shop:about'), None)]
    paths.extend((p.get_absolute_url(), p.updated_at) for p in Product.objects.filter(is_active=True, variant_family__isnull=True).only('slug', 'updated_at'))
    categories = {c.pk: c for c in Category.objects.all()}
    for category in categories.values():
        node, seen, active = category, set(), True
        while node:
            if not node.is_active or node.pk in seen:
                active = False
                break
            seen.add(node.pk)
            node = categories.get(node.parent_id)
        if active:
            paths.append((category.get_absolute_url(), category.updated_at))
    for path, modified in paths:
        url = SubElement(root, 'url')
        SubElement(url, 'loc').text = origin(request) + path
        if modified:
            SubElement(url, 'lastmod').text = modified.date().isoformat()
    return HttpResponse(tostring(root, encoding='utf-8', xml_declaration=True), content_type='application/xml')

@lru_cache(maxsize=2)
def _redirects(path, stamp):
    return json.loads(Path(path).read_text(encoding='utf-8'))

@require_safe
def legacy(request, **kwargs):
    if 'variant' in request.GET or 'variant_id' in request.GET:
        raise Http404('Legacy variant mapping requires verification')
    path = Path(settings.BASE_DIR) / 'catalog_review' / 'seo_redirects.json'
    try:
        mappings = _redirects(str(path), path.stat().st_mtime_ns)
        old = request.path.rstrip('/')
        target = mappings.get(old)
        parts = old.split('/')
        if not target and len(parts) == 5 and parts[1] == 'collections' and parts[3] == 'products' and '/collections/'+parts[2] in mappings:
            target = mappings.get('/products/'+parts[4])
    except (OSError, ValueError):
        target = None
    if not target or not target.startswith(('/product/', '/category/')) or '//' in target or '\\' in target:
        raise Http404
    # Resolve an active destination now, not just when the evidence was exported.
    from django.urls import resolve
    match = resolve(target)
    if match.url_name == 'product_detail':
        if not Product.objects.filter(slug=match.kwargs['product_slug'], is_active=True).exists():
            raise Http404
    elif match.url_name == 'category_detail':
        category = Category.objects.filter(slug=match.kwargs['category_slug'], is_active=True).first()
        if not category or any(not c.is_active for c in category.get_ancestors()):
            raise Http404
    else:
        raise Http404
    return HttpResponsePermanentRedirect(target)

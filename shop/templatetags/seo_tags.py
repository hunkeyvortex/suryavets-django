import json
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags
from shop.seo import origin

register = template.Library()

@register.simple_tag(takes_context=True)
def seo_metadata(context):
    request = context['request']
    base = origin(request)
    product, category = context.get('product'), context.get('category')
    path = product.get_absolute_url() if product else request.path
    if not product and request.GET.get('page', '').isdigit() and int(request.GET['page']) > 1:
        path += '?page=' + request.GET['page']
    canonical = base + path
    item = product or category
    title = ((getattr(item, 'meta_title', '') or item.name) + ' | SuryaVets') if item else 'SuryaVets'
    description = strip_tags(getattr(item, 'meta_description', '') or getattr(item, 'short_description', '') or getattr(item, 'description', ''))[:300]
    tags = format_html('<link rel="canonical" href="{}"><meta property="og:url" content="{}"><meta property="og:title" content="{}"><meta property="og:description" content="{}"><meta property="og:type" content="{}"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="{}">', canonical, canonical, title, description, 'product' if product else 'website', title)
    graph = []
    if request.path == '/':
        graph += [{'@type': 'Organization', 'name': 'SuryaVets', 'url': base}, {'@type': 'WebSite', 'name': 'SuryaVets', 'url': base}]
    if product:
        data = {'@type': 'Product', 'name': product.name, 'url': canonical, 'description': description}
        selected = context.get('selected_variant') or product
        if selected.sku:
            data['sku'] = selected.sku
        photo = context.get('gallery_primary')
        if photo:
            image = photo.display_url
            image = base + image if image.startswith('/') else image
            data['image'] = image
            tags += format_html('<meta property="og:image" content="{}">', image)
        price = context.get('display_price')
        if price and price > 0 and context.get('buying_in_stock') and not context.get('selection_error'):
            data['offers'] = {'@type': 'Offer', 'priceCurrency': 'INR', 'price': str(price), 'url': canonical,
                'availability': 'https://schema.org/InStock' if context.get('buying_in_stock') else 'https://schema.org/OutOfStock'}
        graph.append(data)
        category = product.category
    if category:
        crumbs = [{'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': base + '/'}]
        for node in [*category.get_ancestors(), category]:
            crumbs.append({'@type': 'ListItem', 'position': len(crumbs)+1, 'name': node.name, 'item': base+node.get_absolute_url()})
        if product:
            crumbs.append({'@type': 'ListItem', 'position': len(crumbs)+1, 'name': product.name, 'item': canonical})
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': crumbs})
    if graph:
        payload = json.dumps({'@context': 'https://schema.org', '@graph': graph}).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        tags += format_html('<script type="application/ld+json">{}</script>', mark_safe(payload))
    return tags

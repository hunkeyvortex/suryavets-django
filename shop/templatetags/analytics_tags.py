from django import template
from django.conf import settings
from django.utils.html import json_script

register = template.Library()

@register.simple_tag(takes_context=True)
def commerce_events(context):
    if not settings.ANALYTICS_EVENTS_ENABLED:
        return ''
    request = context['request']
    route = getattr(request.resolver_match, 'url_name', '')
    events = []
    pending = request.session.pop('commerce_event', None)
    if pending:
        events.append(pending)
    product = context.get('product')
    if product and route == 'product_detail':
        variant = context.get('selected_variant')
        events.append({'event': 'view_item', 'item_id': str(product.pk), 'variant_id': variant.pk if variant else None})
    if route == 'checkout':
        events.append({'event': 'begin_checkout'})
    order = context.get('order')
    if order and route == 'order_confirmation' and (order.payment_status == 'paid' or order.payment_method == 'cod') and order.status != 'cancelled':
        events.append({'event': 'purchase', 'transaction_id': str(order.pk), 'currency': 'INR', 'value': str(order.total)})
    return json_script(events, 'surya-commerce-events')

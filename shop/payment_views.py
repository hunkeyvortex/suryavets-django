import hashlib
import hmac
import json
import re
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Order, PaymentAttempt
from .services.cart import get_cart
from .services.payments import PaymentError, enabled, initialize, verify_signature, verify_captured


def owned_order(request, pk):
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user)
    else:
        cart = get_cart(request, create=False)
        orders = Order.objects.filter(user__isnull=True, checkout_cart=cart) if cart else Order.objects.none()
    return get_object_or_404(orders, pk=pk)


@never_cache
def payment(request, order_id):
    order = owned_order(request, order_id)
    if order.payment_status == 'paid' or order.payment_method != 'online':
        return redirect('shop:order_confirmation', order_id=order.pk)
    error = ''
    attempt = get_object_or_404(PaymentAttempt, order=order)
    if request.method == 'POST':
        try:
            if request.POST.get('action') == 'verify':
                if request.POST.get('razorpay_order_id') != attempt.gateway_order_id:
                    raise PaymentError('Payment order mismatch.')
                payment_id = request.POST.get('razorpay_payment_id', '')
                verify_signature(attempt.gateway_order_id, payment_id, request.POST.get('razorpay_signature'))
                verify_captured(attempt.pk, payment_id)
                return redirect('shop:order_confirmation', order_id=order.pk)
            initialize(order)
        except PaymentError as problem:
            error = str(problem)
        attempt.refresh_from_db()
    return render(request, 'payment.html', {'order': order, 'attempt': attempt, 'payment_error': error,
        'verification': request.POST if request.POST.get('action') == 'verify' and error else None,
        'gateway_ready': enabled() and attempt.state == 'ready',
        'gateway_options': {'key': settings.RAZORPAY_KEY_ID, 'order_id': attempt.gateway_order_id,
            'amount': attempt.amount, 'currency': attempt.currency, 'name': 'SuryaVets',
            'description': order.order_number, 'theme': {'color': '#009b51'}}})


@csrf_exempt  # Gateway cannot carry a browser CSRF token; raw-body HMAC is mandatory.
@require_POST
def webhook(request):
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not enabled() or not secret or len(request.body) > 1000000:
        return HttpResponse(status=503)
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    signature = request.headers.get('X-Razorpay-Signature', '')
    if not re.fullmatch(r'[0-9a-f]{64}', signature) or not hmac.compare_digest(expected, signature):
        return HttpResponse(status=400)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return HttpResponse(status=400)
        if data.get('event') != 'payment.captured':
            return HttpResponse(status=200)
        entity = data['payload']['payment']['entity']
        attempt = PaymentAttempt.objects.filter(gateway_order_id=entity['order_id']).first()
        if not attempt:
            return HttpResponse(status=200)  # A different store's event must not change this DB.
        verify_captured(attempt.pk, entity['id'])
    except (ValueError, TypeError, KeyError):
        return HttpResponse(status=400)
    except PaymentError:
        return HttpResponse(status=503)  # Retryable; no fake acknowledgement of captured state.
    return HttpResponse(status=200)

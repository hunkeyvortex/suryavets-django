"""Razorpay TEST-only adapter. Browser claims never prove a captured payment."""
import base64
import hashlib
import hmac
import json
import re
from urllib.request import Request, urlopen
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shop.models import Order, PaymentAttempt


class PaymentError(Exception):
    pass


def enabled():
    return bool(settings.RAZORPAY_ENABLED and settings.RAZORPAY_KEY_ID.startswith('rzp_test_') and settings.RAZORPAY_KEY_SECRET)


def api(path, payload=None):
    if not enabled():
        raise PaymentError('Test payments are not configured. No payment has been confirmed.')
    token = base64.b64encode(f'{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}'.encode()).decode()
    request = Request('https://api.razorpay.com/v1/' + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization': 'Basic ' + token, 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read(1000000))
    except Exception:
        raise PaymentError('The payment service could not be reached. Please retry verification later; do not pay again.') from None


def identifier(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r'_[A-Za-z0-9]{1,80}', value):
        raise PaymentError('Invalid payment reference.')
    return value


def initialize(order):
    if not enabled():
        raise PaymentError('Razorpay test payments are not configured.')
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        attempt = PaymentAttempt.objects.select_for_update().get(order=locked)
        if locked.status != 'awaiting_payment' or locked.payment_status != 'pending':
            raise PaymentError('This order is not awaiting payment.')
        if attempt.state == 'ready':
            return attempt
        if not PaymentAttempt.objects.filter(pk=attempt.pk, state='new').update(state='creating'):
            raise PaymentError('Payment setup is awaiting reconciliation. Please contact support; do not start another checkout.')
    # The durable claim prevents retrying an uncertain upstream create request.
    try:
        result = api('orders', {'amount': attempt.amount, 'currency': 'INR', 'receipt': locked.order_number})
        gateway_id = identifier(result.get('id'), 'order')
        if result.get('amount') != attempt.amount or result.get('currency') != 'INR' or result.get('receipt') != locked.order_number:
            raise PaymentError('Gateway order details did not match this checkout.')
        attempt.gateway_order_id, attempt.state = gateway_id, 'ready'
        attempt.save(update_fields=['gateway_order_id', 'state'])
    except Exception:
        PaymentAttempt.objects.filter(pk=attempt.pk, state='creating').update(state='uncertain')
        raise PaymentError('Payment setup needs reconciliation. Contact support before trying another payment.') from None
    return attempt


def verify_signature(order_id, payment_id, signature):
    if not enabled():
        raise PaymentError('Test payment verification is unavailable.')
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f'{order_id}|{payment_id}'.encode(), hashlib.sha256).hexdigest()
    if not isinstance(signature, str) or not re.fullmatch(r'[0-9a-f]{64}', signature) or not hmac.compare_digest(expected, signature):
        raise PaymentError('Payment verification failed. No payment has been confirmed.')


def verify_captured(attempt_id, payment_id):
    attempt = PaymentAttempt.objects.select_related('order').get(pk=attempt_id)
    payment_id = identifier(payment_id, 'pay')
    gateway_order_id = identifier(attempt.gateway_order_id, 'order')
    payment = api('payments/' + payment_id)
    gateway_order = api('orders/' + gateway_order_id)
    if not isinstance(payment, dict) or not isinstance(gateway_order, dict):
        raise PaymentError('Invalid gateway response. Please retry verification later.')
    if (payment.get('id') != payment_id or payment.get('order_id') != gateway_order_id
            or payment.get('status') != 'captured' or payment.get('captured') is not True
            or payment.get('amount') != attempt.amount or payment.get('currency') != attempt.currency
            or gateway_order.get('id') != gateway_order_id or gateway_order.get('status') != 'paid'
            or gateway_order.get('amount_paid') != attempt.amount or gateway_order.get('amount') != attempt.amount
            or gateway_order.get('currency') != attempt.currency):
        raise PaymentError('Payment is not yet verified as captured for this order. Please check again; do not pay again.')
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=attempt.order_id)
        attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.state == 'paid':
            if attempt.gateway_payment_id != payment_id:
                raise PaymentError('An additional payment requires staff reconciliation.')
            return order
        if order.status != 'awaiting_payment' or order.payment_status != 'pending' or attempt.state != 'ready':
            raise PaymentError('This payment requires staff reconciliation.')
        attempt.state, attempt.gateway_payment_id, attempt.verified_at = 'paid', payment_id, timezone.now()
        attempt.save(update_fields=['state', 'gateway_payment_id', 'verified_at'])
        order.status, order.payment_status, order.payment_reference = 'pending', 'paid', payment_id
        order.save(update_fields=['status', 'payment_status', 'payment_reference', 'updated_at'])
        from .order_tracking import record_event
        record_event(order, 'paid', kind='payment')
        record_event(order, 'pending')
    return order

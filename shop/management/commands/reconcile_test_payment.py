"""Explicit reconciliation; never creates a second gateway order or marks unpaid money paid."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from shop.models import Order, PaymentAttempt
from shop.services.payments import api, enabled, identifier, verify_captured, PaymentError


class Command(BaseCommand):
    help = 'Bind a verified existing Razorpay TEST order after an uncertain create, and/or recheck a captured payment.'

    def add_arguments(self, parser):
        parser.add_argument('order_number')
        parser.add_argument('--gateway-order-id', required=True)
        parser.add_argument('--payment-id')

    def handle(self, *args, **options):
        try:
            if not enabled():
                raise PaymentError('Test gateway configuration is required.')
            gateway_id = identifier(options['gateway_order_id'], 'order')
            remote = api('orders/' + gateway_id)
            with transaction.atomic():
                order = Order.objects.select_for_update().get(order_number=options['order_number'])
                attempt = PaymentAttempt.objects.select_for_update().get(order=order)
                if (remote.get('id') != gateway_id or remote.get('receipt') != order.order_number
                        or remote.get('amount') != attempt.amount or remote.get('currency') != attempt.currency):
                    raise PaymentError('Gateway receipt/amount/currency mismatch. Nothing was changed.')
                if attempt.gateway_order_id and attempt.gateway_order_id != gateway_id:
                    raise PaymentError('A different gateway order is already bound.')
                if attempt.state in ('creating', 'uncertain'):
                    attempt.gateway_order_id, attempt.state = gateway_id, 'ready'
                    attempt.save(update_fields=['gateway_order_id', 'state'])
                elif attempt.state not in ('ready', 'paid'):
                    raise PaymentError('This attempt is not eligible for reconciliation.')
            if options['payment_id']:
                verify_captured(attempt.pk, options['payment_id'])
            self.stdout.write('Existing gateway attempt reconciled. No additional payment was created.')
        except (Order.DoesNotExist, PaymentAttempt.DoesNotExist, PaymentError) as error:
            raise CommandError(str(error)) from None

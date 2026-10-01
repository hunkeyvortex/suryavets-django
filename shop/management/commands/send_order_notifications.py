"""Explicit outbox worker. Disabled by default; no page-save email side effects."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from shop.services.notifications import deliver_pending
from shop.models import OrderNotification


class Command(BaseCommand):
    help = 'Deliver pending email order events only when ORDER_EMAIL_ENABLED is true.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--dry-run', action='store_true')
        scope = parser.add_mutually_exclusive_group()
        scope.add_argument('--notification-id', type=int, help='Process only this pending notification.')
        scope.add_argument('--retry-failed', type=int, help='Retry a confirmed rejection after fixing its cause; never an uncertain send.')

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(f"Pending email notifications: {OrderNotification.objects.filter(state='pending', channel='email').count()}. No sends or state changes.")
            return
        if not getattr(settings, 'ORDER_EMAIL_ENABLED', False):
            raise CommandError('Order email delivery is disabled. Configure a verified email backend before enabling it.')
        notification_id = options['notification_id'] or options['retry_failed']
        if options['retry_failed']:
            claimed = OrderNotification.objects.filter(pk=notification_id, channel='email', state='failed',
                retryable=True, attempts__lt=settings.ORDER_EMAIL_MAX_ATTEMPTS).update(state='pending', next_attempt_at=None)
            if not claimed:
                raise CommandError('Not retryable: unknown outcomes, previews, accepted messages and exhausted attempts cannot be replayed.')
        if notification_id and not OrderNotification.objects.filter(pk=notification_id).exists():
            raise CommandError('Notification not found.')
        deliver_pending(notification_id=notification_id, limit=options['limit'])
        self.stdout.write('Outbox processed. Inspect notification state/message ID; acceptance is not proof of inbox delivery.')
        if notification_id:
            row = OrderNotification.objects.get(pk=notification_id)
            self.stdout.write(f'Notification {row.pk}: {row.state}; attempts={row.attempts}; error={row.error or "none"}')

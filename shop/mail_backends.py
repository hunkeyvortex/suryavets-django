"""Small Brevo transactional API backend; business code uses Django email messages."""
import json
import ssl
import truststore
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.validators import validate_email


class DeliveryError(Exception):
    def __init__(self, code, *, retryable=False, retry_after=None):
        # Only static codes/status numbers: never retain provider response bodies or keys.
        super().__init__(code)
        self.retryable, self.retry_after = retryable, retry_after


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never forward API credentials to another location.


def post_email(payload):
    if not settings.BREVO_API_KEY:
        raise DeliveryError('brevo_missing_key', retryable=True)
    request = Request('https://api.brevo.com/v3/smtp/email', data=json.dumps(payload).encode('utf-8'),
        headers={'api-key': settings.BREVO_API_KEY, 'Accept':'application/json', 'Content-Type':'application/json'})
    try:
        # Use the same native certificate validation as the existing media importer.
        # Hostname/CA validation stays enabled; never bypass TLS for API credentials.
        with build_opener(NoRedirect(), HTTPSHandler(context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))).open(request, timeout=settings.BREVO_TIMEOUT) as response:
            status = response.status
            result = json.loads(response.read(65536))
    except HTTPError as error:
        # 408/5xx might follow acceptance. Never automatically replay ambiguous outcomes.
        status = error.code
        delay = None
        if status == 429:
            try: delay = min(86400, max(60, int(error.headers.get('Retry-After', '60'))))
            except (TypeError, ValueError): delay = 60
        # duplicate_parameter may be returned with 400. Treat every 400 as review-required.
        raise DeliveryError(f'brevo_http_{status}', retryable=status in (401,403,404,422,429), retry_after=delay) from None
    except URLError as error:
        if isinstance(error.reason, ssl.SSLCertVerificationError):
            raise DeliveryError('brevo_tls_verification_failed', retryable=True) from None
        raise DeliveryError('brevo_outcome_unknown') from None
    except Exception:
        raise DeliveryError('brevo_outcome_unknown') from None
    message_id = result.get('messageId') if isinstance(result, dict) else None
    if status != 201 or not isinstance(message_id, str) or not 1 <= len(message_id) <= 255 or '\n' in message_id or '\r' in message_id:
        raise DeliveryError('brevo_response_unconfirmed')
    return message_id


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            try:
                sender_name, sender_email = parseaddr(message.from_email or '')
                validate_email(sender_email)
                if len(message.to) != 1 or message.cc or message.bcc or message.attachments:
                    raise ValueError('Unsupported transactional message shape')
                recipient_name, recipient_email = parseaddr(message.to[0])
                validate_email(recipient_email)
                html = next((a.content for a in message.alternatives if a.mimetype == 'text/html'), '')
                if not html or not message.body or '\r' in message.subject or '\n' in message.subject:
                    raise ValueError('Missing content or invalid subject')
                payload = {'sender':{'email':sender_email, 'name':sender_name or settings.DEFAULT_FROM_NAME},
                    'to':[{'email':recipient_email, 'name':recipient_name or recipient_email}],
                    'subject':message.subject, 'htmlContent':html, 'textContent':message.body,
                    'headers':{'X-Mailin-custom':getattr(message, 'notification_reference', 'suryavets-test')}}
                if hasattr(message, 'idempotency_key'):
                    payload['headers']['idempotencyKey'] = message.idempotency_key
                if settings.BREVO_SANDBOX:
                    payload['headers']['X-Sib-Sandbox'] = 'drop'
            except Exception:
                raise DeliveryError('brevo_invalid_message', retryable=True) from None
            message.provider_message_id = post_email(payload)
            message.delivery_sandbox = settings.BREVO_SANDBOX
            sent += 1
        return sent

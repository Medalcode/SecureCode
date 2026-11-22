"""Minimal transactional-email adapter for Resend.

The adapter deliberately uses the HTTPS API directly so the production image
does not need another SDK dependency.  It accepts only fully rendered email
content; templates and account-token policy remain in the API layer.
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EmailDeliveryError(RuntimeError):
    """Raised when the configured provider cannot accept an email."""


def _bounded_timeout() -> int:
    try:
        return min(max(int(os.environ.get("RESEND_TIMEOUT_SECONDS", "10")), 1), 30)
    except ValueError:
        return 10


def send_resend_email(*, to: str, subject: str, html: str, text: str, idempotency_key: str) -> None:
    """Submit a transactional message to Resend without logging secrets.

    ``RESEND_API_KEY`` and ``RESEND_FROM_EMAIL`` are injected at runtime from
    Secret Manager.  Resend supports an Idempotency-Key header, which prevents
    a retry of the same token email from generating duplicate deliveries.
    """
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("RESEND_FROM_EMAIL", "").strip()
    if not api_key or not sender:
        raise EmailDeliveryError("Transactional email is not configured")

    payload = json.dumps({
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }).encode("utf-8")
    request = Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        },
    )
    try:
        with urlopen(request, timeout=_bounded_timeout()) as response:
            if not 200 <= response.status < 300:
                raise EmailDeliveryError("Transactional email provider rejected the request")
    except (HTTPError, URLError, TimeoutError) as error:
        raise EmailDeliveryError("Transactional email delivery failed") from error

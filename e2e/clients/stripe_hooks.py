"""Construct and HMAC-sign Stripe webhook events for offline delivery.

stripe-mock is stateless and never delivers webhooks, so the suite builds the
event JSON itself and signs it with the test signing secret using Stripe's
documented `t=<ts>,v1=<hmac>` scheme.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx


def signed_headers(payload: bytes, secret: str) -> dict[str, str]:
    """Return the Stripe-Signature header for a raw payload."""
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode() + payload
    signature = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={timestamp},v1={signature}"}


def send_event(
    client: httpx.Client, path: str, event: dict, *, secret: str
) -> httpx.Response:
    """POST a signed event to a webhook endpoint and return the response."""
    payload = json.dumps(event).encode()
    headers = {"Content-Type": "application/json", **signed_headers(payload, secret)}
    return client.post(path, content=payload, headers=headers)


def checkout_completed(session_id: str, metadata: dict[str, str]) -> dict[str, Any]:
    """Build a checkout.session.completed event carrying handler metadata."""
    return {
        "id": f"evt_{session_id}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "payment_status": "paid",
                "status": "complete",
                "metadata": metadata,
            }
        },
    }

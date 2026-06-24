"""Activate an owner subscription via a signed Stripe webhook (offline).

stripe-mock never delivers webhooks, so the suite signs a
``customer.subscription.updated`` event itself to move the owner's subscription
to ACTIVE — the state properties-ms requires before an owner may add listings.
"""

from __future__ import annotations

import time
import uuid

import httpx

from e2e import config
from e2e.clients import stripe_hooks


def activate_subscription(
    client: httpx.Client, owner_id: str, plan_slug: str = "enterprise"
) -> None:
    """Drive the owner's subscription to ACTIVE so they can create listings.

    Sends the same ``customer.subscription.updated`` event Stripe would emit,
    carrying the ``owner_id``/``plan_slug`` metadata payments-ms reads to upsert
    the subscription record. ``enterprise`` has unlimited listings by default.
    """
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": f"sub_{uuid.uuid4().hex[:24]}",
                "object": "subscription",
                "customer": f"cus_{uuid.uuid4().hex[:24]}",
                "status": "active",
                "cancel_at_period_end": False,
                "current_period_end": int(time.time()) + 30 * 24 * 3600,
                "metadata": {"owner_id": owner_id, "plan_slug": plan_slug},
            }
        },
    }
    resp = stripe_hooks.send_event(
        client, "/payments/webhook", event, secret=config.STRIPE_WEBHOOK_SECRET
    )
    resp.raise_for_status()

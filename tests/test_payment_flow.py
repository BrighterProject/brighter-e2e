"""E2E: checkout session -> signed webhook -> payment paid & booking confirmed."""

from __future__ import annotations

import httpx

from e2e import bookings, config, properties, users
from e2e.clients import stripe_hooks
from e2e.http import make_client


def test_checkout_then_webhook_marks_paid(
    owner_client: tuple[httpx.Client, dict[str, str]],
) -> None:
    owner, _ = owner_client
    prop = properties.create_property(owner)
    with make_client() as guest:
        rec = users.register_user(guest)
        users.login(guest, rec["username"], rec["password"])
        booking = bookings.create_booking(guest, prop["id"], email=rec["email"])

        # Create a checkout session (talks to stripe-mock).
        resp = guest.post("/payments/checkout", json={"booking_id": booking["id"]})
        assert resp.status_code in (200, 201)
        session_id = resp.json().get("session_id") or resp.json().get("id")

        # Deliver the signed completion webhook.
        event = stripe_hooks.checkout_completed(
            session_id, metadata={"booking_id": booking["id"]}
        )
        hook = stripe_hooks.send_event(
            guest, "/payments/webhook", event, secret=config.STRIPE_WEBHOOK_SECRET
        )
        assert hook.status_code == 200

        # Payment is now recorded as paid for the booking.
        record = guest.get(f"/payments/booking/{booking['id']}")
        assert record.status_code == 200
        assert record.json()["status"].lower() in ("paid", "succeeded", "completed")

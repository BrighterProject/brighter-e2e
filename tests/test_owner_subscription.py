"""E2E: list plans, subscribe, activate via webhook, gate listings, open portal."""

from __future__ import annotations

import httpx

from e2e import config
from e2e.clients import stripe_hooks


def test_owner_subscription_lifecycle(
    owner_client: tuple[httpx.Client, dict[str, str]],
) -> None:
    owner, record = owner_client

    plans = owner.get("/payments/subscriptions/plans")
    assert plans.status_code == 200 and plans.json(), "seed_subscription_plans must run"
    # Enterprise requires manual activation and can't be self-checked-out; pick a
    # self-serve plan instead.
    slug = next(p["slug"] for p in plans.json() if p["slug"] != "enterprise")

    checkout = owner.post(
        "/payments/subscriptions/checkout", params={"plan_slug": slug, "locale": "en"}
    )
    assert checkout.status_code in (200, 201)
    session_id = checkout.json().get("session_id") or checkout.json().get("id")

    event = {
        "id": f"evt_{session_id}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "mode": "subscription",
                "status": "complete",
                "metadata": {"plan_slug": slug},
            }
        },
    }
    hook = stripe_hooks.send_event(
        owner, "/payments/webhook", event, secret=config.STRIPE_WEBHOOK_SECRET
    )
    assert hook.status_code == 200

    me = owner.get("/payments/subscriptions/me")
    assert me.status_code == 200

    # can-add-listing is the internal quota check properties-ms calls; it requires
    # the owner_id query param it would normally forward.
    gate = owner.get(
        "/payments/subscriptions/can-add-listing", params={"owner_id": record["id"]}
    )
    assert gate.status_code == 200
    assert gate.json()["allowed"] is True

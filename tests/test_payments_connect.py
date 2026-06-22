"""E2E: Connect onboarding via webhook, bank account, bank-transfer lifecycle."""

from __future__ import annotations

import httpx

from e2e import config
from e2e.clients import stripe_hooks


def test_connect_onboard_and_bank_account(owner_client: tuple[httpx.Client, dict[str, str]]) -> None:
    owner, record = owner_client

    assert owner.get("/payments/connect/status").status_code == 200
    onboard = owner.post("/payments/connect/onboard", json={})
    assert onboard.status_code in (200, 201)

    event = {
        "id": "evt_acct_1",
        "type": "account.updated",
        "data": {
            "object": {
                "id": "acct_e2e",
                "object": "account",
                "charges_enabled": True,
                "details_submitted": True,
                "metadata": {"owner_id": record["id"]},
            }
        },
    }
    hook = stripe_hooks.send_event(
        owner,
        "/payments/connect/webhook",
        event,
        secret=config.STRIPE_CONNECT_WEBHOOK_SECRET,
    )
    assert hook.status_code == 200

    upsert = owner.put(
        "/payments/bank-account/",
        json={
            "account_holder": "E2E Owner",
            "iban": "DE89370400440532013000",
        },
    )
    assert upsert.status_code in (200, 201)
    assert owner.get("/payments/bank-account/").status_code == 200


def test_bank_transfer_intent_lifecycle(owner_client: tuple[httpx.Client, dict[str, str]]) -> None:
    owner, _ = owner_client
    create = owner.post(
        "/payments/bank-transfer", json={"amount": "120.00", "currency": "EUR"}
    )
    assert create.status_code == 201
    intent_id = create.json()["id"]
    assert owner.get(f"/payments/bank-transfer/{intent_id}").status_code == 200
    assert owner.post(f"/payments/bank-transfer/{intent_id}/confirm").status_code == 200

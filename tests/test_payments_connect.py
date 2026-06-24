"""E2E: Connect status/onboarding, owner bank account, bank-transfer lifecycle."""

from __future__ import annotations

import httpx
import pytest

from e2e import bookings, properties


def test_connect_status_and_bank_account(
    owner_client: tuple[httpx.Client, dict[str, str]],
) -> None:
    """The Connect surface that stripe-mock can serve: status + bank account CRUD."""
    owner, _ = owner_client

    assert owner.get("/payments/connect/status").status_code == 200

    upsert = owner.put(
        "/payments/bank-account/",
        json={
            "account_holder": "E2E Owner",
            "iban": "DE89370400440532013000",
        },
    )
    assert upsert.status_code in (200, 201)
    assert owner.get("/payments/bank-account/").status_code == 200

    # Upsert is idempotent: a second PUT updates the existing row, not 500s.
    update = owner.put(
        "/payments/bank-account/",
        json={
            "account_holder": "E2E Owner Renamed",
            "iban": "DE89370400440532013000",
        },
    )
    assert update.status_code in (200, 201)


@pytest.mark.xfail(
    reason=(
        "Connect onboarding uses the Stripe Accounts v2 API "
        "(stripe>=15.2 v2.core.accounts), which stripe-mock v0.201.0 does not "
        "emulate (POST /v2/core/accounts -> 404). The code path is correct "
        "against real Stripe; this xpasses once stripe-mock adds v2 support."
    ),
    strict=False,
)
def test_connect_onboard_via_stripe_v2(
    owner_client: tuple[httpx.Client, dict[str, str]],
) -> None:
    owner, _ = owner_client
    onboard = owner.post("/payments/connect/onboard", json={})
    assert onboard.status_code in (200, 201)
    assert onboard.json()["redirect_url"]


def test_bank_transfer_intent_lifecycle(
    owner_client: tuple[httpx.Client, dict[str, str]],
) -> None:
    owner, _ = owner_client
    # The intent derives amount/currency from a pending booking that was created
    # with bank_transfer as its payment method; the owner books their own listing
    # so they are both the booking's user and the property owner (who confirms).
    # The intent requires the owner to have bank details on file.
    assert owner.put(
        "/payments/bank-account/",
        json={"account_holder": "E2E Owner", "iban": "DE89370400440532013000"},
    ).status_code in (200, 201)
    prop = properties.create_property(owner)
    booking = bookings.create_booking(owner, prop["id"], payment_method="bank_transfer")

    create = owner.post("/payments/bank-transfer", json={"booking_id": booking["id"]})
    assert create.status_code == 201
    intent_id = create.json()["id"]
    assert owner.get(f"/payments/bank-transfer/{intent_id}").status_code == 200
    assert owner.post(f"/payments/bank-transfer/{intent_id}/confirm").status_code == 200

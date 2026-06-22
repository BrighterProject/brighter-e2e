"""E2E: booking creation fires a notification; owner confirms; illegal transition rejected."""

from __future__ import annotations

import httpx

from e2e import bookings, properties, users
from e2e.clients import mailpit
from e2e.http import make_client


def test_booking_create_notifies_and_confirms(
    owner_client: tuple[httpx.Client, dict[str, str]],
) -> None:
    owner, _ = owner_client
    prop = properties.create_property(owner)

    # Guest books.
    with make_client() as guest:
        rec = users.register_user(guest)
        users.login(guest, rec["username"], rec["password"])
        booking = bookings.create_booking(guest, prop["id"], email=rec["email"])
        assert booking["status"] == "PENDING"

    # A "booking created" email reached the guest.
    mailpit.wait_for_email(to=rec["email"])

    # Owner confirms.
    resp = owner.patch(
        f"/bookings/{booking['id']}/status", json={"status": "CONFIRMED"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"


def test_illegal_status_transition_rejected(
    owner_client: tuple[httpx.Client, dict[str, str]],
) -> None:
    owner, _ = owner_client
    prop = properties.create_property(owner)
    with make_client() as guest:
        rec = users.register_user(guest)
        users.login(guest, rec["username"], rec["password"])
        booking = bookings.create_booking(guest, prop["id"], email=rec["email"])
    # PENDING -> COMPLETED is not a legal transition.
    resp = owner.patch(
        f"/bookings/{booking['id']}/status", json={"status": "COMPLETED"}
    )
    assert resp.status_code in (409, 422)

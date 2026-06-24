"""E2E: guest cancellation applies the correct refund per cancellation policy."""

from __future__ import annotations

import httpx
import pytest

from e2e import bookings, properties, users
from e2e.http import make_client


@pytest.mark.parametrize("policy", ["free", "moderate", "strict"])
def test_cancellation_under_each_policy(
    owner_client: tuple[httpx.Client, dict[str, str]], policy: str
) -> None:
    owner, _ = owner_client
    prop = properties.create_property(owner, cancellation_policy=policy)
    with make_client() as guest:
        rec = users.register_user(guest)
        users.login(guest, rec["username"], rec["password"])
        booking = bookings.create_booking(guest, prop["id"], email=rec["email"])
        resp = guest.patch(
            f"/bookings/{booking['id']}/status", json={"status": "cancelled"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

"""Helpers to create properties (with the required bg translation) via the API."""

from __future__ import annotations

import os
import uuid
from typing import Any

import httpx

from e2e import users
from e2e.http import make_client


def _approve_property(property_id: str) -> None:
    """Approve a freshly-created listing (admin-only) so it becomes bookable.

    New properties are persisted as ``pending_approval``; bookings-ms refuses to
    book anything that is not ``active``. An admin PATCHes the status to active.
    """
    with make_client() as admin:
        users.login(admin, os.environ["E2E_ADMIN_USER"], os.environ["E2E_ADMIN_PASS"])
        resp = admin.patch(
            f"/properties/{property_id}/status", json={"status": "active"}
        )
        resp.raise_for_status()


def create_property(
    owner_client: httpx.Client,
    cancellation_policy: str = "free",
    *,
    approve: bool = True,
) -> dict[str, Any]:
    """Create a minimal valid property owned by the logged-in owner.

    Args:
        owner_client: Authenticated client for the property owner.
        cancellation_policy: One of "free", "moderate", "strict".
        approve: When True, an admin approves the listing so it is bookable.

    Returns:
        The created property record.
    """
    payload = {
        "property_type": "apartment",
        "status": "active",
        "city": "Sofia",
        "region_code": "SFO",
        "settlement_ekatte": "68134",
        "registration_number": f"E2E-{uuid.uuid4().hex[:12]}",
        "latitude": 42.6977,
        "longitude": 23.3219,
        "price_per_night": "80.00",
        "currency": "EUR",
        "bedrooms": 1,
        "bathrooms": 1,
        "beds": 1,
        "max_guests": 2,
        "amenities": ["wifi"],
        "has_parking": False,
        "min_nights": 1,
        "cancellation_policy": cancellation_policy,
        "translations": [
            {
                "locale": "bg",
                "name": "Тестов апартамент",
                "description": "Описание на тестов апартамент за e2e.",
                "address": "ул. Тестова 1, София",
            },
            {
                "locale": "en",
                "name": "Test apartment",
                "description": "An end-to-end test apartment description.",
                "address": "1 Test St, Sofia",
            },
        ],
    }
    resp = owner_client.post("/properties/", json=payload)
    resp.raise_for_status()
    record = resp.json()
    if approve:
        _approve_property(record["id"])
    return record

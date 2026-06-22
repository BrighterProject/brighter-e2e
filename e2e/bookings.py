"""Helper to create a booking via the API."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx


def create_booking(
    client: httpx.Client, property_id: str, *, nights: int = 2, email: str = "guest@example.test"
) -> dict[str, Any]:
    """Create a booking starting tomorrow for `nights` nights."""
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=nights)
    payload = {
        "property_id": property_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "guest_name": "E2E Guest",
        "guest_email": email,
        "guest_phone": "+359888000000",
    }
    resp = client.post("/bookings/", json=payload)
    resp.raise_for_status()
    return resp.json()

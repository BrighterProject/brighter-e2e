"""Helpers to create properties (with the required bg translation) via the API."""

from __future__ import annotations

import httpx


def create_property(owner_client: httpx.Client) -> dict:
    """Create a minimal valid property owned by the logged-in owner."""
    payload = {
        "property_type": "apartment",
        "status": "active",
        "city": "Sofia",
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
        "cancellation_policy": "free",
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
    resp = owner_client.post("/properties", json=payload)
    resp.raise_for_status()
    return resp.json()

"""E2E: owner creates a property, public read reflects it, then deletes."""

from __future__ import annotations

from e2e import properties


def test_property_create_read_delete(owner_client, anon_client):
    client, _ = owner_client
    created = properties.create_property(client)
    prop_id = created["id"]

    # Public read reflects it and carries cache headers.
    public = anon_client.get(f"/properties/{prop_id}")
    assert public.status_code == 200
    assert "cache-control" in {k.lower() for k in public.headers}

    # Owner can delete it.
    assert client.delete(f"/properties/{prop_id}").status_code in (200, 204)
    assert anon_client.get(f"/properties/{prop_id}").status_code == 404


def test_property_requires_bg_translation(owner_client):
    client, _ = owner_client
    bad = {
        "property_type": "apartment",
        "status": "active",
        "city": "Sofia",
        "price_per_night": "80.00",
        "currency": "EUR",
        "bedrooms": 1,
        "bathrooms": 1,
        "beds": 1,
        "max_guests": 2,
        "cancellation_policy": "free",
        "translations": [
            {
                "locale": "en",
                "name": "Only English",
                "description": "Missing the required bg translation here.",
                "address": "1 Test St",
            }
        ],
    }
    assert client.post("/properties", json=bad).status_code == 422

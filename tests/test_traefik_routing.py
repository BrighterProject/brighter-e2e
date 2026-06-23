"""E2E: Traefik public/protected routing and scope enforcement."""

from __future__ import annotations

import httpx

from e2e import users


def test_public_properties_needs_no_auth(anon_client: httpx.Client) -> None:
    assert anon_client.get("/properties/").status_code == 200


def test_options_preflight_passes_without_auth(anon_client: httpx.Client) -> None:
    resp = anon_client.request(
        "OPTIONS",
        "/properties/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code in (200, 204)


def test_protected_write_without_scope_is_forbidden(
    anon_client: httpx.Client, user_record: dict[str, str]
) -> None:
    users.login(anon_client, user_record["username"], user_record["password"])
    # A freshly registered user has no properties:write scope.
    resp = anon_client.post("/properties/", json={})
    assert resp.status_code in (
        403,
        422,
    )  # 403 = scope denied, 422 only if authz passes
    assert resp.status_code == 403

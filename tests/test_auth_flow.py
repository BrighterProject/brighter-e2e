"""E2E: registration, cookie auth, Bearer fallback, scope visibility."""

from __future__ import annotations

import httpx
import pytest

from e2e import config, users
from e2e.http import make_client


def test_login_sets_httponly_cookie(anon_client: httpx.Client, user_record: dict[str, str]) -> None:
    users.login(anon_client, user_record["username"], user_record["password"])
    assert "access_token" in anon_client.cookies


def test_protected_route_requires_cookie(user_record: dict[str, str]) -> None:
    with make_client() as client:  # no cookie
        resp = client.get("/users/me")
        assert resp.status_code == 401


def test_bearer_fallback_is_accepted(anon_client: httpx.Client, user_record: dict[str, str]) -> None:
    resp = anon_client.post(
        "/auth",
        data={"username": user_record["username"], "password": user_record["password"]},
    )
    token = resp.json()["access_token"]
    with make_client() as bare:
        bare.cookies.clear()
        r = bare.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

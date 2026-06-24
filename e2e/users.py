"""Helpers to register, authenticate, and escalate test users."""

from __future__ import annotations

import uuid

import httpx

from e2e.clients import mailpit

# Owner scopes the platform grants; kept here so tests don't import service code.
DEFAULT_OWNER_SCOPES: list[str] = [
    "properties:me",
    "properties:write",
    "properties:delete",
    "properties:images",
    "properties:schedule",
    "bookings:manage",
]
DEFAULT_ADMIN_SCOPES: list[str] = ["admin:users", "admin:properties", "admin:bookings"]


def register_user(client: httpx.Client) -> dict[str, str]:
    """Create a fresh user with a unique username/email and return its record."""
    suffix = uuid.uuid4().hex[:12]
    payload = {
        "username": f"e2e_{suffix}",
        "full_name": "E2E User",
        "email": f"e2e_{suffix}@example.com",
        "password": "Sup3rSecret!",
    }
    resp = client.post("/users/", json=payload)
    resp.raise_for_status()
    body = resp.json()
    verify_email(client, payload["email"])
    return {**payload, "id": body["id"]}


def verify_email(client: httpx.Client, email: str) -> None:
    """Activate a freshly-registered account via the email verification link.

    Reads the token from the email mailpit captured, then hits the verify
    endpoint so the user becomes active and can authenticate.
    """
    token = mailpit.fetch_verification_token(email)
    resp = client.get("/auth/verify-email", params={"token": token})
    resp.raise_for_status()


def login(client: httpx.Client, username: str, password: str) -> None:
    """Log in via the OAuth2 password form; the access_token cookie is stored."""
    resp = client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    assert "access_token" in client.cookies


def escalate_scopes(
    admin_client: httpx.Client, user_id: str, scopes: list[str]
) -> None:
    """Grant scopes to a user (admin-only endpoint)."""
    resp = admin_client.put(f"/users/{user_id}/scopes", json={"scopes": scopes})
    resp.raise_for_status()


def register_owner(client: httpx.Client) -> dict[str, str]:
    """Self-register a property owner (grants DEFAULT_OWNER_SCOPES immediately).

    No admin needed: the service's /users/register-owner endpoint assigns owner
    scopes on creation.
    """
    suffix = uuid.uuid4().hex[:12]
    payload = {
        "username": f"e2eowner_{suffix}",
        "full_name": "E2E Owner",
        "email": f"e2eowner_{suffix}@example.com",
        "password": "Sup3rSecret!",
        "phone": "+359888123456",
    }
    resp = client.post("/users/register-owner", json=payload)
    resp.raise_for_status()
    verify_email(client, payload["email"])
    return {**payload, "id": resp.json()["id"]}

"""HTTP client factory for talking to the stack through Traefik."""

from __future__ import annotations

import httpx

from e2e import config


def make_client() -> httpx.Client:
    """Return a client rooted at the Traefik gateway with a fresh cookie jar."""
    return httpx.Client(base_url=config.BASE_URL, timeout=10.0, follow_redirects=False)

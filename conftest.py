"""Session health gate and shared user fixtures for the E2E suite."""

from __future__ import annotations

from collections.abc import Generator

import httpx
import pytest
from tenacity import retry, stop_after_delay, wait_fixed

from e2e import config, users
from e2e.http import make_client


@retry(stop=stop_after_delay(config.HEALTH_TIMEOUT_SECONDS), wait=wait_fixed(2))
def _wait_for_stack() -> None:
    """Warm-up gate: poll a real route through Traefik until it answers 2xx."""
    with httpx.Client(base_url=config.BASE_URL, timeout=5.0) as c:
        assert c.get("/properties").status_code == 200


@pytest.fixture(scope="session", autouse=True)
def _stack_ready() -> None:
    try:
        _wait_for_stack()
    except Exception as exc:  # noqa: BLE001 - surface a clear setup failure
        pytest.exit(
            f"Stack not reachable at {config.BASE_URL}. "
            f"Start it with COMPOSE_PROFILES=e2e docker compose up -d --wait. ({exc})",
            returncode=2,
        )


@pytest.fixture
def anon_client() -> Generator[httpx.Client, None, None]:
    with make_client() as client:
        yield client


@pytest.fixture
def user_record(anon_client: httpx.Client) -> dict[str, str]:
    return users.register_user(anon_client)

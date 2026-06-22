"""Runtime configuration for the E2E suite, sourced from the environment."""

from __future__ import annotations

import os

BASE_URL: str = os.environ.get("BASE_URL", "http://localhost")
MAILPIT_URL: str = os.environ.get("MAILPIT_URL", "http://localhost:8025")
STRIPE_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_e2e")
STRIPE_CONNECT_WEBHOOK_SECRET: str = os.environ.get(
    "STRIPE_CONNECT_WEBHOOK_SECRET", "whsec_e2e_connect"
)
HEALTH_TIMEOUT_SECONDS: int = int(os.environ.get("E2E_HEALTH_TIMEOUT", "60"))

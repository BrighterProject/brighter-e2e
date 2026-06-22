"""Read-side client for asserting emails delivered to Mailpit."""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_delay, wait_fixed

from e2e import config


@retry(stop=stop_after_delay(20), wait=wait_fixed(1), reraise=True)
def wait_for_email(to: str, subject_contains: str | None = None) -> dict:
    """Poll Mailpit for a message addressed to `to`; return the first match.

    Filters strictly by recipient so parallel tests never see each other's mail.
    """
    with httpx.Client(base_url=config.MAILPIT_URL, timeout=5.0) as c:
        resp = c.get("/api/v1/search", params={"query": f"to:{to}"})
        resp.raise_for_status()
        messages = resp.json().get("messages", [])
        if subject_contains is not None:
            messages = [m for m in messages if subject_contains in m.get("Subject", "")]
        assert messages, f"no email to {to} (subject~{subject_contains})"
        return messages[0]

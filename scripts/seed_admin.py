"""Seed an idempotent admin user for the E2E suite.

Run INSIDE the users-ms container:
    docker compose exec -T users-ms uv run python - < scripts/seed_admin.py
Reads E2E_ADMIN_USER / E2E_ADMIN_PASS from the environment.
"""

import asyncio
import os

from tortoise import Tortoise

from app.auth import get_password_hash
from app.models import User
from app.scopes import DEFAULT_ADMIN_SCOPES
from app.settings import db_url


async def seed() -> None:
    username = os.environ["E2E_ADMIN_USER"]
    password = os.environ["E2E_ADMIN_PASS"]
    await Tortoise.init(db_url=db_url, modules={"models": ["app.models"]})
    scopes = [str(s) for s in DEFAULT_ADMIN_SCOPES]
    await User.update_or_create(
        username=username,
        defaults={
            "full_name": "E2E Admin",
            "email": f"{username}@example.com",
            "hashed_password": get_password_hash(password),
            "is_active": True,
            "scopes": scopes,
        },
    )
    print(f"seeded admin {username} with {scopes}")
    await Tortoise.close_connections()


asyncio.run(seed())

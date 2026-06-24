COMPOSE := docker compose -f ../brighter-compose/docker-compose.yml
export COMPOSE_PROFILES := e2e
export OTEL_SDK_DISABLED := true
export STRIPE_API_BASE := http://stripe-mock:12111
# Pin webhook signing secrets so the stack and the offline stripe_hooks signer
# agree (shell env overrides any brighter-compose/.env). Must match config.py.
export STRIPE_WEBHOOK_SECRET := whsec_e2e
export STRIPE_CONNECT_WEBHOOK_SECRET := whsec_e2e_connect
# Deliver verification email via SMTP → mailpit (not Resend) so the suite can
# read the token. ASCII from-address avoids SMTPUTF8/IDNA handling for mailpit.
export EMAIL_TRANSPORT := smtp
export DEFAULT_FROM_EMAIL := Brighter <noreply@brighter.bg>
# Disable users-ms rate limiting: the whole suite shares one Traefik-sourced IP
# bucket, so per-minute registration caps would otherwise throttle parallel runs.
export SLOWAPI_NO_LIMITS := 1
E2E_ADMIN_USER ?= e2e_admin
E2E_ADMIN_PASS ?= Adm1nSecret!
export E2E_ADMIN_USER
export E2E_ADMIN_PASS

.PHONY: up seed seed-admin test e2e lint typecheck clean-e2e-db

up:
	$(COMPOSE) up -d --wait

seed-admin:
	$(COMPOSE) exec -T -e E2E_ADMIN_USER -e E2E_ADMIN_PASS users-ms uv run python - < scripts/seed_admin.py

seed: seed-admin
	$(COMPOSE) exec -T payments-ms uv run python scripts/seed_subscription_plans.py

test:
	uv run pytest -n auto

# Full local run: boot, seed, then test. CI splits these into separate steps
# (make up / make seed / make test) for per-phase failure attribution.
e2e: up seed test

lint:
	uv run ruff check . && uv run ruff format --check .

typecheck:
	uvx ty check e2e conftest.py

clean-e2e-db:
	$(COMPOSE) rm -fsv db || true
	docker volume rm brighter-compose_pgdata || true

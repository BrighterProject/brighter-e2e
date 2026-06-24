# brighter-e2e

End-to-end integration suite for BrighterProject. Boots the **full stack** via
`brighter-compose` (Traefik + all backend services + Postgres + Redis + mailpit +
stripe-mock, compose profile `e2e`) and exercises real cross-service flows: auth,
owner self-registration with email verification, properties, bookings, payments.

## Branch & PR workflow

- Default branch is **`main`** (infra-style repo). Branch off `main` as
  `feat/`/`fix/`/`chore/<slug>`, PR to `main`.
- The suite under test is checked out from `main`; service repos are checked out
  at the run's `service_ref` (default `dev`).

## Running the suite

```bash
make e2e          # local one-shot: boot + seed + test
make up           # docker compose up -d --wait   (profile: e2e)
make seed         # admin user + subscription plans
make test         # pytest -n auto

make dispatch              # remote (GitHub Actions), services @ dev
make dispatch REF=main     # ...or any branch
make watch                 # stream the latest remote run to completion
```

## Key conventions

- **The Makefile is the single source of truth for run env.** It `export`s
  `EMAIL_TRANSPORT=smtp`, `SLOWAPI_NO_LIMITS=1`, `OTEL_SDK_DISABLED`, Stripe test
  secrets, and admin creds. Do NOT duplicate these in the workflow `env:`.
- **The GitHub workflow is manual-only** (`workflow_dispatch`). It does not run on
  push/PR and there is no `repository_dispatch`: a dispatch from a service merge
  never surfaced as a check on the service PR, so auto-triggering only produced
  unwatched runs. Run it deliberately and read the result.
- **CI splits the run** into `make up` / `make seed` / `make test` steps for
  per-phase failure attribution; `make e2e` is the local one-shot.
- Tests hit the **real running stack** (no mocking). Tests live in `tests/`,
  HTTP/seed helpers in `e2e/`.

## Wiring an env-gated feature for e2e

When a service needs different behaviour under e2e (e.g. SMTP transport instead of
Resend), wire the toggle in **three places** or the run still fails:

1. **service code → its `dev`** — read an env var; default to prod-safe behaviour.
2. **`brighter-compose/docker-compose.yml` → `main`** — pass it through:
   `VAR: ${VAR:-<prod-default>}`.
3. **this repo's `Makefile` → `main`** — `export VAR := <e2e value>`.

Production stays safe because compose defaults the var to the production value.

## Gotchas

- **`entrypoint.sh` must be mode `100755`** on every service branch. Dev compose
  bind-mounts the repo over `/app`, so a `100644` host file shadows the image's
  `chmod +x` copy and breaks startup (`exec: ./entrypoint.sh: permission denied`).
- The `test_connect_onboard_via_stripe_v2` xfail is expected: stripe-mock does not
  emulate the Stripe Accounts v2 API; the code path is correct against real Stripe.

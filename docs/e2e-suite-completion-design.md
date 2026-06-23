# E2E Suite Completion — Implementation Design

Status: **draft / proposed**
Owner: TBD
Last updated: 2026-06-23

This document captures (a) what has already been fixed to get the e2e pipeline
booting, (b) the remaining work to make the suite actually pass — centered on the
**email-verification activation flow via mailpit** — and (c) the CI
optimization plan. It is written so an implementer can execute it top-to-bottom.

---

## 1. Background & current state

`brighter-e2e` boots the full compose stack (`e2e` profile), seeds an admin +
subscription plans, then runs `pytest -n auto` against the stack through Traefik.

### 1.1 Already fixed (root-caused from CI evidence)

| # | Symptom | Root cause | Fix | Repo / commit |
|---|---------|-----------|-----|---------------|
| 1 | `stripe-mock` unhealthy → `compose up --wait` fails | Healthcheck hit `/v1/` and got **401**; busybox `wget` treats 4xx as failure. A 401 already proves liveness. | Healthcheck accepts any HTTP response (`grep -qE 'Unauthorized\|charges'`) | `brighter-compose` `38462ff` |
| 2 | `notifications-ms` unhealthy → startup crash | `mjml` CLI `FileNotFoundError`: the source **bind-mount shadowed the image's `/app/node_modules`**, so the mjml binary disappeared at runtime | Added a `notifications-node-modules` named volume (seeds from image, same pattern as `.venv`) | `brighter-compose` `67f1705` |
| 3 | Every xdist worker "crashes" at session start | Stack-ready gate hit **bare paths** (`/properties`); Traefik only serves `/api/*` and there is **no frontend catch-all in the `e2e` profile** → 404 → 60s gate timeout → `pytest.exit` in every worker | Pointed suite at `/api` + fixed path drift | `brighter-e2e` `fix: align e2e suite paths…` |
| 4 | Failure logs unusable | Dump step didn't activate `e2e` profile, so stripe-mock/mailpit logs were missing | Dump now prints per-container healthcheck `exit/out` + `e2e`-profile logs | `brighter-e2e` `ci: capture healthcheck logs…` |

### 1.2 Path drift corrected in the suite

The suite was scaffolded against an older contract. Verified against live routers:

| Suite called | Correct (live) | Why |
|--------------|----------------|-----|
| `POST /auth` | `POST /auth/token` | OAuth2 token endpoint |
| `POST /users`, `GET /properties`, `GET /payments` | `…/` (trailing slash) | collection roots are `@router.get("/")`; service returns hard **404** (no `redirect_slashes`) |
| `POST /payments` | `POST /payments/checkout` | checkout endpoint |
| `POST /payments/subscriptions` | `POST /payments/subscriptions/checkout` | |
| `GET /users/me` | `GET /users/@me/get` | actual current-user route |
| email `@example.test` | `@example.com` | `EmailStr` rejects reserved `.test` TLD → 422 |
| owner payload missing `phone` | add `phone` | `OwnerCreate.phone` is required |

> **Pending (uncommitted) in `brighter-e2e`:** the `@example.com` + owner `phone`
> changes are applied locally but **not pushed** — they belong with the
> verification work below so CI isn't churned on a still-red run.

### 1.3 The remaining blocker

`register_user` **and** `register_owner` (in `brighter-users-ms/app/routers/users.py`)
create users with **`is_active=False`** and an `email_verification_token`, then
fire a verification email. `authenticate_user` rejects inactive users → **`POST
/auth/token` returns 401** → every fixture that logs in fails.

The suite already ships `e2e/clients/mailpit.py::wait_for_email` that is **never
called** — confirming the verification round-trip was designed but never wired.

---

## 2. The email-verification activation flow

### 2.1 Target flow

```
register_user/owner ──► POST /api/users[/register-owner]   (201, user inactive)
        │
        ├─ users-ms fires POST notifications-ms:8004/notifications/send
        │     (already sends X-User-Scopes: admin:notifications:write — auth OK)
        │
        ▼
notifications-ms ──► deliver email ──► mailpit  (SMTP :1025)   ◄── GAP (see 2.2)
        │
        ▼
e2e: wait_for_email(to) ─► GET mailpit /api/v1/message/{id} ─► extract token
        │
        ▼
e2e: GET /api/auth/verify-email?token=…   (user.is_active = True)
        │
        ▼
e2e: login(/auth/token) ─► 200 + access_token cookie
```

### 2.2 GAP — notifications-ms delivers via Resend HTTP API, not mailpit

`brighter-notifications-ms/app/routers/notifications.py` calls
`resend.Emails.send(...)` (Resend's HTTPS API). In the `e2e` profile
`RESEND_API_KEY=re_test_placeholder`, so the call fails (caught, logged as
`failed`, returns 201) and **nothing ever reaches mailpit**. mailpit is an SMTP
sink on `mailpit:1025` (web/API `:8025`; `MP_SMTP_AUTH_ALLOW_INSECURE=true`),
and is **not** Resend-API-compatible, so overriding `resend.api_url` will not work.

**Decision required up-front:** notifications-ms needs a pluggable transport so it
sends via **SMTP → mailpit** in dev/e2e and via Resend in prod.

> ⚠️ Editing `brighter-notifications-ms` is a service change with its own
> PR/branch/`dev` flow (see its CLAUDE.md). Coordinate before starting.

#### Recommended implementation (notifications-ms)

1. `app/settings.py` — add transport config:
   ```python
   email_transport = os.environ.get("EMAIL_TRANSPORT", "resend")  # "resend" | "smtp"
   smtp_host = os.environ.get("SMTP_HOST", "mailpit")
   smtp_port = int(os.environ.get("SMTP_PORT", "1025"))
   smtp_starttls = os.environ.get("SMTP_STARTTLS", "false").lower() == "true"
   ```
2. New `app/email_transport.py` with a small `Protocol` and two impls:
   - `ResendTransport` — wraps the current `resend.Emails.send` call.
   - `SmtpTransport` — `aiosmtplib.send(...)` (async; `uv add aiosmtplib`) building a
     `email.message.EmailMessage` (HTML), `From = settings.default_from_email`.
     Return a synthetic id so the existing `log_sent(resend_id=…)` path is unchanged.
3. `send_email` / `dispatch` pick the transport from `settings.email_transport`.
   Keep the existing try/except + CRUD logging.
4. Compose: set on `notifications-ms` (both base and/or an `e2e` override):
   ```yaml
   EMAIL_TRANSPORT: ${EMAIL_TRANSPORT:-resend}
   SMTP_HOST: ${SMTP_HOST:-mailpit}
   SMTP_PORT: ${SMTP_PORT:-1025}
   ```
   In the e2e workflow env set `EMAIL_TRANSPORT: smtp`.
5. Unit tests in notifications-ms: mock `aiosmtplib.send`; assert SMTP path chosen
   when `EMAIL_TRANSPORT=smtp`; keep Resend tests green. (80% coverage gate.)

> **Context7:** before coding, pull current docs for `aiosmtplib` (async send
> signature, STARTTLS) and confirm the `resend` Python SDK surface. Use Context7
> rather than guessing the APIs.

> **Alternative (no service change), if transport work is deferred:** add a
> **test seam** — an internal, network-only `is_active` activation. This is the
> "Test-only activation seam" option and is intentionally *not* chosen here, but
> noted as the fallback if the SMTP chain proves too costly.

### 2.3 e2e suite work (`brighter-e2e`)

Once mail lands in mailpit:

1. `e2e/clients/mailpit.py` — add body fetch + token extraction:
   ```python
   import re
   _TOKEN_RE = re.compile(r"verify-email\?token=([A-Za-z0-9_\-]+)")

   def fetch_verification_token(to: str) -> str:
       msg = wait_for_email(to, subject_contains="Verify")   # existing poller
       with httpx.Client(base_url=config.MAILPIT_URL, timeout=5.0) as c:
           full = c.get(f"/api/v1/message/{msg['ID']}").raise_for_status().json()
       body = f"{full.get('HTML','')} {full.get('Text','')}"
       m = _TOKEN_RE.search(body)
       assert m, f"no verification token in email to {to}"
       return m.group(1)
   ```
   > **Context7:** confirm mailpit's message JSON keys (`ID`, `HTML`, `Text`) and
   > the search response shape for `axllent/mailpit:v1.20`.
2. `e2e/users.py` — add `verify(client, email)` that GETs
   `/auth/verify-email?token=…`, then make `register_user`/`register_owner` call it
   so returned accounts are **active**:
   ```python
   def verify_email(client, email):
       token = mailpit.fetch_verification_token(email)
       client.get("/auth/verify-email", params={"token": token}).raise_for_status()
   ```
   Call it at the end of `register_user` and `register_owner` before returning.
   (Keeps `login()` and all fixtures unchanged.)
3. Commit the held `@example.com` + owner `phone` edits alongside this.

### 2.4 After activation — expect a second wave of per-test work

Activation unblocks auth; the booking/payment/subscription tests then exercise real
business logic and may surface further mismatches (Stripe webhook signing vs
`stripe-mock`, subscription-plan seeding, refund math, notification side-effects).
Triage each from the now-useful failure dump; fix paths/payloads/assertions per
the live contract. Treat this as a short iterative loop, not a big bang.

---

## 3. Local execution with `act` (avoid CI round-trips)

The e2e workflow takes ~4 min/run; iterate locally instead.

- Tool: [`act`](https://github.com/nektos/act) runs the GH workflow in Docker.
- The job checks out **8 sibling repos** and builds the full compose stack, so:
  - Use a large runner image: `act -P ubuntu-latest=catthehacker/ubuntu:full-latest`.
  - It needs Docker (compose-in-job). Run with the host Docker socket
    (`--container-daemon-socket -` or bind `/var/run/docker.sock`).
  - Provide repo access for the private checkouts: `act -s GITHUB_TOKEN=$(gh auth token)`.
- Trigger the same event CI uses:
  ```bash
  act repository_dispatch -e event.json   # event.json: {"action":"service-merged", ...}
  # or simply: act push   (e2e.yml also runs on push to master)
  ```
- Faster inner loop: once the stack is up locally you can bypass `act` entirely and
  run `make e2e` (or `uv run pytest -o addopts="-ra" tests/…`) against a
  locally-booted `COMPOSE_PROFILES=e2e` stack. mailpit + stripe-mock must be up for
  the verification/payment tests.

---

## 4. CI optimization plan (4-min runtime + log noise)

Apply after the suite is green (so debugging runs stay readable).

1. **Docker layer caching (biggest win, ~2 min).** The job rebuilds 6 Python images
   + notifications-ms (apt install node + `npm ci`) from scratch every run. Add
   `docker/setup-buildx-action` and BuildKit GHA cache to the compose build:
   ```yaml
   - uses: docker/setup-buildx-action@v3
   - run: COMPOSE_PROFILES=e2e docker compose -f ../brighter-compose/docker-compose.yml build
     env:
       COMPOSE_BAKE: "true"          # use buildx bake
       # per-service: cache_from/cache_to type=gha (or a bake file with x-bake cache)
   ```
   Simplest path: a `docker-bake.hcl` with `cache-from = ["type=gha"]`,
   `cache-to = ["type=gha,mode=max"]`, invoked via `docker buildx bake`.
2. **Concurrency — kill the pile-up.** The "cancelled" runs the user saw are
   superseded triggers. Add:
   ```yaml
   concurrency:
     group: e2e-${{ github.ref }}
     cancel-in-progress: true
   ```
3. **Trim log noise.**
   - Quiet apt in `brighter-notifications-ms/Dockerfile`: `apt-get install -qq … > /dev/null`
     and `npm ci --silent`.
   - Failure dump: only emit logs for **unhealthy/exited** containers, not all
     (filter `docker ps` by status before `compose logs`).
4. **Remove redundant work.** `checks.yml` re-runs each backend service's unit-test
   matrix on every push to the e2e repo — those already run in each service's own CI.
   Drop `checks.yml` (or restrict to `paths:`/manual) and let e2e own only the
   integration concern.
5. **Silence deprecations.** Bump `actions/checkout` / `astral-sh/setup-uv` to
   Node24-based releases to clear the runner warnings.
6. **Right-size parallelism.** `-n auto` = vCPU count; on the shared runner with the
   full stack, `-n 2` (or `--dist loadgroup` as today) may be more stable. Re-evaluate
   once green.

Target after (1)+(2): warm runs ~2 min, no cancelled pile-ups, readable logs.

---

## 5. Work breakdown / order of execution

1. **notifications-ms**: SMTP transport (`EMAIL_TRANSPORT=smtp` → mailpit) + tests. *(blocks everything below)*
2. **brighter-compose**: wire `EMAIL_TRANSPORT`/`SMTP_HOST`/`SMTP_PORT`; e2e sets `smtp`.
3. **brighter-e2e**: mailpit token extraction + `verify_email` in register helpers; commit held `@example.com`+`phone`.
4. Run locally (`act` or local `e2e` stack); iterate on the second-wave business-logic failures.
5. **CI optimization** (§4) once green.

## 6. Risks / open questions

- **SMTP From-address**: `DEFAULT_FROM_EMAIL` contains Cyrillic (`@площадка.бг`);
  ensure SMTPUTF8 / IDNA handling so mailpit accepts it (or override in e2e).
- **Verification link locale**: `verify_url` is `/{locale}/auth/verify-email?token=…`;
  the regex in §2.3 matches the `token` param regardless of locale prefix — keep it that way.
- **Subscription-plan seed** must exist for `test_owner_subscription` (seeded by
  `make seed`); confirm slugs match what the test posts.
- **stripe-mock statefulness**: `stripe_hooks` builds signed webhooks offline
  because stripe-mock never delivers them — verify the signing secret matches the
  service's `STRIPE_WEBHOOK_SECRET` in e2e.

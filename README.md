# Tennis Court Finder

Real-time tennis court availability tracker with notifications. Monitors integrated booking systems and alerts you when desired time slots open up.

## What's Implemented

| Area | Status | Details |
|------|--------|---------|
| **API (spec-first)** | ✅ | OpenAPI 3.0 spec → auto-generated Pydantic models → FastAPI |
| **Web UI** | ✅ | Jinja2 + HTMX + Pico CSS — schedule grid, login, alert management |
| **SEB Arena integration** | ✅ | Live court & slot data from [book.sebarena.lt](https://book.sebarena.lt) |
| **Caching** | ✅ | Background refresh every 60 s — external API is never hit per-request |
| **Auth** | ✅ | Email OTP → signed JWT stored in HTTP-only cookie |
| **Database** | ✅ | SQLite via `aiosqlite` — subscriptions & OTP codes persist across restarts |
| **Notification engine** | ✅ | Background task detects slot status transitions, matches against subscriptions |
| **Email delivery** | ✅ | SMTP via `aiosmtplib` — falls back to console output when SMTP is not configured |
| **Deployment** | ✅ | Dockerfile, Fly.io config, GitHub Actions CI/CD |

## Quick Start

```bash
# 1. Install tooling (Python managed via mise)
brew install mise        # or see https://mise.jdx.dev
mise install             # installs Python version from .mise.toml

# 2. Install dependencies
poetry install

# 3. Run
poetry run python main.py
```

Open [localhost:8000](http://localhost:8000) for the UI, or [localhost:8000/docs](http://localhost:8000/docs) for Swagger.

The SQLite database is created automatically at `data/tennis_court_finder.db` on first run.

## Deployment (Fly.io)

The app is designed to run on [Fly.io](https://fly.io) free tier with a persistent volume for SQLite.

### First-time setup

```bash
# Install the Fly CLI
brew install flyctl

# Authenticate
fly auth login

# Create the app (uses fly.toml config)
fly launch --no-deploy

# Create a 1 GB persistent volume for SQLite
fly volumes create data --region ams --size 1

# Set production secrets
fly secrets set \
  JWT_SECRET=$(openssl rand -hex 32) \
  SMTP_HOST=smtp.example.com \
  SMTP_PORT=587 \
  SMTP_USERNAME=your-username \
  SMTP_PASSWORD=your-password \
  SMTP_FROM_EMAIL=alerts@yourdomain.com

# Deploy
fly deploy
```

### Automated deployment via GitHub Actions

Push to `main` triggers the CI/CD pipeline (`.github/workflows/ci.yml`):

1. **Test** — runs `pytest` on every push and PR
2. **Deploy** — on push to `main`, deploys to Fly.io automatically

Add the `FLY_API_TOKEN` secret to your GitHub repo:

```bash
fly tokens create deploy -x 999999h
# Copy the token → GitHub repo → Settings → Secrets → Actions → FLY_API_TOKEN
```

### SMTP (free tier options)

| Provider | Free tier | Setup |
|----------|-----------|-------|
| [Brevo](https://brevo.com) | 300 emails/day | SMTP credentials in dashboard |
| [Resend](https://resend.com) | 3,000 emails/month | SMTP credentials in dashboard |
| Gmail | ~500/day | App password via Google Account security |

Without SMTP configured, all emails (OTP codes, notifications) are printed to the console.

## Project Structure

```
openapi.yaml              ← single source of truth for the API contract
app/
  config.py               ← settings from env vars (JWT, DB, SMTP, notifier)
  db.py                   ← SQLite repository (subscriptions, OTP codes, logs)
  generated/models.py     ← auto-generated from openapi.yaml (do not edit)
  routers/                ← FastAPI route handlers (API + HTML pages)
  services/
    tennis_club.py        ← TennisClubService protocol (interface)
    cache.py              ← in-memory cache with background refresh
    notifier.py           ← slot change detection + subscription matching
    email.py              ← SMTP / console email delivery
    registry.py           ← service registry (maps club slugs → services)
    seb_arena/            ← SEB Arena integration (client, service, config)
  templates/              ← Jinja2 templates (base, pages, HTMX partials)
data/                     ← SQLite DB file (gitignored, auto-created)
Dockerfile                ← multi-stage production image
fly.toml                  ← Fly.io deployment config
.github/workflows/ci.yml  ← CI/CD pipeline (test + deploy)
scripts/generate.py       ← model generation script
tests/
  unit_tests/             ← pytest unit tests (81 tests)
  mocks/                  ← shared mock data & services
```

## Development

### Regenerate models after editing `openapi.yaml`

```bash
poetry run generate
```

### Run tests

```bash
poetry run pytest
```

### Configure SMTP (optional)

Copy `env.example` to `.env` and fill in your SMTP credentials. Without SMTP configured, notification emails are printed to the console — useful for development.

### Add a new club integration

1. Create `app/services/<club_slug>/` with `client.py`, `service.py`, `config.py`
2. Implement the `TennisClubService` protocol (see `app/services/tennis_club.py`)
3. Register it in `ClubRegistry.register_<club>()` inside `app/services/registry.py`
4. Call the register method in `app/main.py` lifespan

### Key conventions

- **API-first**: edit `openapi.yaml`, regenerate models, then write route handlers
- **Slug-based club IDs**: clubs use URL-friendly slugs (`seb-arena`), not UUIDs
- **Cache-first reads**: routers → `CachedClubService` → in-memory cache; the external API is only called by the background refresh task
- **Notifier loop**: runs every 60 s, diffs the slot snapshot, matches transitions against active subscriptions, sends one digest email per user
- **HTMX partials**: templates under `partials/` are fragments returned for in-page swaps; full pages extend `base.html`

# Tennis Court Finder

Real-time tennis court availability tracker with notifications. Monitors integrated booking systems and alerts you when desired time slots open up.

## What's Implemented

| Area | Status | Details |
|------|--------|---------|
| **API (spec-first)** | ✅ | OpenAPI 3.0 spec → auto-generated Pydantic models → FastAPI |
| **Web UI** | ✅ | Jinja2 + HTMX + Pico CSS — schedule grid, login, alert management |
| **SEB Arena integration** | ✅ | Live court & slot data from [book.sebarena.lt](https://book.sebarena.lt) |
| **Caching** | ✅ | Background refresh every 60 s — external API is never hit per-request |
| **Auth** | 🔶 | Email OTP flow (mocked — any email + code `123456` works) |
| **Notifications** | 🔶 | CRUD for subscriptions (in-memory, no actual delivery yet) |
| **Database** | ❌ | All data is in-memory; subscriptions reset on restart |

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

## Project Structure

```
openapi.yaml              ← single source of truth for the API contract
app/
  generated/models.py     ← auto-generated from openapi.yaml (do not edit)
  routers/                ← FastAPI route handlers (API + HTML pages)
  services/
    tennis_club.py        ← TennisClubService protocol (interface)
    cache.py              ← in-memory cache with background refresh
    registry.py           ← service registry (maps club slugs → services)
    seb_arena/            ← SEB Arena integration (client, service, config)
  templates/              ← Jinja2 templates (base, pages, HTMX partials)
scripts/generate.py       ← model generation script
tests/
  unit_tests/             ← pytest unit tests
  integration_tests/      ← (placeholder)
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

### Add a new club integration

1. Create `app/services/<club_slug>/` with `client.py`, `service.py`, `config.py`
2. Implement the `TennisClubService` protocol (see `app/services/tennis_club.py`)
3. Register it in `ClubRegistry.register_<club>()` inside `app/services/registry.py`
4. Call the register method in `app/main.py` lifespan

### Key conventions

- **API-first**: edit `openapi.yaml`, regenerate models, then write route handlers
- **Slug-based club IDs**: clubs use URL-friendly slugs (`seb-arena`), not UUIDs
- **Cache-first reads**: routers → `CachedClubService` → in-memory cache; the external API is only called by the background refresh task
- **HTMX partials**: templates under `partials/` are fragments returned for in-page swaps; full pages extend `base.html`

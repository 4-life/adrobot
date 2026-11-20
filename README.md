# AdRobot

[![CI](https://github.com/4-life/adrobot/actions/workflows/ci.yml/badge.svg)](https://github.com/4-life/adrobot/actions/workflows/ci.yml)

An MVP dashboard, run locally, on top of Keitaro. Keitaro does the tracking, redirects and clicks. AdRobot creates Keitaro campaigns and manages the offers in their streams. You edit everything locally as a draft, review the changes, and then push them to Keitaro.

The full design (services, sync rules, Keitaro integration, API, database, testing, security) is in [docs/DESIGN.md](docs/DESIGN.md). The build order is in [PLAN.md](PLAN.md).

## How It Works

Every campaign has two streams, in this order:

| # | Stream | What it does | In AdRobot |
|---|---|---|---|
| 1 | **Geo stream** | Redirects every visitor from the geo countries (Australia by default) to Google | Set at creation, then read-only |
| 2 | **Offers stream** | Splits all other traffic between offers by share (%) | Add, remove, pin, bring back |

1. **Fetch streams** pulls every campaign with its streams and offers from Keitaro.
2. **Create a campaign**, or edit offers. Nothing reaches Keitaro yet, and every unsynced change is marked as pending.
3. **Cancel changes** discards the draft.
4. **Push to KT** writes the draft to Keitaro.

## Tech Stack

- **Backend**: Python 3.14, uv, FastAPI, PostgreSQL with SQLAlchemy 2.0 (async), Alembic.
- **Dashboard**: React with server-side rendering (React Router), Tailwind, shadcn/Base UI.
- **Keitaro client**: Pydantic models generated from Keitaro's OpenAPI schema.
- **Run**: Docker Compose, local only.

## Quick Start

Needs Docker, [uv](https://docs.astral.sh/uv/) and Node.js.

```bash
# first time: the lockfile and the local tooling for checks
cd backend && uv lock && uv sync && cd ..
cd dashboard && npm install && cd ..
chmod +x scripts/*.sh

# config: set KEITARO_URL (no path) and KEITARO_API_KEY
cp .env.example .env

# run
docker compose -f docker/local/compose.yaml up -d --build
```

- Dashboard: http://localhost:3000
- API health: http://localhost:8000/health
- Checks (lint, types, tests): `scripts/check.sh`. CI runs the same checks on every push and pull request (`.github/workflows/ci.yml`).

There's no login, and the ports are bound to `127.0.0.1`. Don't expose them to a network. All variables are listed in [docs/DESIGN.md: Configuration](docs/DESIGN.md#configuration).

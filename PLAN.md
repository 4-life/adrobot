# AdRobot — Implementation Plan

The app is described in [README](README.md) and [docs/DESIGN.md](docs/DESIGN.md). This is an MVP: it runs locally only, with no auth and no deploy. Each phase ends with `scripts/check.sh` passing (Ruff, mypy, pytest and the dashboard typecheck). Before any dependency is pinned, its latest version is checked.

## Repo Layout

```
adrobot/
├─ backend/
│  ├─ app/
│  │  ├─ config.py, db.py
│  │  ├─ models/              # SQLAlchemy models (vendor-neutral)
│  │  ├─ tracker/
│  │  │  ├─ port.py           # TrackerProvider protocol + domain types + TrackerError
│  │  │  ├─ factory.py        # composition root: picks the adapter (TRACKER)
│  │  │  ├─ cache.py          # TTL cache for lookups
│  │  │  └─ keitaro/          # the Keitaro adapter: the only code that knows Keitaro
│  │  │     ├─ openapi.yaml, SCHEMA_VERSION
│  │  │     ├─ models.py      # GENERATED: Pydantic v2
│  │  │     ├─ models_overrides.py
│  │  │     ├─ client.py      # hand-written async httpx client
│  │  │     ├─ layout.py      # geo + offers stream detection
│  │  │     └─ adapter.py     # KeitaroTracker: Keitaro ↔ port types
│  │  ├─ campaigns/           # core: merge, pending, sync, shares, push (port only)
│  │  └─ api/                 # inbound adapter: routes
│  ├─ migrations/
│  ├─ tests/ (+ fixtures/keitaro/*_sample.json, fake tracker)
│  └─ pyproject.toml
├─ dashboard/
├─ docker/{local,test}/compose.yaml
└─ scripts/{check.sh,e2e-test.sh,gen-keitaro.sh,gen-api-types.sh}
```

## Phase 0: Scaffold

- The backend: pyproject, config, db, Alembic, `/health`.
- A dashboard skeleton.
- `docker/local/compose.yaml` with postgres, migrate, api and dashboard. All ports are bound to `127.0.0.1`, and the project name is explicit.
- `.env.example` and `scripts/check.sh`.

## Phase 1: Keitaro Models and Client

- `scripts/gen-keitaro.sh` writes `models.py` from `openapi.yaml`:
  - `datamodel-code-generator --input-file-type openapi --output-model-type pydantic_v2.BaseModel`, with unknown fields allowed, then Ruff.
  - The schema is git-ignored; `models.py` is committed. `scripts/check.sh` regenerates the models when the schema is present locally; CI uses the committed file.
- Check the generator against this schema's quirks:
  - `allOf` with fragments that only list `required` (`CampaignCreateRequired` and the others);
  - `$ref` with sibling keys (`StreamRequestPut`, `AffiliateNetworkPut`);
  - `oneOf` string/object (`action_payload`);
  - HTML in descriptions.

  Fix any problems with generator flags first, then with `models_overrides.py`.
- `models_overrides.py`:
  - `Campaign.domain_id`;
  - `group_id` as an integer everywhere;
  - anything else the fixtures show.
- `client.py`:
  - `list_campaigns` (paged), `list_streams`, `get_stream`, `update_stream`, `create_campaign`, `create_stream`, `list_offers`, `list_domains`, `list_groups`, `list_sources`;
  - `KeitaroError` from the `{error}` body;
  - retries on reads only.
- **Fixtures** (`tests/fixtures/keitaro/*_sample.json`) are **synthetic**: real recordings only show the shape, then every id, name, alias, domain and token is replaced with a made-up value. Raw recordings are git-ignored and never committed.
- Unit tests: the client against the fixtures.

## Phase 2: Data Model and Fetch

- Migration `0001`: `campaigns`, `streams`, `stream_offers`, `sync_log`.
- Stream roles (Keitaro adapter, `layout.py`): position 1 with a country filter is `geo`, and the stream carrying `offers` is `offers`. A campaign that doesn't fit this layout is shown read-only as "Unsupported layout".
- `campaigns/merge.py` (pure, port types only) merges a fetch into the existing rows:
  - updates the synced state (geo countries, offers), and the domain, group and source names;
  - an offer missing from the tracker → `synced_active=false, removed_by=tracker`;
  - on a stream with no pending changes, the draft follows synced;
  - on a stream with pending changes, the draft is kept, and `conflict` is set if the synced state changed;
  - a campaign archived or missing in the tracker → `state=archived`, read-only.
- `POST /sync/fetch`, `GET /campaigns`, and `GET /tracker/*` lookups with a 60 s in-memory cache.
- Unit tests for every merge case.

## Phase 2b: Tracker Port (DIP, Hexagonal) — done

- `TrackerProvider` port with domain types. Keitaro moved behind it as an adapter (`app/tracker/keitaro/`).
- Core services and the API depend only on the port. The adapter is chosen in `factory.py` and injected via `deps.get_tracker`.
- The database and API are vendor-neutral (`external_id`, `offer_id`, `state`, `/tracker/*`).
- Adapter tests: Keitaro JSON → port types, and Keitaro errors → `TrackerError`.

## Phase 3: Draft Editing and Shares — done

- `campaigns/shares.py` (pure): equal split of what's left after pins, largest-remainder rounding, validation errors.
- `campaigns/pending.py`: per-offer change markers (`added` / `removed` / `share`), added and removed geo countries, and the pending flags.
- `campaigns/drafts.py` (pure): add, remove (an offer added only in this draft is dropped, a synced one goes to Removed), bring back (with its last pin), pin / unpin (1-100%), set geo, cancel (a new campaign is deleted). Every offer change rebalances the shares. Archived and unsupported-layout campaigns are read-only (`409`).
- Geo countries draft: `PUT /streams/{id}/geo` (ISO codes, uppercased, deduplicated, at least one).
- Endpoints: add, patch (pin), remove, restore, cancel and cancel-all.
- Unit tests: share tables (1 to 10 offers, with and without pins, edge cases), the diff and restore.

## Phase 4: Create Campaign

- `POST /campaigns` creates a draft: validates the domain, group and source against the lookups, generates the alias, stores the geo countries, and adds the offers with their calculated shares.
- Port: `create_campaign(...)`, `create_geo_stream(...)` and `create_offers_stream(...)`, taking domain types and returning external ids.
- The Keitaro adapter builds the Keitaro payloads:
  - the campaign;
  - the geo stream (redirect to `GEO_REDIRECT_URL`, country `accept` filter);
  - the offers stream (`schema: landings` with no landings, `offers` with shares; the exact `type` / `action_type` taken from the schema).
- Default name: `CAMPAIGN_NAME_PREFIX` + the next N.
- Unit tests: the payloads, alias generation and the next N.
- **First real push** (once Phase 5 is done): the owner creates `test_name_campaign1` in AdRobot and pushes it.
  - Check: did Keitaro store both streams as intended (positions, the country filter, the redirect, the offer shares)? If not, fix the payloads and retry.
  - Record `GET /campaigns/{id}/streams` as `streams.json`.
  - Edit its offers in AdRobot and push again, to confirm that `PUT /streams/{id}` replaces the offers array rather than merging it.

## Phase 5: Push

- Port: `get_stream(external_id, role)`, `push_offers(stream, offers)` and `push_geo(stream, countries)`. They return the stream as the tracker stored it.
- **Existing campaign**: for each changed stream (offers and/or geo), re-read it (`409` + conflict on a mismatch), validate (`422`), push, then set synced = draft = the result.
- **New campaign**: the create steps in order, each storing its `external_id` right away, so a retry continues where it stopped. Then a re-read, and the campaign stops being new.
- The Keitaro adapter's payloads keep whatever else the stream carries, from `raw`. They change only `offers` on the offers stream, and only the country filter's `payload` on the geo stream.
- `POST /sync/push-all` pushes campaign by campaign and reports a result for each one. A failure doesn't stop the rest.
- `POST /campaigns/{id}/resolve`, plus `sync_log` entries for every step.

## Phase 6: Dashboard

- `scripts/gen-api-types.sh` dumps the API schema and runs `openapi-typescript`, writing `dashboard/app/api/types.ts`.
- Header: Fetch streams (with a spinner and the last fetch time), New campaign, the pending count, Push all and Cancel all.
- The New campaign dialog: name, alias, geo (multi-select of countries), domain, group and source selects, and an offers search. An error stays in the dialog.
- Campaign cards:
  - the header with alias, domain, group, source and badges (New, Not synced, Conflict, Archived, Unsupported layout);
  - the geo stream's country multi-select, with pending markers;
  - the offers table with share, pin, remove and change markers;
  - Add offer with a search combobox;
  - the Removed list with Bring back;
  - Push to KT and Cancel.
- A **Show: Ours / All** toggle, with Ours as the default. Ours means a name that starts with `CAMPAIGN_NAME_PREFIX`. The choice is kept in the URL and in `localStorage`.
- Filters by group, domain and source, a name search, and Pending only.
- Dialogs for confirmations. Validation errors are shown on the card, and Push is disabled while the draft is invalid.
- Small page components, with children under `components/`.

## Phase 7: Integration Tests

- Core flow tests against an in-memory fake `TrackerProvider`, with no HTTP.
- A fake Keitaro service (FastAPI stub on the fixtures, with a "fail on the next call" switch) in `docker/test/compose.yaml`, for the adapter end to end.
- `scripts/e2e-test.sh` runs the full flow from [DESIGN: Testing](docs/DESIGN.md#testing).

## Later (after MVP)

- Login and auth.
- Production deploy.

## Decisions

1. **Geo**: the geo stream's countries are set per campaign (`AU` by default) and stay editable after creation (draft → push).
2. **Campaign fields** (name, alias, domain, group, source) are set only at creation.
3. **Offers stream** has no country filter for now.
4. **Scope**: AdRobot manages every campaign on the (shared) tracker. The dashboard shows "ours" by default; see Phase 6.
5. **MVP**: local only, no auth, no deploy, no Redis (the tracker lists are cached in the `api`'s memory).
6. **Architecture**: DIP and Hexagonal (Ports and Adapters) for every external service. The core depends on ports it owns, and vendors live in adapter packages. See [DESIGN: Architecture](docs/DESIGN.md#architecture-ports-and-adapters).

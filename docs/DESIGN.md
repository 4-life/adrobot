# AdRobot — Design

The detailed design behind the [README](../README.md). The build order is in the [PLAN](../PLAN.md).

## Services

| Service | Role |
|---|---|
| `api` | FastAPI. Handles fetch, the drafts, push, and tracker lookups. It is the only service that talks to the tracker. |
| `dashboard` | SSR React. It talks only to the `api`. |
| `postgres` | The database. |
| `migrate` | One-shot `alembic upgrade head`. Every service waits for it to finish. |

```
owner ─▶ dashboard ─▶ api ─▶ TrackerProvider (port) ─▶ Keitaro adapter ─▶ Keitaro Admin API
                       │
                       └─▶ Postgres (synced snapshot + draft)
```

The `api` keeps an in-memory cache, 60 s, for the tracker lists: offers, domains, groups and sources.

## Architecture: Ports and Adapters

The backend follows the **Dependency Inversion Principle** and **Hexagonal Architecture (Ports and Adapters)**. The core never depends on Keitaro. It depends on a port that it owns, and Keitaro is one adapter behind that port.

| Layer | Where | Knows Keitaro? |
|---|---|---|
| **Port** | `app/tracker/port.py`: the `TrackerProvider` protocol, the domain types (`TrackerCampaign`, `TrackerStream`, `TrackerOffer`, `LookupItem`) and `TrackerError` | no |
| **Core services** | `app/campaigns/` (merge, pending, sync; shares, push next) | no: only the port |
| **Adapter** | `app/tracker/keitaro/`: generated models, overrides, the HTTP client, layout detection, and `adapter.py` (Keitaro ↔ domain types) | yes: the only place |
| **Composition root** | `app/tracker/factory.py` picks the adapter from `TRACKER` (`keitaro`), and `app/api/deps.py` injects it | — |
| **Inbound adapter** | `app/api/`: the HTTP routes | no |

- The database and the API are vendor-neutral: `external_id`, `offer_id`, `state`, `/tracker/*`.
- `streams.raw` stores the tracker's own stream data, opaque to the core. It's handed back to the adapter on push, so a push changes only what AdRobot manages.
- **Adding another tracker**: a new package `app/tracker/<name>/` implementing `TrackerProvider`, plus one branch in `factory.py`. Merge, drafts, shares and the UI don't change.
- Core tests use port types or a fake provider. Only the adapter's own tests touch Keitaro's JSON.

## Creating a Campaign

**New campaign** opens a form with these fields:

| Field | Keitaro | Source |
|---|---|---|
| Name | `name` | prefilled as `CAMPAIGN_NAME_PREFIX` + N (`test_name_campaign1`, `…2`), where N is 1 + the highest N among existing campaigns and drafts; can be edited |
| Alias | `alias` (required by Keitaro, used in the URL `https://<domain>/<alias>`) | generated from the name plus a random suffix; can be edited |
| Geo | the geo stream's `country` filter | country codes, `AU` by default |
| Domain | `domain_id` | `GET /domains` |
| Group | `group_id` | `GET /groups?type=campaigns` |
| Traffic source | `traffic_source_id` | `GET /traffic_sources` |
| Offers | the offers stream's `offers` | searched in `GET /offers` |

Saving creates the campaign **as a draft** with a "New, not in Keitaro" badge. Its offers can be edited like any other campaign's.

**Push to KT** creates the campaign in three steps. The Keitaro ID returned by each step is stored as soon as it arrives, so a push that fails partway resumes from the step that failed and never creates a duplicate.

1. `POST /campaigns`: name, alias, domain, group and source, with `type: position`.
2. `POST /streams` for the geo stream:
   - position 1, `schema: redirect`, `action_type: http`, `action_payload: GEO_REDIRECT_URL` (`https://google.com` by default);
   - `filters: [{name: country, mode: accept, payload: <geo>}]`.
3. `POST /streams` for the offers stream: position 2, the `offers` array with the calculated shares.

The stream payloads are built from the Keitaro schema. The first real push (`test_name_campaign1`) checks them: AdRobot re-reads what Keitaro stored, and those responses become the test fixtures (Phases 4–5 of the [PLAN](../PLAN.md)).

## Offers and Shares

Keitaro stores offers on the stream as `offers: [{offer_id, share, state}]`, where `share` is an integer percentage. The active offers' shares always add up to 100.

- **Unpinned** offers split what's left equally: 2 offers get 50% each, 4 get 25% each.
- A **pinned** offer keeps its share fixed however many offers are added. The unpinned ones split `100 − sum(pinned)`.
- Rounding uses the largest-remainder method, so 3 offers get 34 / 33 / 33. The extra point goes to the top offers in list order.
- A draft is invalid, and can't be pushed, when:
  - the pinned shares add up to more than 100;
  - every offer is pinned and the shares don't add up to exactly 100;
  - there are unpinned offers but nothing is left for them;
  - there are no active offers.
- Shares are recalculated on every draft change (add, remove, pin, unpin, bring back). Right after a fetch, a stream keeps Keitaro's actual shares until the first edit.

## Draft and Sync

AdRobot keeps two states for each editable part of a campaign: the geo stream's countries, and the offers stream's offers.

| State | What it is |
|---|---|
| **synced** | What Keitaro had at the last fetch or push |
| **draft** | What AdRobot will push |

A campaign is **pending** when any draft differs from its synced state. A pending campaign shows:

- a "Not synced" badge on the campaign;
- the change on each offer row: added, removed, share changed, pinned changed;
- the added and removed countries on the geo stream;
- a pending-campaign count in the header.

A new campaign is always pending.

**Fetch streams**
- Reads all campaigns, their streams (8 campaigns at a time) and offers, plus the offer and source names, and replaces every synced state. Domain and group names come with each campaign.
- **Layout**: exactly two live streams. The first has a `country` filter and no offers (the geo stream), and the second isn't a plain redirect (the offers stream). Disabled offers count as removed. Any other campaign is shown read-only as **Unsupported layout**.
- An offer that is new in Keitaro is appended to the draft too, even when the draft has pending changes.
- A campaign with pending changes keeps its draft.
- If Keitaro changed that stream since the last fetch, the campaign is flagged **Conflict**. You then choose **Keep my draft** (it will be pushed over Keitaro's version) or **Cancel changes**.
- A campaign archived in Keitaro (state `deleted`, or missing from the list) is shown as **Archived in Keitaro** and is read-only.

**Push to KT**
- Works per campaign, or **Push all** for every pending campaign.
- For an existing campaign, it first re-reads each changed stream (`GET /streams/{id}`). If a stream differs from its synced state, the push is refused with `409` and the campaign is flagged Conflict.
- Otherwise it sends `PUT /streams/{id}` for each changed stream: the offers array for the offers stream, the country filter for the geo stream.
- It then re-reads the streams and sets synced and draft both to what Keitaro returned. Anything Keitaro stored differently from what was sent is reported as `mismatch` (and logged), and the draft follows Keitaro.
- A push updates only what AdRobot manages: the offers stream's `offers`, and the geo stream's country filter (its other filters are sent back unchanged, with their ids).
- An empty geo country list can't be pushed (`422`).

**Cancel changes**
- Sets draft back to synced, for one campaign or for all. A new campaign's draft is deleted.

## Removed Offers

- **Removed in AdRobot**: the offer is marked removed in the draft (pending), and its share goes to the others. After a push it stays listed under **Removed** with a **Bring back** button.
- **Removed in Keitaro**: on the next fetch, an offer that was in the synced state but is no longer on the stream is listed under **Removed** with **Bring back**. The row notes that it was removed in Keitaro.
- **Bring back**: returns the offer to the draft with its last pinned setting, and the change is pending until pushed.
- Removed offers are kept per campaign, indefinitely.

## Adding Offers

Keitaro's `GET /offers` has no search parameter, so the `api` loads the whole list, caches it in memory for 60 s, and searches it by name or ID.

- Only offers with `state` `active` are listed.
- Offers already active in the stream are shown disabled.
- A removed offer can't be added from the search; use its **Bring back** button instead.

Domains, groups and traffic sources are cached the same way.

## Keitaro Integration

- **Connection**:
  - Base URL: `KEITARO_URL` + `/admin_api/v1`.
  - Auth: the `Api-Key: <KEITARO_API_KEY>` header.
  - Both values come from `.env`.
  - Keitaro answers `402` if the edition doesn't include the Admin API.
- **Schema**: `backend/app/tracker/keitaro/openapi.yaml` (OpenAPI 3.0.0, the Keitaro Admin API v1). It is **not in the repo**: it's Keitaro's to publish, not ours, so it's git-ignored. Download it from your own Keitaro's Admin API docs into that path when you need to regenerate the models. `SCHEMA_VERSION` notes the Keitaro version it came from.
- **Models**: `scripts/gen-keitaro.sh` runs `datamodel-code-generator` (YAML input, Pydantic v2 output, unknown fields allowed) and writes `backend/app/tracker/keitaro/models.py`, formatted with Ruff. The generated file is committed (CI has no schema) and never edited by hand.
  - `scripts/check.sh` regenerates it when the schema is present locally (commit any change). Without the schema, as in CI, the committed file is used.
  - Data that doesn't match the schema doesn't crash: the adapter turns it into a tracker error (`502`) naming the field path, never its values. Fix it in `models_overrides.py`.
  - `models_overrides.py` fixes the places where the schema is wrong or incomplete. Known so far:
    - `Campaign` has no `domain_id`; only `CampaignRequest` does. The real response does include `domain_id`, along with `domain` and `group` names.
    - `Campaign.bind_visitors` is an enum `s` / `sl` / `slo`, but Keitaro sends `""` when binding is off.
    - `Offer.values` and `Offer.country` are lists, but Keitaro sends `""` when they're empty.
    - `group_id` is `integer` in `Campaign` but `string` in `CampaignRequest` / `DomainRequest`.
    - `Filter.payload` is typed as a string, but a `country` filter carries a list.
    - `Filter.oid` is typed as a string, but Keitaro sends a number.
    - `Report.rows` is typed as an array of strings (not used).
- **Endpoints used**:

  | Endpoint | Used for |
  |---|---|
  | `GET /campaigns` (`offset` / `limit`, paged) | fetch |
  | `GET /campaigns/{id}/streams` | fetch |
  | `GET /streams/{id}` · `PUT /streams/{id}` | push (conflict check, write) |
  | `POST /campaigns` · `POST /streams` | create a campaign |
  | `GET /offers` | offer search and offer names |
  | `GET /domains` · `GET /groups?type=campaigns` · `GET /traffic_sources` | the create form and the names on cards |

- **Client**: `backend/app/tracker/keitaro/client.py`, hand-written.
  - Async `httpx` with timeouts.
  - Reads are retried on 5xx and network errors. Writes are not; a failed write is resumed by the next push.
  - Returns the generated models. Keitaro's `{error}` body becomes a typed `KeitaroError`.
  - The API key is never logged.
- **Dashboard types**: the dashboard calls only AdRobot's API. Its types are hand-written for now in `dashboard/app/features/campaigns/types.ts`, mirroring `backend/app/api/schemas.py`. Later, `scripts/gen-api-types.sh` can generate them from `app.openapi()` (which isn't served over HTTP).

## Dashboard

React Router SSR. Only the dashboard server talks to the API: route loaders and actions do, through `app/lib/api.server.ts`. The browser never calls the API directly.

**Structure** (pages only compose; components are split into shared and feature ones):

| Where | What |
|---|---|
| `app/routes/home.tsx` | The page. The loader reads the campaigns and the redirect URL (an API error is shown above them). The single action runs every campaign form (`intent`). It composes the shared Header and Footer with the feature components |
| `app/routes/offers-search.ts`, `new-campaign-data.ts` | Resource routes for fetchers: offer search, and the New campaign dialog's defaults and selects |
| `app/components/shared/` | Feature-agnostic UI: `Header`, `Footer`, `Button`, `Badge`, `Dialog` (native `<dialog>`), `ConfirmDialog` (never `window.confirm`), `Notice`, `Spinner`, `Field` / `TextInput` / `Select` |
| `app/features/campaigns/` | The campaigns feature. `api.server.ts` has the API calls, `actions.server.ts` the intent dispatcher, `types.ts` the API shapes, and `filters.ts` / `countries.ts` hold pure helpers. `useCampaignAction.ts` posts one action per component, with its own pending state and result |
| `app/features/campaigns/components/` | `CampaignsView`, `CampaignFilters`, `CampaignList`, `CampaignCard`, `CampaignBadges`, `CampaignActions`, `ConflictBanner`, `GeoEditor`, `OffersTable`, `OfferRow`, `ShareCell`, `ChangeBadge`, `PinControl`, `RemovedOffers`, `OfferSearch`, `AddOffer`, `ActionFeedback`, `SyncBar`, `PushAllResults`, `NewCampaignDialog` |

**Page**:

- **Header**:
  - **Fetch streams**, with the last fetch time.
  - **New campaign**.
  - The pending count, with **Push all** and **Cancel all**.
- **Campaigns**: a card per campaign. After every action the loader reloads them.
  - The header shows its name, Keitaro ID (or "New"), alias, domain, group and source, the Not synced / Conflict / Archived badge, **Push to KT** and **Cancel changes**.
  - **Geo stream**: the countries (multi-select, changes marked pending) and the redirect target.
  - **Offers stream**: a table with offer, share %, pin toggle with share input, change marker and remove button, plus **Add offer** (search) and a collapsible **Removed** list with **Bring back**.
  - **Show: Ours / All**, set to **Ours** by default. It's a filter only, and every campaign can be managed under All. The choice is remembered in the browser. A campaign is "ours" when its name starts with `CAMPAIGN_NAME_PREFIX`.
  - Filters by group, domain and source, a name search, and "Pending only".
- Confirmations (Push all, Cancel, Keep my draft) use a Dialog, never `window.confirm`.

## API

There's no auth: the MVP runs only on the local machine (see [Security](#security)). There's no `/docs` or `/openapi.json` over HTTP.

| Endpoint | Purpose |
|---|---|
| `GET /health` | health check (also checks Postgres), for manual checks; nothing polls it |
| *errors* | `404` unknown campaign / stream / offer, `409` read-only campaign (archived, unsupported layout) or an edit that doesn't apply (already removed, …), `422` invalid input, `502` tracker error; body `{detail}` |
| `POST /sync/fetch` | Fetch streams. Returns the campaigns flagged Conflict. |
| `GET /campaigns?scope=ours\|all` | campaigns (`ours` by default; each carries `ours`) with their streams, draft offers, removed offers, pending/conflict/new/archived flags; per offer its `change` (`added` / `removed` / `share`), per stream `geo_added` / `geo_removed` and `errors` (why the draft can't be pushed). Every edit endpoint returns the campaign in this shape |
| `GET /campaigns/defaults` | prefills the New campaign form: the next name, a generated alias, `[DEFAULT_GEO]`, the redirect URL |
| `POST /campaigns` | `{name?, alias?, countries?, domain_id, group_id?, traffic_source_id?, offer_ids[]}` → `201` with a new **draft** campaign (New, pending). Blank name/alias/countries use the defaults. Domain, group, source and offers must be active in the tracker (`422`); a duplicate alias is `409` |
| `GET /tracker/offers?q=` · `GET /tracker/domains` · `GET /tracker/groups` · `GET /tracker/sources` | tracker lookups (cached for 60 s) |
| `PUT /streams/{id}/geo` | `{countries[]}`: set the geo stream's countries in the draft |
| `POST /streams/{id}/offers` | `{offer_id}`: add an offer to the draft. `409` if it's already active or removed (use bring back). |
| `PATCH /streams/{id}/offers/{offer_id}` | `{pinned, pinned_share}` (1-100). `offer_id` is the tracker's offer id; `{id}` is AdRobot's stream id |
| `DELETE /streams/{id}/offers/{offer_id}` | remove the offer in the draft |
| `POST /streams/{id}/offers/{offer_id}/restore` | Bring back |
| `POST /campaigns/{id}/push` | Push to KT → `{pushed, mismatch, campaign}`. `pushed: false` when nothing was pending; `mismatch` lists where the tracker stored something other than what was sent. `409` on Conflict (the tracker changed since the last fetch: the campaign is flagged and its synced state updated), `422` on an invalid draft, `502` with the tracker's error (a new campaign resumes from the failed step on the next push) |
| `POST /sync/push-all` | every pending campaign, one by one → `{results: [{campaign_id, name, ok, error, mismatch}]}`; a failure doesn't stop the rest |
| `POST /campaigns/{id}/cancel` · `POST /sync/cancel-all` | Cancel changes: `{deleted, campaign}` (a new draft campaign is deleted) / `{cancelled, deleted}` |
| `POST /campaigns/{id}/resolve` | `{keep_draft}`: `true` clears Conflict (the next push goes over the tracker's version), `false` cancels the draft → `{deleted, campaign}`. `409` without a conflict |

## Postgres

| Table | Content |
|---|---|
| `campaigns` | `external_id` (the tracker's id; null until pushed), name, alias, `domain_id`, `group_id`, `traffic_source_id` plus their names, `state` (`active` / `disabled` / `archived`), `layout_supported`, `fetched_at`, `conflict`, `is_new` |
| `streams` | `external_id` (null until pushed), campaign, role (`geo` / `offers`), position, `synced_geo` / `draft_geo` countries (geo stream), `raw`: the tracker's stream data from the last fetch or push (read only by the adapter) |
| `stream_offers` | stream, `offer_id` (the tracker's), offer name, `position` (list order), `synced_active` / `synced_share` (on the tracker's stream), `draft_active` / `draft_share` (`draft_active = false`: under Removed), `pinned`, `pinned_share`, `removed_by` (`adrobot` / `tracker`), `removed_at` |
| `sync_log` | each fetch, create and push: time, campaign, step, result, Keitaro's error, a diff summary |

"Pending" is calculated, not stored: a campaign is pending when it is new, when its draft geo countries differ from the synced ones, or when any of its offer rows' draft state, share or pin differs from the synced one. Alembic migrations run automatically before the services start.

## Configuration

Everything is set in `.env`. `.env.example` lists every variable.

| Variable | |
|---|---|
| `TRACKER` | the tracker adapter (`keitaro`, the only one so far) |
| `KEITARO_URL` | the Keitaro panel's address without a path, e.g. `https://tracker.example.com` (required) |
| `KEITARO_API_KEY` | an Admin API key created in Keitaro (required) |
| `GEO_REDIRECT_URL` | where the geo stream sends visitors (`https://google.com`) |
| `DEFAULT_GEO` | the default for the create form's Geo field (`AU`) |
| `CAMPAIGN_NAME_PREFIX` | the prefix of new campaign names, and the "Ours" filter (`test_name_campaign`) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | the local database |
| `API_PORT` / `DASHBOARD_PORT` | `8000` / `3000` |

- The compose files set explicit project names (`adrobot-local`, `adrobot-test`).
- After a code change, run `docker compose -f docker/local/compose.yaml up -d --build` again.

## Testing

`scripts/check.sh` regenerates the Keitaro models (when the schema is present), then runs Ruff, mypy, the unit tests and the dashboard typecheck. GitHub Actions (`.github/workflows/ci.yml`) runs the same script on every push and pull request, using the committed `models.py`. It installs exactly `uv.lock` and `package-lock.json`, so both must be committed. The README badge shows the latest run.

- **Unit** (no DB, Docker or Keitaro):
  - share calculation (pins, rounding, the validation cases);
  - the diff between draft and synced;
  - fetch merging (removed in Keitaro, conflicts, archived campaigns);
  - push and create payload building, including resuming a failed create;
  - the Keitaro client against recorded JSON fixtures.
- **Integration** (`scripts/e2e-test.sh` with `docker/test/compose.yaml`, always `down -v` afterwards): runs against a **fake Keitaro**, a small FastAPI stub on the fixtures, never the real tracker. The test runs:
  1. Create a campaign, then push it. Check the stub received a campaign and two streams.
  2. Fetch.
  3. Add, pin and remove offers, change the geo countries, then cancel.
  4. Edit again, then push. Check the shares and the geo filter.
  5. Remove an offer in the stub, then fetch. It should show as removed in Keitaro.
  6. Bring it back, then push.
  7. A conflict on push.
  8. Make the stub fail mid-create, then push again. It should resume.

## Security

- **No auth**: anyone who can reach the dashboard can push to Keitaro. All ports are bound to `127.0.0.1`, so only this machine can reach them. Never expose them to a network.
- The Keitaro API key is used only by the `api`. It is never sent to the browser, logged, or included in error messages or `sync_log`.
- `.env` is git-ignored, and `.env.example` lists the variables without real values.
- Containers run as unprivileged users.

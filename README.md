# FlightTracker

[![CI](https://github.com/PriyanjanMitra/FlightTracker/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/PriyanjanMitra/FlightTracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Ruff](https://img.shields.io/badge/Ruff-lint-7A1FA2?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![pytest](https://img.shields.io/badge/pytest-passing-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)

A live flight-tracking dashboard. An ingestion pipeline periodically pulls
aircraft state vectors from the [OpenSky Network](https://opensky-network.org),
stores them in SQLite, and serves them to a React + Leaflet map. Selecting an
aircraft enriches the view with the aircraft's model and operating airline,
aviation-grade details for that flight, its trail, and a Dark-Souls-themed
day/night overlay.

**This document is both a quick-start and a deep reference.** It explains the
architecture, every module, the data model, configuration, testing, and the API
contract — enough that a new developer can reason about the whole system.

## Table of contents

- [Features](#features)
- [High-level architecture](#high-level-architecture)
- [Project layout](#project-layout)
- [How the backend works](#how-the-backend-works)
  - [CLI entry point](#cli-entry-point--mainpy)
  - [Configuration](#configuration)
  - [The ingestion pipeline](#the-ingestion-pipeline)
  - [Controller / Service / Repository](#controller--service--repository)
  - [Providers](#providers)
  - [ORM model & SQLite](#orm-model--sqlite)
  - [The REST API](#the-rest-api)
- [How the frontend works](#how-the-frontend-works)
- [Data model](#data-model)
- [End-to-end data flow](#end-to-end-data-flow)
- [Quick start](#quick-start)
- [Configuration reference](#configuration-reference)
- [Building the aircraft registry](#building-the-aircraft-registry)
- [Commands](#commands)
- [Development](#development)
- [Testing](#testing)
- [API reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- **Live map** — dark-themed Leaflet map. Aircraft are drawn as plane glyphs
  rotated to their heading and colored by altitude (green → red gradient).
- **Clustering** — dense areas collapse into numbered clusters that expand as
  you zoom, keeping the map responsive at world scale.
- **Day / night overlay** — a twilight terminator renders the earth's lit
  hemisphere and updates every minute.
- **Aircraft list** — sortable, filterable sidebar with climb / descend / level
  status badges and live aircraft counts.
- **Flight detail** — click any aircraft to isolate it, fly the map to it, draw
  its position trail, and read its altitude, speed, heading, vertical speed,
  aircraft model (e.g. *Boeing 777-200LR*), registration, and operating airline.
- **Themes** — a *Radar* and *Bonfire* (Dark Souls) visual theme. Switching to
  Bonfire plays a "YOU DIED" sting, greys out the map, and shows a rising-embers
  transition; the whole UI re-skinned with a gold-on-black palette and a serif
  font.
- **Mock mode** — run the entire frontend against deterministic synthetic data
  with no backend at all.

## High-level architecture

Two processes talk to one SQLite database and a separate aircraft-registry
index. Nothing else is shared.

```mermaid
flowchart LR
    subgraph Writer
        P[Pipeline: APScheduler] --> O[OpenSky Provider]
        O --> SV[IngestionService]
        SV --> R[FlightStateRepo] -- upsert --> S[(SQLite flight_states)]
    end
    subgraph Reader
        A[FastAPI] -- read --> S
    end
    subgraph Enrichment
        A -. 'flight-info' --> AD[adsbdb API]
        A -. type fallback --> REG[(aircraft_registry.db)]
    end
    U[React + Leaflet] -- "/api/*" --> A
```

- **Writer side** — an APScheduler job *always* fetches the full state snapshot
  from OpenSky, then the repository upserts rows keyed on `(icao24, last_contact)`.
- **Reader side** — FastAPI exposes read-only endpoints over the same file, so
  SQLite must run in **WAL mode** to allow a concurrent writer and multiple
  readers (see [ORM model & SQLite](#orm-model--sqlite)).
- **Enrichment** — when a user selects an aircraft, the frontend calls
  `/api/flight-info`, which queries the adsbdb API for airline/aircraft details
  and falls back to a local registry for the aircraft typecode.

## Project layout

```text
FlightTracker/
├─ main.py                     # thin entry point delegating to the CLI
├─ run.sh                      # one-command local orchestration
├─ pyproject.toml              # Python metadata, ruff/mypy/pytest config
├─ .env                        # local settings (git-ignored)
├─ .env.example                 # documented env-template
├─ credentials.json             # optional OpenSky auth (git-ignored)
├─ data/
│  ├─ flight_tracker.db        # SQLite state store (git-ignored)
│  └─ aircraft_registry.db     # offline icao24 → typecode index
├─ src/flight_tracker/
│  ├─ main.py                  # argparse CLI (init-db, ingest-once, ...)
│  ├─ config.py                # Pydantic settings from env
│  ├─ logging.py               # log config
│  ├─ pipeline.py               # APScheduler wiring
│  ├─ api.py                    # FastAPI app
│  ├─ models/
│  │  ├─ dtos.py               # runtime DTOs / Pydantic response schemas
│  │  ├─ orm.py                 # SQLAlchemy FlightState + engine helpers
│  │  └─ enums.py                # shared enums / labels
│  ├─ controllers/
│  │  └─ ingestion_controller.py
│  ├─ services/
│  │  └─ ingestion_service.py
│  ├─ repository/
│  │  └─ flight_state_repo.py
│  └─ providers/
│     ├─ opensky_provider.py   # reads OpenSky states API
│     ├─ adsbdb_provider.py    # reads adsbdb aircraft/airline info
│     └─ aircraft_registry.py  # local typecode lookup
├─ scripts/
│  ├─ init_db.py               # DB bootstrap helper
│  └─ build_aircraft_index.py  # build aircraft_registry.db from OpenSky CSV
├─ dashboard/                 # React + Vite + TypeScript frontend
│  ├─ index.html
│  ├─ vite.config.ts
│  ├─ public/you-died.mp3
│  └─ src/
│     ├─ main.tsx         # React entry, ThemeProvider
│     ├─ theme.tsx        # theme definitions + context
│     ├─ api.ts           # Axios client + types; mock helpers
│     ├─ App.tsx          # root: polling, selection, map composition
│     ├─ Sidebar.tsx      # aircraft list
│     ├─ AircraftMarkers.tsx
│     ├─ TrailLayer.tsx   # polyline trail
│     ├─ DayNightOverlay.tsx
│     ├─ ThemeSwitchOverlay.tsx
│     ├─ SelectionDetail.tsx
│     ├─ Logo.tsx
│     ├─ sound.ts         # autoplay "YOU DIED"
│     └─ index.css
└─ tests/                 # pytest suite (backend)
```

## How the backend works

The backend is a small layered Python package. Data flows in one direction at
write time and crosses the DB boundary back out at read time:

**CLI → controller → service → provider** for ingestion
**HTTP → FastAPI → repository → DB** for reads

Everything is wired with plain constructor injection — no DI framework.

### CLI entry point — `main.py`

`main.py` is an `argparse` CLI. Each subcommand maps to one function:

- `init-db` — creates/upgrades the SQLite schema (`init_db`).
- `ingest-once` — performs a single OpenSky fetch and persists it. Useful for
  debugging without running the scheduler.
- `run-pipeline` — starts the periodic scheduler in the foreground.
- `serve-backend` — launches uvicorn on `0.0.0.0:8000`.

`run-pipeline` registers `SIGINT`/`SIGTERM` handlers that call
`scheduler.shutdown(wait=False)` and exit, so `Ctrl+C` stops cleanly instead of
killing the process mid-write.

### Configuration — `config.py`

A Pydantic `Settings` class reads environment variables (from `.env`) and any
typed attributes:

| Env var | Default | Purpose |
| ------- | ------- | ------- |
| `OPENSKY_BBOX` | *(empty = whole world)* | `lat_min,lat_max,lng_min,lng_max` |
| `OPENSKY_POLL_SECONDS` | `90` | ingestion poll interval |
| `OPENSKY_USERNAME` / `OPENSKY_PASSWORD` | *(empty)* | optional auth fallback |
| `AIRCRAFT_REGISTRY_DB` | `data/aircraft_registry.db` | type-lookup index |
| `DATABASE_URL` | `sqlite:///data/flight_tracker.db` | SQLAlchemy conn string |
| `LOG_LEVEL` | `INFO` | log verbosity |
| `LOG_FORMAT` | `text` | `text` or `json` |
| `CORS_ORIGINS` | `*` | comma-separated allowed origins |

### The ingestion pipeline

`pipeline.py` builds an APScheduler `BackgroundScheduler`:

- **`ingest_states`** — runs `IngestionController.handle_tick()` every
  `opensky_poll_seconds`. Configured with `max_instances=1`, `coalesce=True`,
  and a `misfire_grace_time`, so slow or skipped ticks never pile up.
- **`prune_states`** — hourly, calls `repo.prune_old_states()` to delete rows
  older than 24 h, keeping the DB bounded.

### Controller / Service / Repository

**`IngestionController`** owns the `session_factory` and the `OpenSkyProvider`.
Each tick opens a *fresh* session, so an error in one tick never leaks session
state into the next.

**`IngestionService.run_once()`** calls `provider.fetch_states(bbox)`, converts
each `FlightStateDTO` into a plain dict (adding a `fetched_at` timestamp), and
hands the list to `repo.upsert_many`.

**`FlightStateRepo`** encapsulates every query against `flight_states`:

- `upsert_many` — a bulk SQLite `INSERT ... ON CONFLICT DO UPDATE` keyed on
  `(icao24, last_contact)`. The same aircraft recontacted at the same second is
  updated, never duplicated.
- `latest_states(limit, recent_minutes)` — one row per aircraft: join against a
  subquery of the max `fetched_at` per `icao24`, then filter to
  `last_contact` in the recent window. This powers `/api/states`.
- `states_in_window(start, end)` — every row whose `last_contact` falls in a
  range, powering the trail polyline.
- `prune_old_states` / `count` — housekeeping helpers.

### Providers

Providers are the only layer that talks to the outside world, isolated behind a
narrow interface so the rest of the app never makes network calls.

**`opensky_provider.py`** — the live flight source:

- **Credentials** — `_load_auth()` reads `credentials.json` from the project
  root first (accepting `username`/`password` *or* `clientId`/`clientSecret`),
  falling back to the env vars, and qualifies for the authenticated OpenSky tier.
- **OAuth2 token** — validated credentials are exchanged for a bearer token via
  the OpenSky auth endpoint, cached until near expiry, and refreshed lazily.
- **Rate limiting** — anonymous access is ~10 requests/min. On HTTP 429 it reads
  `x-rate-limit-retry-after-seconds` (or `Retry-After`), stores a cooldown, and
  returns an empty list until it passes. Subsequent ticks skip the network call.
- **Retries** — transient `ConnectionError`/`Timeout` retried up to 3 times with
  exponential backoff; a 401 refreshes the token once.
- **Parsing** — `_parse_states()` maps OpenSky's array-of-arrays payload (each
  row indexed by position) onto the typed `FlightStateDTO`, skipping malformed
  rows rather than aborting the whole snapshot.

**`adsbdb_provider.py`** — enrichment. `fetch_flight_info(icao24, callsign)`
queries `https://api.adsbdb.com/v0/aircraft/{icao24}` for the aircraft's model,
manufacturer, registration, owner, and the operating airline. Callers treat a
miss (HTTP 404 or a parse failure) as `None`.

**`aircraft_registry.py`** — a read-only local SQLite index of OpenSky's public
aircraft database. It resolves `icao24 → (typecode, manufacturer, model,
registration, operator)` with per-thread connections (SQLite is
thread-specific) and returns `None` when the index is missing or the aircraft
is unknown. See [Building the aircraft registry](#building-the-aircraft-registry).

### ORM model & SQLite

`FlightState` is the only SQLAlchemy table. Composite indexes support the two
hot queries: unique `(icao24, last_contact)` for the upsert, and
`(icao24, fetched_at)` for the "latest per aircraft" join.

`create_engine_safe()` matters: it uses `NullPool` (no shared connections across
the writer/readers), sets a 10 s busy timeout, and enables SQLite **WAL mode**
via `PRAGMA journal_mode=WAL` so the pipeline writer and the HTTP readers can
operate concurrently without locking each other out.

`init_db()` deduplicates existing rows and back-fills missing indexes on older
databases, then creates any missing tables.

### The REST API

`api.py` defines a FastAPI app with CORS from `CORS_ORIGINS`. Responses are
cached with a tiny monotonic TTL wrapper to absorb frontend polling.

- `GET /api/states` — latest aircraft. Cached 2 s. Drops rows with no
  coordinates and converts altitude meters→feet.
- `GET /api/trails?minutes=N` — position history per icao24 within the last N
  minutes.
- `GET /api/flight-info` — enrichment. Validates the callsign format, queries
  adsbdb, and prefers the local aircraft registry for the typecode when adsbdb
  is unknown. Returns `{aircraft, airline}` (origin/destination routing was
  removed).

## How the frontend works

The dashboard is a React 18 + Vite + TypeScript SPA. `main.tsx` mounts
`<ThemeProvider>` then `<App/>`. Data flows in via public HTTP calls from
`api.ts`.

**`App.tsx`** is the root. It owns `states` (all aircraft) and `selected`
(the chosen `icao24`), polls `fetchStates()` every **60 s** (and a
`MapClickHandler` deselects on a background click). It lays out the sidebar plus
the `<MapContainer>` (locked to `maxBounds=[[-85,-180],[85,180]]`), and the
`FitWorldMinZoom` kid computes `minZoom = ceil(log2(maxDimension/256))` so the
whole world always fills the viewport. `MapFlyTo` re-flies only when the
*selected aircraft changes* (not per position tick).

**`Sidebar.tsx`** — a dark, sortable, search-filterable table of all aircraft
(by callsign, altitude, speed, heading, country), with live climb / descend /
level badges and counts.

**`AircraftMarkers.tsx`** — renders one Leaflet marker per aircraft inside a
`MarkerClusterGroup`. Each marker is a plane glyph rotated to its quantized
(5°) heading; heading quantization means icons are cached and reused instead of
recreated every poll. Icon colour follows the theme's altitude gradient
(green → red). The selected aircraft gets a larger, glowing marker and the UI
`grayscale` alone. The `theme` context (in `theme.tsx`) supplies everything
color/font related, with two themes — **Radar** (blue/graphite) and **Bonfire**
(gold/black, Cinzel serif).

**`DayNightOverlay.tsx`** — a `leaflet.terminator` layer that renders the
terminator line; `setTime` refreshes it every 60 s. In Bonfire mode the night
side is pure black; in Radar dark blue, matching the palette.

**`TrailLayer.tsx`** — fetches `/api/trails` on selection and draws the
selected flight's recent positions as a themed polyline.

**`SelectionDetail.tsx`** — bottom slide-up panel for the selected flight:
callsign, aircraft (type, manufacturer, registration), airline name, a
telemetry grid (altitude, speed in knots, heading, vertical status), and
metadata (country, ICAO, category, last contact). It calls `/api/flight-info`
when a callsign exists.

**`ThemeSwitchOverlay.tsx` + `sound.ts`** — when switching from Radar to
Bonfire, `sound.ts` plays `you-died.mp3`, the whole UI is briefly grayscaled and
a rising-embers "THEME SWITCHED" overlay fades in over ~8 s.

**`index.css`** — global reset, map tiles darkened via a CSS filter on
`.leaflet-tile-pane` (`brightness(0.72) saturate(0.7)`), scrollbar + ember
keyframe animations.

## Data model

### `flight_states`

One row per aircraft observation; the last row per `(icao24, last_contact)`
represents the latest known state.

| Column | Type | Notes |
| ------ | ---- | ----- |
| `id` | INTEGER PK | autoincrement |
| `icao24` | String(6) | Mode S hex identity, indexed |
| `callsign` | String(8) | e.g. `UAL123` |
| `origin_country` | String(64) | registration country |
| `longitude` / `latitude` | Float | position |
| `baro_altitude` | Float | metres (converted to ft in API) |
| `velocity` / `heading` | Float | ground speed; degrees |
| `vertical_rate` | Float | m/s |
| `on_ground` | Boolean | |
| `last_contact` | Integer | epoch seconds of the observation |
| `category` | Integer | OpenSky `category` 0..19 |
| `fetched_at` | DateTime | when our ingest stored the row |

Indexes: unique `(icao24, last_contact)` (upsert key), `(icao24, fetched_at)`,
and `(last_contact)` (prune/range).

## End-to-end data flow

1. **Ingest** (every `OPENSKY_POLL_SECONDS`): OpenSky `states/all` → parsed into
   `FlightStateDTO`s → `IngestionService.run_once()` → `FlightStateRepo.upsert_many()`
   commits into SQLite (WAL).
2. **List** (every 60 s in the browser): `GET /api/states` reads `latest_states()`
   (latest per icao) and filters out coordinate-less rows; the frontend renders
   clustered plane markers plus the sidebar.
3. **Select** (on click): the map flies to the aircraft, `TrailLayer` fetches
   `/api/trails`, and `SelectionDetail` calls `/api/flight-info` to enrich with
   adsbdb + the local aircraft registry.

## Quick start

```bash
# one command: DB init + backend + frontend, then services
./run.sh
```

| Service    | URL                       |
| ---------- | ------------------------- |
| Dashboard  | http://localhost:5173     |
| API        | http://localhost:8000     |
| Swagger    | http://localhost:8000/docs |

Press `Ctrl+C` to stop all services.

**Run the dashboard against mock data (no backend):**

```bash
cd dashboard
VITE_MOCK=true npm run dev
```

## Configuration reference

Copy `.env.example → `.env` and adjust. See
[Configuration](#configuration) for behavior.

**Frontend (Vite env):** `VITE_API_URL` (default `http://localhost:8000`) and
`VITE_MOCK=true` to enable synthetic data.

## Building the aircraft registry

The registry powers offline type lookup. Download the latest OpenSky snapshot
from the link in `.env.example`/comments and index it once:

```bash
python scripts/build_aircraft_index.py \
  aircraft-database-complete-2025-08.csv \
  data/aircraft_registry.db
```

You can regenerate it anytime; the FastAPI process will detect the DB on the
next request.

## Commands

```bash
python main.py init-db          # create/upgrade DB
python main.py ingest-once      # one OpenSky fetch + persist, then exit
python main.py run-pipeline     # run the polling scheduler forever
python main.py serve-backend    # start the FastAPI server
```

## Development

```bash
pip install -e ".[dev]"   # dev deps: ruff, mypy, pytest, etc.
ruff check src/ tests/    # lint (also ruff format --check)
mypy src/                 # strict type check
pytest                    # run the test suite
```

The repo splits QA across CI (`.github/workflows/ci.yml`) and locally:

- **Lint** — `ruff check src/ tests/`.
- **Types** — `mypy src/` (strict).
- **Tests** — pytest for the backend; `npm run typecheck` / `npm run build` for
  the frontend.

## Testing

The backend test suite (`tests/`) is 37 tests:

- `test_aircraft_registry.py` — offline registry lookups.
- `test_api.py` — the FastAPI endpoints, route behavior.
- `test_adsbdb_provider.py` — adsbdb parsing (aircraft + airline).
- `test_opensky_provider.py` — states parsing, bbox params, auth, rate limit,
  retries.
- `test_repositories.py` — upsert semantics, window queries, pruning.
- `test_controllers.py` — ingestion tick orchestration.
- `test_smoke.py` — importability, schema creation, safe engine.
- `conftest.py` — fixtures (e.g. `db_session`) shared across the suite.

Run the whole thing with:

```bash
pytest
```

## API reference

> All endpoints return JSON.

### `GET /api/states`

Latest aircraft states. Query: `limit` (default 5000). Cached 2 s.

```json
[{
  "icao24": "a35f28", "callsign": "UAL123", "origin_country": "United States",
  "latitude": 40.64, "longitude": -73.78, "baro_altitude": 35000,
  "velocity": 250.4, "heading": 270.0, "vertical_rate": 0.3,
  "on_ground": false, "category_label": "Large", "last_contact": 1700000000
}]
```

### `GET /api/trails`

Position history per icao. Query: `minutes` (default 15).

Returns `{ "<icao>": [{"lat":…,"lon":…,"ts":…}, …], … }`.

### `GET /api/flight-info`

Enrichment. Query `callsign` (required, `[A-Z0-9]{2,10}`), optional `icao24`.

Returns aircraft + airline details:
```json
{
  "aircraft": { "icao": "398565", "type": "B738", "icao_type": "B738",
    "manufacturer": "Boeing", "registration": "N1", "owner": "..." },
  "airline": { "name": "United", "icao": "UAL", "iata": "UA" }
}
```

> ⌘ Origin/destination are intentionally **not** returned — route resolution
> was removed to keep the pipeline focused on identity information.

## Troubleshooting

**Map shows no aircraft.** Ensure the backend and frontend are both running, and
the DB has data (`python main.py ingest-once`).

**"Cannot reach backend" banner.** The frontend defaults to
`http://localhost:8000`; set `VITE_API_URL` if your API is elsewhere, or run mock
mode.

**Rate-limited.** Anonymous OpenSky ~10 req/min. Add `credentials.json` for 4000
req/h (see [Configuration](#configuration)).

**Slow map on very dense areas.** Clustering + heading quantization are already
on; lower `GET /api/states?limit` if needed.

## License

MIT
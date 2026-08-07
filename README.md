# FlightTracker

[![CI](https://github.com/PriyanjanMitra/FlightTracker/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/PriyanjanMitra/FlightTracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A live flight-tracking dashboard that shows aircraft on a map in real time,
with a dark, dual-theme interface (Radar and Dark Souls "Bonfire"). Select an
aircraft to view its altitude, speed, heading, model, airline, and trail.

## Quick start

```bash
./run.sh
```

This single command installs dependencies, sets up the database, and starts
all services:

| What      | URL                       |
| --------- | ------------------------- |
| Dashboard | http://localhost:5173     |
| API       | http://localhost:8000     |
| Docs      | http://localhost:8000/docs |

Press `Ctrl+C` to stop everything.

> For most users, `./run.sh` is all that is required. The sections below are
> for those who want to go further.

## Features

- **Live map** — aircraft color-coded by altitude.
- **Aircraft list** — sortable, searchable sidebar.
- **Flight details** — click an aircraft to view its trail, altitude, speed,
  heading, model, and airline.
- **Day/night overlay** — updates over time.
- **Themes** — toggle between *Radar* (blue) and *Bonfire* (Dark Souls
  gold-on-black).

## Data sources

- **[OpenSky Network](https://opensky-network.org)** — free live aircraft
  positions.
- **[adsbdb](https://www.adsbdb.com)** — aircraft model and airline details.
- **SQLite** — a local database for fast, offline-capable reads.

No API key is required to get started. A free OpenSky account unlocks a much
higher request limit (see below).

## Configuration (optional)

Defaults are sensible, so configuration is only needed to customize behavior:

```bash
cp .env.example .env   # optional
```

- **OpenSky area** — set `OPENSKY_BBOX` to restrict fetching to a bounding box.
- **OpenSky access** — anonymous access is limited to ~10 requests/min. To
  raise it to 4000/hour, create a free OpenSky account and add a
  `credentials.json` to the project root:
  ```json
  { "clientId": "...", "clientSecret": "..." }
  ```
  Obtain these values from the OpenSky API client console. The app reads only
  this file. It is git-ignored and must not be committed.

## Useful commands

Use these to run components individually instead of `run.sh`:

```bash
python main.py init-db          # set up the database (run.sh does this for you)
python main.py ingest-once      # fetch aircraft data once
python main.py run-pipeline     # keep pulling data on a schedule
python main.py serve-backend    # start the API server only
```

## Development

```bash
pip install -e ".[dev]"   # dev tools: ruff, mypy, pytest
ruff check src/ tests/    # lint
mypy src/                 # type check
pytest                    # run tests
```

Tests live in `tests/` and are also run automatically by GitHub Actions (CI).

## Troubleshooting

- **No aircraft on the map** — ensure the backend and frontend are running, and
  that data is available: `python main.py ingest-once`.
- **"Cannot reach backend"** — the frontend expects the API at
  `http://localhost:8000`. Ensure `serve-backend` (or `run.sh`) is running.
- **Slow or rate-limited data** — set up OpenSky authentication as described
  above.

## License

MIT
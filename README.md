# FlightTracker

[![CI](https://github.com/PriyanjanMitra/FlightTracker/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/PriyanjanMitra/FlightTracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A live flight-tracking dashboard that shows aircraft on a map in real time,
with a fun, dark, dual-theme (Radar / Dark Souls "Bonfire") look. Pick an
aircraft to see its altitude, speed, heading, model, airline, and trail.

## Quick start

```bash
./run.sh
```

That's it. One command installs dependencies, sets up the database, and starts
everything:

| What      | URL                       |
| --------- | ------------------------- |
| Dashboard | http://localhost:5173     |
| API       | http://localhost:8000     |
| Docs      | http://localhost:8000/docs |

Press `Ctrl+C` to stop everything.

> Most people only need `./run.sh`. The sections below are for going deeper.
> The backend is Windows/Linux-bash friendly via `run.sh`; the frontend runs
> with `cd dashboard && npm i && npm run dev` if you'd rather split them out.

## What you'll see

- A **live map** of aircraft, color-coded by altitude.
- A **sidebar list** you can sort and search.
- **Click any aircraft** — the map flies to it, a trail appears, and a panel
  shows its altitude, speed, heading, aircraft model, and airline.
- A **day/night overlay** that updates over time.
- A **theme toggle** switching the whole UI between *Radar* (blue) and
  *Bonfire* (Dark Souls gold-on-black).

## Where the data comes from

- **[OpenSky Network](https://opensky-network.org)** — free, live aircraft
  positions (the core feed).
- **[adsbdb](https://www.adsbdb.com)** — aircraft model and airline details for
  the panel.
- A small **local database** (SQLite) so the dashboard stays fast and works
  offline for the data it has already pulled.

You don't need any API key to get started. Registering for a free OpenSky
account unlocks a much higher request limit (see below).

## Configuration (optional)

Everything has sensible defaults, so you can skip this unless you want to tune
things. The main knobs:

```bash
cp .env.example .env   # optional — only if you want to customize
```

- **OpenSky area** — `OPENSKY_BBOX` narrows the fetch to a bounding box.
- **OpenSky speed** — create a free account and add `credentials.json` in the
  project root to go from ~10 requests/min to 4000/hour.
  ```json
  { "username": "you@mail.com", "password": "your-password" }
  ```
  (This file is git-ignored — never commit it.)

## Useful commands

Use these instead of `run.sh` when you want to do one thing at a time:

```bash
python main.py init-db          # set up the database (run.sh does this for you)
python main.py ingest-once      # pull aircraft data once, then print how many
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

- **No aircraft on the map** — make sure both the backend and frontend are
  running, and that the API has data: `python main.py ingest-once`.
- **"Cannot reach backend"** — the frontend expects `http://localhost:8000`.
  Make sure `serve-backend` (or `run.sh`) is running.
- **Data feeding slowly / rate-limited** — set up OpenSky authentication (above).

## License

MIT
# FlightTracker

Live flight tracking dashboard — an ingestion pipeline pulls aircraft state vectors from the OpenSky Network, stores them in SQLite, and serves them to a React + Leaflet map UI.

## Features

- **Live map** — dark-themed Leaflet map with aircraft markers colored by altitude
- **Aircraft list** — sortable/filterable sidebar with climb/descend status badges
- **Flight detail** — click any aircraft to isolate it, view its trail, and see telemetry (altitude, speed, heading, vertical speed) plus origin/destination from flight-info lookup
- **Mock mode** — run the UI standalone with synthetic data, no backend required

## Architecture

```
┌─────────────┐   poll OpenSky    ┌────────────┐   upsert   ┌────────────┐
│  Pipeline   │ ────────────────▶ │  Provider  │ ─────────▶ │  SQLite    │
└─────────────┘                   └────────────┘            └─────┬──────┘
                                                                  │
                          ┌──────────┐   /api/*   ┌───────────────┴───┐
                          │ React UI │ ◀────────  │ FastAPI backend  │
                          └──────────┘            └───────────────────┘
```

## Quick start

```bash
./run.sh
```

This installs dependencies, initializes the database, loads reference data (airports, airlines, routes) on first run, and launches:

- **Dashboard** — http://localhost:5173
- **API** — http://localhost:8000
- **Docs** — http://localhost:8000/docs

Press `Ctrl+C` to stop all services.

## Running just the UI (mock data)

No backend or OpenSky access needed:

```bash
./ui-mock.sh
```

Renders the dashboard at http://localhost:5173 with 60–90 synthetic aircraft over the continental US.

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|---|---|---|
| `OPENSKY_BBOX` | *(empty)* | `lat_min,lat_max,lng_min,lng_max`; empty = worldwide |
| `OPENSKY_POLL_SECONDS` | `1` | Ingestion poll interval |
| `OPENSKY_USERNAME` / `OPENSKY_PASSWORD` | *(empty)* | Authenticated OpenSky access (4000 req/h) |
| `DATABASE_URL` | `sqlite:///data/flight_tracker.db` | SQLAlchemy connection string |
| `LOG_LEVEL` | `INFO` | Logging level |

### Authenticated OpenSky access

Anonymous access is limited to ~10 requests/min. To raise the limit to 4000 req/h, register at [opensky-network.org](https://opensky-network.org) and add a `credentials.json` in the project root:

```json
{
  "username": "your@email.com",
  "password": "your-password"
}
```

Both `username`/`password` and `clientId`/`clientSecret` key pairs are recognized. **This file is git-ignored — never commit it.**

## Commands

```bash
python main.py init-db          # create database schema
python main.py load-ref-data    # load airports/airlines/routes
python main.py run-pipeline     # start the OpenSky ingestion loop
python main.py serve-backend    # start the FastAPI server
```

## Development

```bash
pip install -e ".[dev]"   # dev dependencies (ruff, mypy, pytest)
ruff check src/ tests/    # lint
mypy src/                 # type check
pytest                    # run tests (53 passing)
```

## API

| Endpoint | Description |
|---|---|
| `GET /api/states?limit=5000` | Latest aircraft states |
| `GET /api/trails?minutes=15` | Recent trail points per aircraft |
| `GET /api/flight-info?callsign=…` | Enriched route/airport info for a flight |

## License

MIT

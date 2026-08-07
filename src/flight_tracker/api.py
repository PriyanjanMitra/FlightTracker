"""FastAPI backend for the FlightTracker React frontend."""

import time
from collections.abc import Callable, Generator
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker

from flight_tracker.config import settings
from flight_tracker.models.dtos import (
    CATEGORY_LABELS,
    FlightInfoResponse,
    FlightStateResponse,
)
from flight_tracker.models.orm import create_engine_safe
from flight_tracker.providers.adsbdb_provider import AdsbdbProvider
from flight_tracker.providers.aircraft_registry import AircraftRegistry

app = FastAPI(title="FlightTracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine_safe(settings.database_url)
_SessionLocal = sessionmaker(bind=engine)

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 2.0
_ADSBCACHE_TTL = 120.0

_adsbdb = AdsbdbProvider()
_registry = AircraftRegistry(settings.aircraft_registry_db)


def _cached(key: str, ttl: float, factory: Callable[[], Any]) -> Any:
    now = time.monotonic()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    result = factory()
    _cache[key] = (now, result)
    return result


def get_db() -> Generator[Session, None, None]:
    with _SessionLocal() as session:
        yield session


@app.get("/api/states", response_model=list[FlightStateResponse])
def get_states(
    limit: int = 5000,
    db: Session = Depends(get_db),
) -> list[FlightStateResponse]:
    return _cached(f"states:{limit}", _CACHE_TTL, lambda: _query_states(limit, db))  # type: ignore[no-any-return]


def _query_states(limit: int, db: Session) -> list[FlightStateResponse]:
    from flight_tracker.repository.flight_state_repo import FlightStateRepo

    repo = FlightStateRepo(db)
    rows = repo.latest_states(limit=limit)
    return [
        FlightStateResponse(
            icao24=str(r.icao24),
            callsign=str(r.callsign or ""),
            origin_country=str(r.origin_country or ""),
            latitude=float(r.latitude),
            longitude=float(r.longitude),
            baro_altitude=(
                round(float(r.baro_altitude) * 3.28084)
                if r.baro_altitude is not None
                else None
            ),
            velocity=float(r.velocity) if r.velocity is not None else None,
            heading=float(r.heading) if r.heading is not None else None,
            vertical_rate=float(r.vertical_rate) if r.vertical_rate is not None else None,
            on_ground=bool(r.on_ground) if r.on_ground is not None else False,
            last_contact=int(r.last_contact),
            category_label=CATEGORY_LABELS.get(
                int(r.category) if r.category is not None else 0, "Unknown"
            ),
        )
        for r in rows
        if r.latitude is not None and r.longitude is not None
    ]


@app.get("/api/trails")
def get_trails(
    minutes: int = 15,
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, Any]]]:
    from flight_tracker.repository.flight_state_repo import FlightStateRepo

    cutoff = int((datetime.now(UTC) - timedelta(minutes=minutes)).timestamp())
    now_ts = int(datetime.now(UTC).timestamp())
    repo = FlightStateRepo(db)
    rows = repo.states_in_window(cutoff, now_ts)
    trails: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.latitude is None or r.longitude is None:
            continue
        key = str(r.icao24)
        trails.setdefault(key, []).append(
            {"lat": r.latitude, "lon": r.longitude, "ts": r.last_contact}
        )
    return trails


@app.get("/api/flight-info", response_model=FlightInfoResponse)
def get_flight_info(
    callsign: str = Query(..., min_length=2, max_length=10, pattern=r"^[A-Z0-9]{2,10}$"),
    icao24: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    heading: float | None = None,
    vertical_rate: float | None = None,
) -> FlightInfoResponse:
    """Build flight-info from ADS‑B DB + OpenSky aircraft registry (no routes)."""
    adsb_info = None
    if icao24:
        key = f"flight-info:{icao24}:{callsign.upper()}"
        adsb_info = _cached(
            key,
            _ADSBCACHE_TTL,
            lambda: _adsbdb.fetch_flight_info(icao24, callsign),
        )

    aircraft = adsb_info.aircraft if adsb_info else None
    airline = adsb_info.airline if adsb_info else None

    # Prefer the local OpenSky aircraft registry for type details (offline, free).
    if (aircraft is None or aircraft.icao_type is None) and icao24:
        registered = _registry.lookup(icao24)
        if registered:
            aircraft = registered
            if adsb_info is not None and adsb_info.aircraft is not None:
                aircraft.owner = aircraft.owner or adsb_info.aircraft.owner

    return FlightInfoResponse(
        aircraft=aircraft,
        airline=airline,
    )

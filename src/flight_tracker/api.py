"""FastAPI backend for the FlightTracker React frontend."""

import math
import re
import time
from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker

from flight_tracker.config import settings
from flight_tracker.models.dtos import (
    CATEGORY_LABELS,
    AirportInfo,
    FlightInfoResponse,
    FlightStateResponse,
)
from flight_tracker.models.orm import Airline, Airport, Route, create_engine_safe

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
            baro_altitude=float(r.baro_altitude) if r.baro_altitude is not None else None,
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


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(math.radians(lat2))
    y = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
         - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.cos(dlon))
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@app.get("/api/flight-info", response_model=FlightInfoResponse)
def get_flight_info(
    callsign: str = Query(..., min_length=2, max_length=10, pattern=r"^[A-Z0-9]{2,10}$"),
    latitude: float | None = None,
    longitude: float | None = None,
    heading: float | None = None,
    vertical_rate: float | None = None,
    db: Session = Depends(get_db),
) -> FlightInfoResponse:
    """Match a callsign to origin/destination using proximity, phase, and bearing."""
    m = re.match(r"([A-Z]{2,3})(\d*)", callsign.strip().upper())
    if not m:
        return FlightInfoResponse()
    airline_code = m.group(1)

    codes = _resolve_airline_codes(db, airline_code)

    routes = (
        db.query(Route)
        .filter(Route.airline.in_(list(codes)))
        .filter(Route.source_airport.isnot(None))
        .filter(Route.destination_airport.isnot(None))
        .all()
    )
    if not routes:
        return FlightInfoResponse()

    airport_iata_codes: set[str] = set()
    for r in routes:
        if r.source_airport:
            airport_iata_codes.add(str(r.source_airport))
        if r.destination_airport:
            airport_iata_codes.add(str(r.destination_airport))

    airports = (
        db.query(Airport)
        .filter(Airport.iata.in_(list(airport_iata_codes)))
        .all()
    )
    ap_map: dict[str, AirportInfo] = {}
    for a in airports:
        iata = str(a.iata) if a.iata else ""
        if not iata:
            continue
        ap_map[iata] = AirportInfo(
            iata=iata,
            name=str(a.name or iata),
            latitude=float(a.latitude),
            longitude=float(a.longitude),
        )

    @dataclass
    class _RouteCandidate:
        origin: AirportInfo
        destination: AirportInfo
        route_bearing: float
        dist_origin_km: float
        dist_dest_km: float

    candidates: list[_RouteCandidate] = []
    for r in routes:
        src = ap_map.get(str(r.source_airport))
        dst = ap_map.get(str(r.destination_airport))
        if not src or not dst:
            continue
        candidates.append(_RouteCandidate(
            origin=src,
            destination=dst,
            route_bearing=_bearing(
                src.latitude, src.longitude,
                dst.latitude, dst.longitude,
            ),
            dist_origin_km=_haversine_km(
                latitude or 0, longitude or 0,
                src.latitude, src.longitude,
            ),
            dist_dest_km=_haversine_km(
                latitude or 0, longitude or 0,
                dst.latitude, dst.longitude,
            ),
        ))

    if not candidates:
        return FlightInfoResponse()

    if latitude is not None and longitude is not None:
        is_climbing = vertical_rate is not None and vertical_rate > 2
        is_descending = vertical_rate is not None and vertical_rate < -2

        def score(c: _RouteCandidate) -> float:
            d_org = float(c.dist_origin_km)
            d_dst = float(c.dist_dest_km)
            bear_diff = abs(float(c.route_bearing) - (heading or 0)) % 360
            if bear_diff > 180:
                bear_diff = 360 - bear_diff

            if is_climbing:
                proximity = d_org
            elif is_descending:
                proximity = d_dst
            else:
                proximity = min(d_org, d_dst)

            return proximity + bear_diff * 5

        candidates.sort(key=score)

    best = candidates[0]
    return FlightInfoResponse(origin=best.origin, destination=best.destination)


def _resolve_airline_codes(db: Session, code: str) -> set[str]:
    """Resolve an airline ICAO/IATA code to a set of known codes from the database."""
    codes = {code}

    if len(code) == 3:
        row = db.query(Airline).filter(Airline.icao == code).first()
        if row and row.iata:
            codes.add(str(row.iata))
    elif len(code) == 2:
        row = db.query(Airline).filter(Airline.iata == code).first()
        if row and row.icao:
            codes.add(str(row.icao))

    return codes

"""Tests for the FastAPI backend endpoints."""

import os
import tempfile
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flight_tracker.api import _cache as api_cache
from flight_tracker.api import app, get_db
from flight_tracker.models.orm import Airport, Base, FlightState, Route

client = TestClient(app)

_db_path: str | None = None


def _seed(
    *,
    airports: list | None = None,
    routes: list | None = None,
    states: list | None = None,
):
    """Create a fresh file-based engine, seed data, and override the get_db dependency."""
    global _db_path
    _db_path = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{_db_path}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def get_test_db():
        eng = create_engine(f"sqlite:///{_db_path}")
        with sessionmaker(bind=eng)() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db

    with session_factory() as session:
        if airports:
            for a in airports:
                if isinstance(a, dict):
                    session.add(Airport(**a))
                else:
                    session.add(a)
            session.commit()
        if routes:
            for r in routes:
                if isinstance(r, dict):
                    session.add(Route(**r))
                else:
                    session.add(r)
            session.commit()
        if states:
            for s in states:
                if isinstance(s, dict):
                    session.add(FlightState(**s))
                else:
                    session.add(s)
            session.commit()


def _clean_db() -> None:
    global _db_path
    if _db_path is not None:
        if os.path.exists(_db_path):
            os.unlink(_db_path)
        _db_path = None
    app.dependency_overrides.pop(get_db, None)
    api_cache.clear()


# --- /api/states -------------------------------------------------------------


def test_get_states_returns_states():
    _clean_db()
    now = datetime.now(UTC)
    _seed(states=[
        dict(icao24="a", callsign="UAL1", origin_country="US",
             latitude=40.0, longitude=-70.0, baro_altitude=10000.0,
             velocity=250.0, heading=180.0, vertical_rate=0.0,
             on_ground=False, last_contact=1000, category=4, fetched_at=now),
        dict(icao24="b", callsign="DAL2", origin_country="US",
             latitude=30.0, longitude=-80.0, baro_altitude=20000.0,
             velocity=300.0, heading=90.0, vertical_rate=1.0,
             on_ground=False, last_contact=1001, category=5, fetched_at=now),
    ])
    resp = client.get("/api/states?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    icaos = {s["icao24"] for s in data}
    assert icaos == {"a", "b"}
    assert data[0]["category_label"] == "Heavy"


def test_get_states_filters_none_coords():
    _clean_db()
    now = datetime.now(UTC)
    _seed(states=[
        dict(icao24="a", callsign="UAL1", origin_country="US",
             latitude=40.0, longitude=-70.0, baro_altitude=10000.0,
             velocity=250.0, heading=180.0, vertical_rate=0.0,
             on_ground=False, last_contact=1000, category=None, fetched_at=now),
        dict(icao24="b", callsign="BAD", origin_country="XX",
             latitude=None, longitude=None, baro_altitude=None,
             velocity=None, heading=None, vertical_rate=None,
             on_ground=None, last_contact=1000, category=None, fetched_at=now),
    ])
    resp = client.get("/api/states?limit=10")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- /api/trails -------------------------------------------------------------


def test_get_trails_returns_points():
    _clean_db()
    now_ts = int(datetime.now(UTC).timestamp())
    _seed(states=[
        dict(icao24="a", callsign="UAL1", origin_country="US",
             latitude=40.0, longitude=-70.0, baro_altitude=10000.0,
             velocity=250.0, heading=180.0, vertical_rate=0.0,
             on_ground=False, last_contact=now_ts - 10, category=None,
             fetched_at=datetime.now(UTC)),
        dict(icao24="a", callsign="UAL1", origin_country="US",
             latitude=41.0, longitude=-71.0, baro_altitude=9000.0,
             velocity=240.0, heading=180.0, vertical_rate=0.0,
             on_ground=False, last_contact=now_ts - 5, category=None, fetched_at=datetime.now(UTC)),
    ])
    resp = client.get("/api/trails?minutes=60")
    assert resp.status_code == 200
    data = resp.json()
    assert "a" in data
    assert len(data["a"]) == 2


def test_get_trails_empty_window():
    _clean_db()
    now = datetime.now(UTC)
    _seed(states=[
        dict(icao24="a", callsign="UAL1", origin_country="US",
             latitude=40.0, longitude=-70.0, baro_altitude=10000.0,
             velocity=250.0, heading=180.0, vertical_rate=0.0,
             on_ground=False, last_contact=1000, category=None, fetched_at=now),
    ])
    resp = client.get("/api/trails?minutes=1")
    assert resp.status_code == 200
    assert resp.json() == {}


# --- /api/flight-info --------------------------------------------------------


def test_flight_info_matches_route():
    _clean_db()
    _seed(
        airports=[
            Airport(id=1, iata="LHR", name="Heathrow", latitude=51.47,
                    longitude=-0.46, altitude=83),
            Airport(id=2, iata="JFK", name="JFK", latitude=40.64,
                    longitude=-73.78, altitude=13),
        ],
        routes=[
            Route(airline="BA", source_airport="LHR", destination_airport="JFK",
                  stops=0),
        ],
    )
    resp = client.get(
        "/api/flight-info?callsign=BA123&latitude=51.47&longitude=-0.46"
        "&heading=270&vertical_rate=15"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["origin"]["iata"] == "LHR"
    assert data["destination"]["iata"] == "JFK"


def test_flight_info_no_match():
    _clean_db()
    _seed()
    resp = client.get("/api/flight-info?callsign=ZZZ999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["origin"] is None
    assert data["destination"] is None


def test_flight_info_uses_climbing_heuristic():
    _clean_db()
    """When climbing near origin A, should prefer A→B over C→B."""
    _seed(
        airports=[
            Airport(id=1, iata="WAW", name="Warsaw", latitude=52.17,
                    longitude=20.97, altitude=100),
            Airport(id=2, iata="ARN", name="Stockholm", latitude=59.65,
                    longitude=17.92, altitude=50),
            Airport(id=3, iata="RZE", name="Rzeszow", latitude=50.11,
                    longitude=22.02, altitude=200),
        ],
        routes=[
            Route(airline="LO", source_airport="WAW", destination_airport="ARN",
                  stops=0),
            Route(airline="LO", source_airport="RZE", destination_airport="ARN",
                  stops=0),
        ],
    )
    # Climbing (vertical_rate=15) near WAW → should pick WAW→ARN
    resp = client.get(
        "/api/flight-info?callsign=LO123&latitude=52.2&longitude=21.0"
        "&heading=350&vertical_rate=15"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["origin"]["iata"] == "WAW"
    assert data["destination"]["iata"] == "ARN"

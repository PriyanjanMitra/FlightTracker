"""Tests for the FastAPI backend endpoints."""

import os
import tempfile
from datetime import UTC, datetime
from unittest.mock import patch

import responses
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flight_tracker.api import _cache as api_cache
from flight_tracker.api import app, get_db
from flight_tracker.models.orm import Base, FlightState
from flight_tracker.providers.adsbdb_provider import ADSBDB_API

client = TestClient(app)

_db_path: str | None = None


def _seed(
    *,
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
    ts = int(now.timestamp())
    _seed(states=[
        dict(icao24="a", callsign="UAL1", origin_country="US",
             latitude=40.0, longitude=-70.0, baro_altitude=10000.0,
             velocity=250.0, heading=180.0, vertical_rate=0.0,
             on_ground=False, last_contact=ts, category=4, fetched_at=now),
        dict(icao24="b", callsign="DAL2", origin_country="US",
             latitude=30.0, longitude=-80.0, baro_altitude=20000.0,
             velocity=300.0, heading=90.0, vertical_rate=1.0,
             on_ground=False, last_contact=ts + 1, category=5, fetched_at=now),
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
    ts = int(now.timestamp())
    _seed(states=[
        dict(icao24="a", callsign="UAL1", origin_country="US",
             latitude=40.0, longitude=-70.0, baro_altitude=10000.0,
             velocity=250.0, heading=180.0, vertical_rate=0.0,
             on_ground=False, last_contact=ts, category=None, fetched_at=now),
        dict(icao24="b", callsign="BAD", origin_country="XX",
             latitude=None, longitude=None, baro_altitude=None,
             velocity=None, heading=None, vertical_rate=None,
             on_ground=None, last_contact=ts, category=None, fetched_at=now),
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


def test_flight_info_no_match():
    _clean_db()
    _seed()
    resp = client.get("/api/flight-info?callsign=ZZZ999")
    assert resp.status_code == 200
    data = resp.json()
    assert "origin" not in data
    assert "destination" not in data


@responses.activate
def test_flight_info_uses_adsbdb():
    _clean_db()
    responses.add(
        responses.Response(
            method="GET",
            url=f"{ADSBDB_API}/aircraft/398565",
            json={
                "response": {
                    "aircraft": {
                        "type": "B738",
                        "icao_type": "B738",
                        "manufacturer": "Boeing",
                        "registration": "N1",
                    },
                    "flightroute": {
                        "airline": {"name": "United", "icao": "UAL", "iata": "UA"},
                        "origin": {"iata_code": "JFK", "name": "JFK", "latitude": 40.6,
                                  "longitude": -73.8},
                        "destination": {"iata_code": "SFO", "name": "SFO", "latitude": 37.6,
                                       "longitude": -122.4},
                    },
                }
            },
            status=200,
        )
    )
    with patch("flight_tracker.api._registry.lookup", return_value=None):
        resp = client.get("/api/flight-info?callsign=UAL123&icao24=398565")
    assert resp.status_code == 200
    data = resp.json()
    assert data["aircraft"]["type"] == "B738"
    assert data["airline"]["name"] == "United"
    assert "origin" not in data
    assert "destination" not in data


def test_flight_info_no_match_no_registry():
    _clean_db()
    _seed()
    with patch("flight_tracker.api._registry.lookup", return_value=None):
        resp = client.get("/api/flight-info?callsign=ZZZ999&icao24=zzz999")
    assert resp.status_code == 200
    data = resp.json()
    assert "origin" not in data
    assert "destination" not in data


def test_flight_info_registry_provides_type_when_adsbdb_missing():
    _clean_db()
    _seed()
    from flight_tracker.models.dtos import AircraftInfo

    reg = AircraftInfo(icao24="4bb15a", icao_type="B77L", type="Boeing 777-200LR",
                       manufacturer="Boeing", registration="TC-JJF", owner="Turkish Airlines")
    with patch("flight_tracker.api._adsbdb.fetch_flight_info", return_value=None), \
         patch("flight_tracker.api._registry.lookup", return_value=reg):
        resp = client.get("/api/flight-info?callsign=THY6237&icao24=4bb15a")
    assert resp.status_code == 200
    data = resp.json()
    assert data["aircraft"]["icao_type"] == "B77L"
    assert data["aircraft"]["type"] == "Boeing 777-200LR"


def test_flight_info_route_never_returned():
    """Origin/destination are never surfaced; routes were removed."""
    _clean_db()
    _seed()

    with patch("flight_tracker.api._adsbdb.fetch_flight_info", return_value=None), \
         patch("flight_tracker.api._registry.lookup", return_value=None):
        resp = client.get("/api/flight-info?callsign=THY6237&icao24=4bb15a")
    assert resp.status_code == 200
    data = resp.json()
    assert "origin" not in data
    assert "destination" not in data

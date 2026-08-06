"""Tests for the AircraftRegistry provider."""

import sqlite3
import tempfile

from flight_tracker.providers.aircraft_registry import AircraftRegistry

SCHEMA = """CREATE TABLE aircraft (
  icao24 TEXT PRIMARY KEY,
  typecode TEXT, manufacturer TEXT, model TEXT, registration TEXT,
  operator TEXT, operator_icao TEXT, operator_iata TEXT
)"""


def _make_db(rows: list[tuple]) -> str:
    path = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    conn.executemany(
        "INSERT INTO aircraft VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return path


def test_lookup_returns_registration_info():
    db = _make_db([("4bb15a", "B77L", "Boeing", "777-200LR", "TC-JJF", "Turkish Airlines",
                    "THY", "TK")])
    reg = AircraftRegistry(db)
    aircraft = reg.lookup("4bb15a")
    assert aircraft is not None
    assert aircraft.icao_type == "B77L"
    assert aircraft.type == "777-200LR"
    assert aircraft.manufacturer == "Boeing"
    assert aircraft.registration == "TC-JJF"
    assert aircraft.owner == "Turkish Airlines"


def test_lookup_is_case_insensitive():
    db = _make_db([("4bb15a", "B77L", "Boeing", "777-200LR", "TC-JJF", "THY", "THY", "TK")])
    reg = AircraftRegistry(db)
    assert reg.lookup("4BB15A") is not None


def test_lookup_returns_none_when_missing():
    db = _make_db([("4bb15a", "B77L", "Boeing", "777-200LR", "TC-JJF", "THY", "THY", "TK")])
    reg = AircraftRegistry(db)
    assert reg.lookup("000000") is None


def test_lookup_returns_none_when_db_missing():
    reg = AircraftRegistry("/nonexistent/path/aircraft.db")
    assert reg.lookup("4bb15a") is None
    assert reg.available is False

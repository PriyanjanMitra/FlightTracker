"""Tests for the OpenFlights CSV provider."""

import pathlib

from flight_tracker.providers.openflights_provider import (
    _airline_cols,
    _airport_cols,
    _route_cols,
)


def _make_path(tmp_path: pathlib.Path, name: str, lines: list[str]) -> pathlib.Path:
    p = tmp_path / name
    p.write_text("\n".join(lines))
    return p


# --- Airport parsing ---------------------------------------------------------


def test_airport_parses_typical_row():
    raw = [
        "507", "London Heathrow Airport", "London", "United Kingdom", "LHR",
        "EGLL", "51.4706", "-0.461941", "83", "0", "E", "large_airport",
        "OurAirports",
    ]
    row = _airport_cols(raw)
    assert row["id"] == 507
    assert row["iata"] == "LHR"
    assert row["icao"] == "EGLL"
    assert row["latitude"] == 51.4706


def test_airport_handles_null_iata():
    raw = ["1", "Some Airport", "City", "Country", "\\N", "\\N",
           "10.0", "20.0", "0", "0", "", "", ""]
    row = _airport_cols(raw)
    assert row["iata"] is None
    assert row["icao"] is None


def test_airport_handles_empty_string():
    raw = ["2", "Test", "City", "Country", "", "", "15.0", "25.0", "100", "", "", "", ""]
    row = _airport_cols(raw)
    assert row["iata"] is None
    assert row["altitude"] == 100


# --- Route parsing -----------------------------------------------------------


def test_route_parses_typical_row():
    raw = ["BA", "1355", "LHR", "507", "JFK", "3854", "", "0", "744 777"]
    row = _route_cols(raw)
    assert row["airline"] == "BA"
    assert row["source_airport"] == "LHR"
    assert row["destination_airport"] == "JFK"
    assert row["stops"] == 0


def test_route_handles_null_airline():
    raw = ["\\N", "", "AAA", "", "BBB", "", "", "1", ""]
    row = _route_cols(raw)
    assert row["airline"] is None
    assert row["stops"] == 1


# --- Airline parsing ---------------------------------------------------------


def test_airline_parses_typical_row():
    raw = ["24", "American Airlines", "AA", "AAL", "AMERICAN", "United States", "Y"]
    row = _airline_cols(raw)
    assert row["id"] == 24
    assert row["iata"] == "AA"
    assert row["icao"] == "AAL"
    assert row["active"] == "Y"


def test_airline_handles_null_iata():
    raw = ["999", "Unknown", "\\N", "\\N", "", "", ""]
    row = _airline_cols(raw)
    assert row["iata"] is None
    assert row["icao"] is None

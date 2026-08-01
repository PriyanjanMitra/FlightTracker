"""Provider that downloads and parses OpenFlights reference CSV files."""

import csv
import logging
import pathlib
from typing import Any

import requests

OPENAIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
OPENROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
OPENAIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"

log = logging.getLogger(__name__)

AirportRow = dict[str, Any]
RouteRow = dict[str, Any]
AirlineRow = dict[str, Any]


def _download(url: str, target: pathlib.Path) -> None:
    log.info("Downloading %s → %s", url, target)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(resp.text, encoding="utf-8")


def _read_csv(path: pathlib.Path) -> list[list[str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.reader(f))


def _null(val: str) -> str | None:
    val = val.strip()
    return None if val in ("", "\\N") else val


# --- Airports -----------------------------------------------------------------


def _airport_cols(raw: list[str]) -> AirportRow:
    return {
        "id": int(raw[0]) if raw[0] else None,
        "name": _null(raw[1]) if len(raw) > 1 else None,
        "city": _null(raw[2]) if len(raw) > 2 else None,
        "country": _null(raw[3]) if len(raw) > 3 else None,
        "iata": _null(raw[4]) if len(raw) > 4 else None,
        "icao": _null(raw[5]) if len(raw) > 5 else None,
        "latitude": float(raw[6]) if raw[6] and raw[6] != "\\N" else None,
        "longitude": float(raw[7]) if raw[7] and raw[7] != "\\N" else None,
        "altitude": int(float(raw[8])) if raw[8] and raw[8] != "\\N" else None,
        "timezone": _null(raw[9]) if len(raw) > 9 else None,
        "dst": _null(raw[10]) if len(raw) > 10 else None,
        "type": _null(raw[11]) if len(raw) > 11 else None,
        "source": _null(raw[12]) if len(raw) > 12 else None,
    }


def download_airports(
    cache_dir: pathlib.Path, force: bool = False
) -> list[AirportRow]:
    target = cache_dir / "airports.dat"
    if force or not target.exists():
        _download(OPENAIRPORTS_URL, target)
    rows = _read_csv(target)
    result = []
    for raw in rows:
        try:
            result.append(_airport_cols(raw))
        except (ValueError, IndexError):
            log.warning("Skipping malformed airport row: %s", raw)
    log.info("Parsed %d airports", len(result))
    return result


# --- Routes -------------------------------------------------------------------


def _route_cols(raw: list[str]) -> RouteRow:
    return {
        "airline": _null(raw[0]) if len(raw) > 0 else None,
        "airline_id": int(raw[1]) if raw[1] and raw[1] != "\\N" else None,
        "source_airport": _null(raw[2]) if len(raw) > 2 else None,
        "source_airport_id": int(raw[3]) if raw[3] and raw[3] != "\\N" else None,
        "destination_airport": _null(raw[4]) if len(raw) > 4 else None,
        "destination_airport_id": int(raw[5]) if raw[5] and raw[5] != "\\N" else None,
        "codeshare": _null(raw[6]) if len(raw) > 6 else None,
        "stops": int(raw[7]) if raw[7] and raw[7] != "\\N" else 0,
        "equipment": _null(raw[8]) if len(raw) > 8 else None,
    }


def download_routes(
    cache_dir: pathlib.Path, force: bool = False
) -> list[RouteRow]:
    target = cache_dir / "routes.dat"
    if force or not target.exists():
        _download(OPENROUTES_URL, target)
    rows = _read_csv(target)
    result = []
    for raw in rows:
        try:
            result.append(_route_cols(raw))
        except (ValueError, IndexError):
            log.warning("Skipping malformed route row: %s", raw)
    log.info("Parsed %d routes", len(result))
    return result


# --- Airlines -----------------------------------------------------------------


def _airline_cols(raw: list[str]) -> AirlineRow:
    return {
        "id": int(raw[0]) if raw[0] else None,
        "name": _null(raw[1]) if len(raw) > 1 else None,
        "iata": _null(raw[2]) if len(raw) > 2 else None,
        "icao": _null(raw[3]) if len(raw) > 3 else None,
        "callsign": _null(raw[4]) if len(raw) > 4 else None,
        "country": _null(raw[5]) if len(raw) > 5 else None,
        "active": _null(raw[6]) if len(raw) > 6 else None,
    }


def download_airlines(
    cache_dir: pathlib.Path, force: bool = False
) -> list[AirlineRow]:
    target = cache_dir / "airlines.dat"
    if force or not target.exists():
        _download(OPENAIRLINES_URL, target)
    rows = _read_csv(target)
    result = []
    for raw in rows:
        try:
            result.append(_airline_cols(raw))
        except (ValueError, IndexError):
            log.warning("Skipping malformed airline row: %s", raw)
    log.info("Parsed %d airlines", len(result))
    return result

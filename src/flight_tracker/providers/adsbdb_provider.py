"""Provider that fetches aircraft, airline, and route data from the adsbdb API."""

import logging
from typing import Any

import requests

from flight_tracker.models.dtos import (
    AircraftInfo,
    AirlineInfo,
    AirportInfo,
    FlightInfoResponse,
)

ADSBDB_API = "https://api.adsbdb.com/v0"
REQUEST_TIMEOUT = 10

log = logging.getLogger(__name__)


def _airport(data: dict[str, Any] | None) -> AirportInfo | None:
    if not data:
        return None
    try:
        return AirportInfo(
            iata=str(data.get("iata_code") or ""),
            name=str(data.get("name") or ""),
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


class AdsbdbProvider:
    def fetch_flight_info(
        self, icao24: str, callsign: str | None = None
    ) -> FlightInfoResponse | None:
        params: dict[str, str] = {}
        if callsign:
            params["callsign"] = callsign
        try:
            resp = requests.get(
                f"{ADSBDB_API}/aircraft/{icao24}", params=params, timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            payload = resp.json().get("response")
            if not isinstance(payload, dict) or "aircraft" not in payload:
                return None
            return self._parse(payload, icao24)
        except requests.RequestException as exc:
            log.warning("adsbdb request failed for %s: %s", icao24, exc)
            return None

    @staticmethod
    def _parse(payload: dict[str, Any], icao24: str) -> FlightInfoResponse:
        ac = payload.get("aircraft") or {}
        fr = payload.get("flightroute") or {}
        airline = fr.get("airline") or {}

        aircraft = AircraftInfo(
            icao24=icao24,
            type=ac.get("type"),
            icao_type=ac.get("icao_type"),
            manufacturer=ac.get("manufacturer"),
            registration=ac.get("registration"),
            owner=ac.get("registered_owner"),
        )

        route_info = FlightInfoResponse(
            aircraft=aircraft,
            airline=AirlineInfo(
                name=airline.get("name"),
                icao=airline.get("icao"),
                iata=airline.get("iata"),
            )
            if airline
            else None,
            origin=_airport(fr.get("origin")),
            destination=_airport(fr.get("destination")),
        )
        return route_info

"""Provider that fetches live aircraft state vectors from the OpenSky API."""

import json
import logging
import pathlib
import time
from collections.abc import Sequence
from typing import Any

import requests

from flight_tracker.models.dtos import FlightStateDTO

OPENSKY_API = "https://opensky-network.org/api/states/all"
OPENSKY_ROUTES_API = "https://opensky-network.org/api/routes"
OPENSKY_FLIGHTS_AIRCRAFT_API = "https://opensky-network.org/api/flights/aircraft"
AUTH_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BASE_BACKOFF = 2.0
DEFAULT_RATE_LIMIT_BACKOFF = 120.0
ROUTE_HISTORY_HOURS = 24

log = logging.getLogger(__name__)


def _load_auth() -> tuple[str, str] | None:
    """Load OpenSky client credentials (clientId/clientSecret) for the OAuth2 flow."""
    creds_path = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "credentials.json"
    if creds_path.exists():
        try:
            data = json.loads(creds_path.read_text())
            client_id = data.get("clientId") or data.get("username") or ""
            client_secret = data.get("clientSecret") or data.get("password") or ""
            if client_id and client_secret:
                return (client_id, client_secret)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Failed to read credentials.json: %s", exc)

    from flight_tracker.config import settings

    if settings.opensky_username and settings.opensky_password:
        return (settings.opensky_username, settings.opensky_password)
    return None


def _parse_retry_after(resp: requests.Response) -> float:
    """Extract retry-after seconds from response headers, falling back to default."""
    val = resp.headers.get("x-rate-limit-retry-after-seconds")
    if val:
        try:
            return max(float(val), 10.0)
        except (ValueError, TypeError):
            pass
    val = resp.headers.get("Retry-After")
    if val:
        try:
            return max(float(val), 10.0)
        except (ValueError, TypeError):
            pass
    return DEFAULT_RATE_LIMIT_BACKOFF


class OpenSkyProvider:
    def __init__(self) -> None:
        self._credentials = _load_auth()
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._rate_limit_until: float = 0.0
        self._rate_limit_logged: bool = False

    def _obtain_token(self) -> None:
        """Exchange client credentials for an OAuth2 access token."""
        if not self._credentials:
            return
        client_id, client_secret = self._credentials
        try:
            resp = requests.post(
                AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            expires_in = int(data.get("expires_in", 1800))
            self._token_expires_at = time.monotonic() + expires_in - 60
            log.info("Obtained OpenSky access token (expires in %ds)", expires_in)
        except (requests.RequestException, KeyError, ValueError) as exc:
            log.error("Failed to obtain OpenSky access token: %s", exc)
            self._token = None

    def _request_headers(self) -> dict[str, str] | None:
        """Return Authorization headers using a valid Bearer token, if credentials exist."""
        if not self._credentials:
            return None
        if not self._token or time.monotonic() >= self._token_expires_at:
            self._obtain_token()
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return None

    def fetch_states(self, bbox: str | None = None) -> Sequence[FlightStateDTO]:
        now = time.monotonic()
        if now < self._rate_limit_until:
            if not self._rate_limit_logged:
                self._rate_limit_logged = True
                log.warning(
                    "OpenSky rate-limited; retrying in %.0fs",
                    self._rate_limit_until - now,
                )
            return []
        if self._rate_limit_logged:
            self._rate_limit_logged = False
            log.info("OpenSky rate-limit cooldown over; resuming requests")

        params: dict[str, str | float] = {}
        if bbox:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) == 4:
                params["lamin"], params["lamax"], params["lomin"], params["lomax"] = parts

        last_exc: Exception | None = None
        headers = self._request_headers()
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(
                    OPENSKY_API, params=params, headers=headers, timeout=REQUEST_TIMEOUT
                )
                if resp.status_code == 401:
                    self._token = None
                    headers = self._request_headers()
                    log.warning("OpenSky returned 401; token refreshed, retrying")
                    continue
                if resp.status_code == 429:
                    retry_after = _parse_retry_after(resp)
                    self._rate_limit_until = time.monotonic() + retry_after
                    self._rate_limit_logged = False
                    log.warning(
                        "OpenSky rate-limited (429); retry in %.0fs",
                        retry_after,
                    )
                    return []
                resp.raise_for_status()
                data = resp.json()
                return self._parse_states(data)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    delay = BASE_BACKOFF * (2 ** attempt)
                    log.warning(
                        "OpenSky request failed (attempt %d/%d): %s; retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, exc, delay,
                    )
                    time.sleep(delay)
                else:
                    log.error(
                        "OpenSky request failed after %d attempts: %s",
                        MAX_RETRIES, exc,
                    )
            except requests.RequestException as exc:
                last_exc = exc
                log.error("OpenSky request failed: %s", exc)
                return []

        if last_exc:
            log.error("OpenSky request failed after %d attempts: %s", MAX_RETRIES, last_exc)
        return []

    def fetch_route(self, callsign: str) -> tuple[str, str] | None:
        """Fetch the route (origin, destination) for a flight by callsign.

        The OpenSky routes API is keyed by callsign and returns a flat list of
        ICAO airport codes: {"route": ["EGLL", "OTHH"], ...}.
        Returns a (origin_icao, destination_icao) tuple, or None when unknown/errors.
        """
        params = {"callsign": callsign}
        headers = self._request_headers()
        try:
            resp = requests.get(
                OPENSKY_ROUTES_API, params=params, headers=headers, timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            route = data.get("route") if isinstance(data, dict) else None
            if not route or len(route) < 2:
                return None
            origin, destination = route[0], route[1]
            if not origin or not destination:
                return None
            return str(origin), str(destination)
        except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
            log.warning("OpenSky route request failed for %s: %s", callsign, exc)
            return None

    def fetch_trajectory_route(self, icao24: str) -> tuple[str | None, str | None]:
        """Fetch origin/destination estimated from the aircraft's observed trajectory.

        Requires authenticated OpenSky access. Queries the aircraft's flights over the
        last ROUTE_HISTORY_HOURS and returns (estDepartureAirport, estArrivalAirport)
        as ICAO codes from the most recent flight. Either element may be None when not
        yet resolved (e.g. arrival is unknown mid-ocean).
        """
        headers = self._request_headers()
        if not headers:
            log.info("No OpenSky credentials; skipping trajectory route for %s", icao24)
            return (None, None)
        now = int(time.time())
        params: dict[str, str | int] = {
            "icao24": icao24,
            "begin": now - ROUTE_HISTORY_HOURS * 3600,
            "end": now,
        }
        try:
            resp = requests.get(
                OPENSKY_FLIGHTS_AIRCRAFT_API,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 404:
                return (None, None)
            if resp.status_code == 401:
                self._token = None
                log.warning("OpenSky returned 401 for trajectory route; token refreshed")
                return (None, None)
            resp.raise_for_status()
            flights = resp.json()
            if not isinstance(flights, list) or not flights:
                return (None, None)
            flight = flights[-1]
            origin = flight.get("estDepartureAirport")
            destination = flight.get("estArrivalAirport")
            return (str(origin) if origin else None, str(destination) if destination else None)
        except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
            log.warning("OpenSky trajectory route request failed for %s: %s", icao24, exc)
            return (None, None)

    @staticmethod
    def _parse_states(data: dict[str, Any]) -> list[FlightStateDTO]:
        states = data.get("states", [])
        result: list[FlightStateDTO] = []
        for raw in states:
            if raw is None:
                continue
            try:
                dto = FlightStateDTO(
                    icao24=raw[0],
                    callsign=raw[1].strip() if raw[1] else None,
                    origin_country=raw[2],
                    longitude=raw[5],
                    latitude=raw[6],
                    baro_altitude=raw[7],
                    velocity=raw[9],
                    heading=raw[10],
                    on_ground=bool(raw[8]) if raw[8] is not None else None,
                    last_contact=raw[4],
                    vertical_rate=raw[11] if len(raw) > 11 else None,
                    category=raw[17] if len(raw) > 17 else None,
                )
                result.append(dto)
            except (IndexError, TypeError) as exc:
                log.warning("Skipping malformed state row: %s — %s", raw, exc)
                continue

        log.info("Fetched %d states from OpenSky", len(result))
        return result

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
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BASE_BACKOFF = 2.0
DEFAULT_RATE_LIMIT_BACKOFF = 120.0

log = logging.getLogger(__name__)


def _load_auth() -> tuple[str, str] | None:
    """Load OpenSky credentials from credentials.json or settings env vars."""
    creds_path = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "credentials.json"
    if creds_path.exists():
        try:
            data = json.loads(creds_path.read_text())
            user = data.get("username") or data.get("clientId") or ""
            pwd = data.get("password") or data.get("clientSecret") or ""
            if user and pwd:
                return (user, pwd)
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
    _rate_limit_until: float = 0.0

    def __init__(self) -> None:
        self._auth = _load_auth()

    def fetch_states(self, bbox: str | None = None) -> Sequence[FlightStateDTO]:
        now = time.monotonic()
        if now < self._rate_limit_until:
            remaining = self._rate_limit_until - now
            log.warning(
                "OpenSky rate-limited; %.0fs remaining until retry",
                remaining,
            )
            return []

        params: dict[str, str | float] = {}
        if bbox:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) == 4:
                params["lamin"], params["lamax"], params["lomin"], params["lomax"] = parts

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(
                    OPENSKY_API, params=params, timeout=REQUEST_TIMEOUT, auth=self._auth
                )
                if resp.status_code == 429:
                    retry_after = _parse_retry_after(resp)
                    self._rate_limit_until = time.monotonic() + retry_after
                    log.warning(
                        "OpenSky rate-limited (429); retry after %.0fs",
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

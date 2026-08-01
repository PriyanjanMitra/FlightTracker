"""Service that orchestrates fetching states from OpenSky and persisting them."""

import logging
from datetime import UTC, datetime

from flight_tracker.providers.opensky_provider import OpenSkyProvider
from flight_tracker.repository.flight_state_repo import FlightStateRepo

log = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, provider: OpenSkyProvider, repo: FlightStateRepo):
        self._provider = provider
        self._repo = repo

    def run_once(self, bbox: str | None = None) -> int:
        states = self._provider.fetch_states(bbox=bbox)
        now = datetime.now(UTC)
        rows = []
        for dto in states:
            rows.append({
                "icao24": dto.icao24,
                "callsign": dto.callsign,
                "origin_country": dto.origin_country,
                "longitude": dto.longitude,
                "latitude": dto.latitude,
                "baro_altitude": dto.baro_altitude,
                "velocity": dto.velocity,
                "heading": dto.heading,
                "vertical_rate": dto.vertical_rate,
                "on_ground": dto.on_ground,
                "last_contact": dto.last_contact,
                "category": dto.category,
                "fetched_at": now,
            })
        self._repo.upsert_many(rows)
        log.info("Persisted %d flight states", len(rows))
        return len(rows)

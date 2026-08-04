from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from flight_tracker.models.orm import FlightState


class FlightStateRepo:
    def __init__(self, session: Session):
        self._session = session

    def upsert_many(self, rows: Sequence[dict[str, Any]]) -> int:
        if not rows:
            return 0

        stmt = sqlite_insert(FlightState).values(list(rows))
        stmt = stmt.on_conflict_do_update(
            index_elements=["icao24", "last_contact"],
            set_={
                "callsign": stmt.excluded.callsign,
                "origin_country": stmt.excluded.origin_country,
                "longitude": stmt.excluded.longitude,
                "latitude": stmt.excluded.latitude,
                "baro_altitude": stmt.excluded.baro_altitude,
                "velocity": stmt.excluded.velocity,
                "heading": stmt.excluded.heading,
                "vertical_rate": stmt.excluded.vertical_rate,
                "on_ground": stmt.excluded.on_ground,
                "category": stmt.excluded.category,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        self._session.execute(stmt)
        self._session.commit()
        return len(rows)

    def prune_old_states(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
        deleted = (
            self._session.query(FlightState)
            .filter(FlightState.fetched_at < cutoff)
            .delete()
        )
        self._session.commit()
        return deleted

    def latest_states(
        self, limit: int = 200, recent_minutes: int = 15
    ) -> list[FlightState]:
        cutoff = int(datetime.now(UTC).timestamp()) - recent_minutes * 60
        max_fetched = (
            self._session.query(
                FlightState.icao24,
                func.max(FlightState.fetched_at).label("max_fetched"),
            )
            .group_by(FlightState.icao24)
            .subquery()
        )
        return (
            self._session.query(FlightState)
            .join(
                max_fetched,
                (FlightState.icao24 == max_fetched.c.icao24)
                & (FlightState.fetched_at == max_fetched.c.max_fetched),
            )
            .filter(FlightState.last_contact >= cutoff)
            .order_by(FlightState.last_contact.desc())
            .limit(limit)
            .all()
        )

    def states_in_window(self, start: int, end: int) -> list[FlightState]:
        return (
            self._session.query(FlightState)
            .filter(FlightState.last_contact >= start)
            .filter(FlightState.last_contact <= end)
            .all()
        )

    def count(self) -> int:
        return self._session.query(FlightState).count()

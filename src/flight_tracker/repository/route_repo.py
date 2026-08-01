from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from flight_tracker.models.orm import Route


class RouteRepo:
    def __init__(self, session: Session):
        self._session = session

    def upsert_many(self, rows: Sequence[dict[str, Any]]) -> list[Route]:
        saved: list[Route] = []
        for r in rows:
            obj = Route(**r)
            self._session.add(obj)
            saved.append(obj)
        self._session.commit()
        return saved

    def get_by_source(self, iata: str) -> list[Route]:
        return (
            self._session.query(Route)
            .filter(Route.source_airport == iata.upper().strip())
            .all()
        )

    def get_by_destination(self, iata: str) -> list[Route]:
        return (
            self._session.query(Route)
            .filter(Route.destination_airport == iata.upper().strip())
            .all()
        )

    def list_all(self, limit: int = 200) -> list[Route]:
        return self._session.query(Route).limit(limit).all()

    def count(self) -> int:
        return self._session.query(Route).count()

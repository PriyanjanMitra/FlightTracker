from collections.abc import Sequence
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from flight_tracker.models.orm import Airport


class AirportRepo:
    def __init__(self, session: Session):
        self._session = session

    def upsert_many(self, rows: Sequence[dict[str, Any]]) -> list[Airport]:
        saved: list[Airport] = []
        for r in rows:
            existing = self._session.query(Airport).filter_by(id=r["id"]).first()
            if existing:
                for k, v in r.items():
                    setattr(existing, k, v)
                saved.append(existing)
            else:
                obj = Airport(**r)
                self._session.add(obj)
                saved.append(obj)
        self._session.commit()
        return saved

    def get_by_iata(self, iata: str) -> Airport | None:
        return (
            self._session.query(Airport)
            .filter(func.upper(Airport.iata) == iata.upper().strip())
            .first()
        )

    def get_by_icao(self, icao: str) -> Airport | None:
        return (
            self._session.query(Airport)
            .filter(func.upper(Airport.icao) == icao.upper().strip())
            .first()
        )

    def list_all(self, limit: int = 200) -> list[Airport]:
        return self._session.query(Airport).limit(limit).all()

    def count(self) -> int:
        return self._session.query(Airport).count()

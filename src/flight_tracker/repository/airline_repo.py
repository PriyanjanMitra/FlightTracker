from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from flight_tracker.models.orm import Airline


class AirlineRepo:
    def __init__(self, session: Session):
        self._session = session

    def upsert_many(self, rows: Sequence[dict[str, Any]]) -> list[Airline]:
        saved: list[Airline] = []
        for r in rows:
            existing = self._session.query(Airline).filter_by(id=r["id"]).first()
            if existing:
                for k, v in r.items():
                    setattr(existing, k, v)
                saved.append(existing)
            else:
                obj = Airline(**r)
                self._session.add(obj)
                saved.append(obj)
        self._session.commit()
        return saved

    def get_by_iata(self, iata: str) -> Airline | None:
        return (
            self._session.query(Airline)
            .filter(Airline.iata == iata.upper().strip())
            .first()
        )

    def get_by_icao(self, icao: str) -> Airline | None:
        return (
            self._session.query(Airline)
            .filter(Airline.icao == icao.upper().strip())
            .first()
        )

    def list_all(self, limit: int = 200) -> list[Airline]:
        return self._session.query(Airline).limit(limit).all()

    def count(self) -> int:
        return self._session.query(Airline).count()

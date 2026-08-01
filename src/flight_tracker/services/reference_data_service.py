import logging
import pathlib

from sqlalchemy.orm import Session

from flight_tracker.providers.openflights_provider import (
    download_airlines,
    download_airports,
    download_routes,
)
from flight_tracker.repository.airline_repo import AirlineRepo
from flight_tracker.repository.airport_repo import AirportRepo
from flight_tracker.repository.route_repo import RouteRepo

log = logging.getLogger(__name__)


class ReferenceDataService:
    def __init__(self, db_session: Session, cache_dir: pathlib.Path):
        self._session = db_session
        self._cache_dir = cache_dir
        self._airport_repo = AirportRepo(db_session)
        self._route_repo = RouteRepo(db_session)
        self._airline_repo = AirlineRepo(db_session)

    def load_all(self, force: bool = False) -> dict[str, int]:
        airports = download_airports(self._cache_dir, force=force)
        self._airport_repo.upsert_many(airports)
        log.info("Loaded %d airports", len(airports))

        routes = download_routes(self._cache_dir, force=force)
        self._route_repo.upsert_many(routes)
        log.info("Loaded %d routes", len(routes))

        airlines = download_airlines(self._cache_dir, force=force)
        self._airline_repo.upsert_many(airlines)
        log.info("Loaded %d airlines", len(airlines))

        return {
            "airports": len(airports),
            "routes": len(routes),
            "airlines": len(airlines),
        }

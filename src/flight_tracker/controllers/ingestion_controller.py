"""Controller that orchestrates ingestion on each scheduler tick."""

import logging

from sqlalchemy.orm import Session, sessionmaker

from flight_tracker.config import settings
from flight_tracker.providers.opensky_provider import OpenSkyProvider
from flight_tracker.repository.flight_state_repo import FlightStateRepo
from flight_tracker.services.ingestion_service import IngestionService

log = logging.getLogger(__name__)


class IngestionController:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory
        self._provider = OpenSkyProvider()

    def handle_tick(self) -> int:
        with self._session_factory() as db_session:
            repo = FlightStateRepo(db_session)
            service = IngestionService(provider=self._provider, repo=repo)
            count = service.run_once(bbox=settings.opensky_bbox)
            log.info("Ingestion tick complete: %d states", count)
        return count

"""Pipeline that wires APScheduler to controllers for periodic execution."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session, sessionmaker

from flight_tracker.config import settings
from flight_tracker.controllers.ingestion_controller import IngestionController
from flight_tracker.models.orm import create_engine_safe
from flight_tracker.repository.flight_state_repo import FlightStateRepo

log = logging.getLogger(__name__)


def build_pipeline() -> BackgroundScheduler:
    engine = create_engine_safe(settings.database_url)
    session_factory: sessionmaker[Session] = sessionmaker(bind=engine)

    ingestion = IngestionController(session_factory)

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        ingestion.handle_tick,
        "interval",
        seconds=settings.opensky_poll_seconds,
        id="ingest_states",
        replace_existing=True,
    )

    scheduler.add_job(
        _prune_states,
        "interval",
        hours=1,
        id="prune_states",
        replace_existing=True,
        args=[session_factory],
    )

    log.info(
        "Pipeline started: polling OpenSky every %d s (bbox=%s), pruning every hour",
        settings.opensky_poll_seconds,
        settings.opensky_bbox,
    )
    return scheduler


def _prune_states(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        repo = FlightStateRepo(session)
        deleted = repo.prune_old_states(max_age_hours=24)
        if deleted:
            log.info("Pruned %d old flight state rows", deleted)

#!/usr/bin/env python3
import argparse
import logging
import signal
import sys
from time import sleep

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flight_tracker.config import settings
from flight_tracker.logging import setup_logging
from flight_tracker.models.orm import init_db

log = logging.getLogger(__name__)


def cmd_init_db() -> None:
    init_db(settings.database_url)
    log.info("Database initialized at %s", settings.database_url)


def cmd_ingest_once() -> None:
    from flight_tracker.controllers.ingestion_controller import IngestionController

    engine = create_engine(settings.database_url)
    session_factory = sessionmaker(bind=engine)
    controller = IngestionController(session_factory)
    count = controller.handle_tick()
    log.info("Ingested %d states (one-shot)", count)


def cmd_run_pipeline() -> None:
    from flight_tracker.pipeline import build_pipeline

    scheduler = build_pipeline()

    def shutdown(signum: int, frame: object) -> None:
        log.info("Shutdown signal received; stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    scheduler.start()
    log.info("Pipeline running. Press Ctrl+C to stop.")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)


def cmd_serve_backend() -> None:
    import uvicorn
    uvicorn.run("flight_tracker.api:app", host="0.0.0.0", port=8000, reload=False)


def cmd_not_implemented(name: str) -> None:
    log.info("Command '%s' is not implemented yet", name)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="FlightTracker")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Initialize the database schema")
    sub.add_parser("ingest-once", help="Fetch states once and exit")
    sub.add_parser("run-pipeline", help="Start the scheduler pipeline")
    sub.add_parser("serve-backend", help="Launch the FastAPI backend")

    args = parser.parse_args()

    match args.command:
        case "init-db":
            cmd_init_db()
        case "ingest-once":
            cmd_ingest_once()
        case "run-pipeline":
            cmd_run_pipeline()
        case "serve-backend":
            cmd_serve_backend()
        case _:
            cmd_not_implemented(args.command)

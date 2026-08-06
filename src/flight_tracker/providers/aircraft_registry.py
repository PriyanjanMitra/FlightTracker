"""Local aircraft registry backed by the OpenSky aircraft database snapshot.

Resolves icao24 -> registration details (typecode, manufacturer, model, owner)
from a compact SQLite index built from the OpenSky aircraft database CSV.
"""

import logging
import pathlib
import sqlite3
import threading

from flight_tracker.models.dtos import AircraftInfo

DEFAULT_DB = pathlib.Path("data/aircraft_registry.db")

log = logging.getLogger(__name__)


class AircraftRegistry:
    """Read-only lookup of aircraft registration data by icao24."""

    def __init__(self, db_path: pathlib.Path | str = DEFAULT_DB) -> None:
        self._db_path = pathlib.Path(db_path)
        self._ready = False
        self._local = threading.local()
        self._open()

    def _open(self) -> None:
        if not self._db_path.exists():
            log.warning("Aircraft registry DB not found at %s", self._db_path)
            return
        try:
            conn = self._conn_for_thread()
            conn.execute("SELECT 1 FROM aircraft LIMIT 1")
            self._ready = True
            log.info("Aircraft registry loaded from %s", self._db_path)
        except sqlite3.Error as exc:
            log.warning("Failed to open aircraft registry %s: %s", self._db_path, exc)

    def _conn_for_thread(self) -> sqlite3.Connection:
        """Return a SQLite connection bound to the current thread."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self._db_path), check_same_thread=True)
            self._local.conn = conn
        return conn

    @property
    def available(self) -> bool:
        return self._ready

    def lookup(self, icao24: str) -> AircraftInfo | None:
        """Return aircraft registration info for an icao24, or None when unknown."""
        if not self._ready:
            return None
        try:
            conn = self._conn_for_thread()
            row = conn.execute(
                "SELECT icao24, typecode, manufacturer, model, registration, operator "
                "FROM aircraft WHERE icao24 = ?",
                (icao24.lower(),),
            ).fetchone()
        except sqlite3.Error as exc:
            log.warning("Aircraft registry lookup failed for %s: %s", icao24, exc)
            return None
        if not row:
            return None
        icao24, typecode, manufacturer, model, registration, operator = row
        return AircraftInfo(
            icao24=icao24,
            type=model or typecode or None,
            icao_type=typecode or None,
            manufacturer=manufacturer or None,
            registration=registration or None,
            owner=operator or None,
        )


registry = AircraftRegistry()

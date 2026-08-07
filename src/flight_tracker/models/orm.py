from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    event,
    inspect,
    text,
)
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class FlightState(Base):
    __tablename__ = "flight_states"
    __table_args__ = (
        Index("ix_flight_states_last_contact", "last_contact"),
        Index("ix_flight_states_icao_fetched", "icao24", "fetched_at"),
        Index("ix_flight_states_icao24_last_contact", "icao24", "last_contact", unique=True),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    icao24 = Column(String(6), nullable=False, index=True)
    callsign = Column(String(8), nullable=True)
    origin_country = Column(String(64), nullable=True)
    longitude = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    baro_altitude = Column(Float, nullable=True)
    velocity = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    vertical_rate = Column(Float, nullable=True)
    on_ground = Column(Boolean, nullable=True)
    last_contact = Column(Integer, nullable=False)
    category = Column(Integer, nullable=True)
    fetched_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


def create_engine_safe(database_url: str, **kwargs: Any) -> Any:
    from sqlalchemy.pool import NullPool

    kwargs.setdefault("poolclass", NullPool)
    connect_args = kwargs.pop("connect_args", {})
    connect_args.setdefault("timeout", 10)
    engine = _create_engine(database_url, connect_args=connect_args, **kwargs)

    @event.listens_for(engine, "connect")
    def _set_wal(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    return engine


def init_db(database_url: str) -> None:
    engine = create_engine_safe(database_url)

    # Migrate existing tables: deduplicate and create indexes
    with engine.connect() as conn:
        conn.execute(text("PRAGMA busy_timeout=10000"))
        inspector = inspect(engine)
        if "flight_states" in inspector.get_table_names():
            conn.execute(text("""
                DELETE FROM flight_states
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM flight_states
                    GROUP BY icao24, last_contact
                )
            """))
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_flight_states_icao24_last_contact
                ON flight_states(icao24, last_contact)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_flight_states_last_contact
                ON flight_states(last_contact)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_flight_states_icao_fetched
                ON flight_states(icao24, fetched_at)
            """))
        conn.commit()

    Base.metadata.create_all(engine)

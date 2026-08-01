import importlib
import pathlib


def test_settings_importable() -> None:
    from flight_tracker.config import settings

    assert settings.database_url == "sqlite:///data/flight_tracker.db"


def test_create_engine_safe_in_memory() -> None:
    from flight_tracker.models.orm import create_engine_safe

    engine = create_engine_safe("sqlite://")
    with engine.connect() as conn:
        result = conn.execute(importlib.import_module("sqlalchemy").text("SELECT 1"))
        assert result.scalar() == 1


def test_init_db_creates_tables(tmp_path: pathlib.Path) -> None:
    from flight_tracker.models.orm import init_db

    db = tmp_path / "test.db"
    url = f"sqlite:///{db}"
    init_db(url)

    from sqlalchemy import inspect

    engine = importlib.import_module("flight_tracker.models.orm").create_engine_safe(
        url
    )
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "airports" in tables
    assert "routes" in tables
    assert "airlines" in tables

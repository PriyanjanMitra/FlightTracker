#!/usr/bin/env python3
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from flight_tracker.config import settings as _settings
from flight_tracker.models.orm import init_db as _init_db

_init_db(_settings.database_url)
print(f"Database initialized at {_settings.database_url}")

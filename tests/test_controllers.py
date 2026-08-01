"""Tests for the ingestion controller."""

from unittest.mock import patch

from sqlalchemy.orm import sessionmaker

from flight_tracker.controllers.ingestion_controller import IngestionController
from flight_tracker.models.dtos import FlightStateDTO


def _make_controller(db_session):
    factory = sessionmaker(bind=db_session.get_bind())
    return IngestionController(factory)


def test_handle_tick_returns_state_count(db_session):
    controller = _make_controller(db_session)
    with patch(
        "flight_tracker.providers.opensky_provider.OpenSkyProvider.fetch_states"
    ) as mock_fetch:
        mock_fetch.return_value = []
        count = controller.handle_tick()
    assert count == 0


def test_handle_tick_persists_states(db_session):
    controller = _make_controller(db_session)
    with patch(
        "flight_tracker.providers.opensky_provider.OpenSkyProvider.fetch_states"
    ) as mock_fetch:
        mock_fetch.return_value = [
            FlightStateDTO(
                icao24="abc",
                callsign="UAL1",
                origin_country="US",
                longitude=-70.0,
                latitude=40.0,
                baro_altitude=10000.0,
                velocity=250.0,
                heading=180.0,
                on_ground=False,
                last_contact=1000,
            ),
        ]
        count = controller.handle_tick()
    assert count == 1
    from flight_tracker.models.orm import FlightState
    assert db_session.query(FlightState).count() == 1

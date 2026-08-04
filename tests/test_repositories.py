"""Tests for FlightStateRepo."""

from datetime import UTC, datetime, timedelta

from flight_tracker.repository.flight_state_repo import FlightStateRepo


def _row(**kw):
    return {
        "icao24": kw.get("icao24", "abc123"),
        "callsign": kw.get("callsign", "UAL1"),
        "origin_country": kw.get("origin_country", "US"),
        "longitude": kw.get("longitude", -70.0),
        "latitude": kw.get("latitude", 40.0),
        "baro_altitude": kw.get("baro_altitude", 10000.0),
        "velocity": kw.get("velocity", 250.0),
        "heading": kw.get("heading", 180.0),
        "vertical_rate": kw.get("vertical_rate", 0.0),
        "on_ground": kw.get("on_ground", False),
        "last_contact": kw.get("last_contact", int(datetime.now(UTC).timestamp())),
        "category": kw.get("category", None),
        "fetched_at": kw.get("fetched_at", datetime.now(UTC)),
    }


def test_upsert_many_persists_rows(db_session):
    repo = FlightStateRepo(db_session)
    count = repo.upsert_many([_row()])
    assert count == 1
    assert repo.count() == 1


def test_latest_states_returns_unique_icao24(db_session):
    repo = FlightStateRepo(db_session)
    now = datetime.now(UTC)
    repo.upsert_many([
        _row(icao24="a", fetched_at=now),
        _row(icao24="a", fetched_at=now + timedelta(seconds=10)),
        _row(icao24="b", fetched_at=now),
    ])
    latest = repo.latest_states(limit=10)
    assert len(latest) == 2
    icaos = {r.icao24 for r in latest}
    assert icaos == {"a", "b"}


def test_states_in_window_filters_by_time(db_session):
    repo = FlightStateRepo(db_session)
    repo.upsert_many([
        _row(last_contact=100),
        _row(last_contact=200, icao24="b"),
        _row(last_contact=300, icao24="c"),
    ])
    rows = repo.states_in_window(150, 250)
    assert len(rows) == 1
    assert rows[0].icao24 == "b"


def test_count_returns_total(db_session):
    repo = FlightStateRepo(db_session)
    assert repo.count() == 0
    repo.upsert_many([_row(), _row(icao24="b")])
    assert repo.count() == 2


def test_prune_old_states_removes_expired(db_session):
    repo = FlightStateRepo(db_session)
    now = datetime.now(UTC)
    repo.upsert_many([
        _row(icao24="a", fetched_at=now - timedelta(hours=48)),
        _row(icao24="b", fetched_at=now),
    ])
    deleted = repo.prune_old_states(max_age_hours=24)
    assert deleted == 1
    assert repo.count() == 1
    assert repo.latest_states(limit=10)[0].icao24 == "b"


def test_upsert_updates_existing_row(db_session):
    repo = FlightStateRepo(db_session)
    ts = int(datetime.now(UTC).timestamp())
    repo.upsert_many([_row(icao24="a", last_contact=ts, callsign="OLD")])
    repo.upsert_many([_row(icao24="a", last_contact=ts, callsign="NEW")])
    assert repo.count() == 1
    assert repo.latest_states(limit=10)[0].callsign == "NEW"

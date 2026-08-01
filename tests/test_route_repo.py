"""Tests for RouteRepo."""

from flight_tracker.repository.route_repo import RouteRepo


def _route(**kw):
    return {
        "airline": kw.get("airline", "BA"),
        "airline_id": kw.get("airline_id", 1355),
        "source_airport": kw.get("source_airport", "LHR"),
        "source_airport_id": kw.get("source_airport_id", 507),
        "destination_airport": kw.get("destination_airport", "JFK"),
        "destination_airport_id": kw.get("destination_airport_id", 3854),
        "codeshare": kw.get("codeshare", None),
        "stops": kw.get("stops", 0),
        "equipment": kw.get("equipment", "744"),
    }


def test_upsert_many_persists(db_session):
    repo = RouteRepo(db_session)
    saved = repo.upsert_many([_route()])
    assert len(saved) == 1
    assert repo.count() == 1


def test_get_by_source(db_session):
    repo = RouteRepo(db_session)
    repo.upsert_many([_route(source_airport="LHR"), _route(source_airport="JFK")])
    rows = repo.get_by_source("lhr")
    assert len(rows) == 1


def test_get_by_destination(db_session):
    repo = RouteRepo(db_session)
    repo.upsert_many([_route(destination_airport="JFK"), _route(destination_airport="LAX")])
    rows = repo.get_by_destination("jfk")
    assert len(rows) == 1


def test_list_returns_all_up_to_limit(db_session):
    repo = RouteRepo(db_session)
    repo.upsert_many([_route() for _ in range(5)])
    assert len(repo.list_all(limit=3)) == 3


def test_count(db_session):
    repo = RouteRepo(db_session)
    assert repo.count() == 0
    repo.upsert_many([_route()])
    assert repo.count() == 1

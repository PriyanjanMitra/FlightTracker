"""Tests for AirlineRepo."""

from flight_tracker.repository.airline_repo import AirlineRepo


def _airline(**kw):
    return {
        "id": kw.get("id", 24),
        "name": kw.get("name", "American Airlines"),
        "iata": kw.get("iata", "AA"),
        "icao": kw.get("icao", "AAL"),
        "callsign": kw.get("callsign", "AMERICAN"),
        "country": kw.get("country", "United States"),
        "active": kw.get("active", "Y"),
    }


def test_upsert_many_persists(db_session):
    repo = AirlineRepo(db_session)
    saved = repo.upsert_many([_airline(id=1), _airline(id=2, iata="BA")])
    assert len(saved) == 2
    assert repo.count() == 2


def test_upsert_updates_existing(db_session):
    repo = AirlineRepo(db_session)
    repo.upsert_many([_airline(id=1, name="Old")])
    repo.upsert_many([_airline(id=1, name="New")])
    assert repo.count() == 1
    al = repo.get_by_iata("AA")
    assert al is not None
    assert al.name == "New"


def test_get_by_iata(db_session):
    repo = AirlineRepo(db_session)
    repo.upsert_many([_airline(id=1)])
    al = repo.get_by_iata("aa")
    assert al is not None
    assert al.iata == "AA"


def test_get_by_icao(db_session):
    repo = AirlineRepo(db_session)
    repo.upsert_many([_airline(id=1)])
    al = repo.get_by_icao("aal")
    assert al is not None


def test_list_all(db_session):
    repo = AirlineRepo(db_session)
    repo.upsert_many([_airline(id=1), _airline(id=2, iata="BA")])
    assert len(repo.list_all()) == 2


def test_count(db_session):
    repo = AirlineRepo(db_session)
    assert repo.count() == 0
    repo.upsert_many([_airline(id=1)])
    assert repo.count() == 1

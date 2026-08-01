"""Tests for AirportRepo."""

from flight_tracker.repository.airport_repo import AirportRepo


def _airport(**kw):
    return {
        "id": kw.get("id", 1),
        "iata": kw.get("iata", "LHR"),
        "icao": kw.get("icao", "EGLL"),
        "name": kw.get("name", "Heathrow"),
        "city": kw.get("city", "London"),
        "country": kw.get("country", "UK"),
        "latitude": kw.get("latitude", 51.47),
        "longitude": kw.get("longitude", -0.46),
        "altitude": kw.get("altitude", 83),
        "timezone": kw.get("timezone", "0"),
        "dst": kw.get("dst", "E"),
        "type": kw.get("type", "large_airport"),
        "source": kw.get("source", "OurAirports"),
    }


def test_upsert_many_persists(db_session):
    repo = AirportRepo(db_session)
    rows = [_airport(id=1), _airport(id=2, iata="JFK")]
    saved = repo.upsert_many(rows)
    assert len(saved) == 2
    assert repo.count() == 2


def test_get_by_iata(db_session):
    repo = AirportRepo(db_session)
    repo.upsert_many([_airport(id=1)])
    ap = repo.get_by_iata("lhr")
    assert ap is not None
    assert ap.iata == "LHR"


def test_get_by_iata_case_insensitive(db_session):
    repo = AirportRepo(db_session)
    repo.upsert_many([_airport(id=1)])
    ap = repo.get_by_iata("lhr")
    assert ap is not None


def test_get_by_icao(db_session):
    repo = AirportRepo(db_session)
    repo.upsert_many([_airport(id=1)])
    ap = repo.get_by_icao("egll")
    assert ap is not None


def test_list_all(db_session):
    repo = AirportRepo(db_session)
    repo.upsert_many([_airport(id=1), _airport(id=2, iata="JFK")])
    assert len(repo.list_all()) == 2


def test_count(db_session):
    repo = AirportRepo(db_session)
    assert repo.count() == 0
    repo.upsert_many([_airport(id=1)])
    assert repo.count() == 1


def test_get_by_iata_not_found(db_session):
    repo = AirportRepo(db_session)
    assert repo.get_by_iata("ZZZ") is None

"""Tests for the adsbdb provider."""

import responses

from flight_tracker.providers.adsbdb_provider import ADSBDB_API, AdsbdbProvider

_ICAO = "398565"
_URL = f"{ADSBDB_API}/aircraft/{_ICAO}"


def _payload():
    return {
        "response": {
            "aircraft": {
                "type": "EMB-190 LR",
                "icao_type": "E190",
                "manufacturer": "Embraer",
                "mode_s": "398565",
                "registration": "F-HBLF",
                "registered_owner": "Air France HOP",
            },
            "flightroute": {
                "callsign": "AFR23SB",
                "airline": {
                    "name": "Air France",
                    "icao": "AFR",
                    "iata": "AF",
                    "country": "France",
                    "country_iso": "FR",
                    "callsign": "AIRFRANS",
                },
                "origin": {
                    "iata_code": "CDG",
                    "icao_code": "LFPG",
                    "latitude": 49.012798,
                    "longitude": 2.55,
                    "municipality": "Paris",
                    "name": "Charles de Gaulle International Airport",
                },
                "destination": {
                    "iata_code": "MAD",
                    "icao_code": "LEMD",
                    "latitude": 40.471926,
                    "longitude": -3.56264,
                    "municipality": "Madrid",
                    "name": "Adolfo Suárez Madrid–Barajas Airport",
                },
            },
        }
    }


@responses.activate
def test_fetch_flight_info_parses_aircraft_and_airline():
    responses.add(responses.Response(method="GET", url=_URL, json=_payload(), status=200))
    provider = AdsbdbProvider()
    info = provider.fetch_flight_info(_ICAO, callsign="AFR23SB")

    assert info is not None
    assert info.aircraft is not None
    assert info.aircraft.type == "EMB-190 LR"
    assert info.aircraft.icao_type == "E190"
    assert info.aircraft.manufacturer == "Embraer"
    assert info.aircraft.registration == "F-HBLF"
    assert info.aircraft.icao24 == _ICAO

    assert info.airline is not None
    assert info.airline.name == "Air France"
    assert info.airline.icao == "AFR"
    assert info.airline.iata == "AF"


@responses.activate
def test_fetch_flight_info_returns_none_on_404():
    responses.add(responses.Response(method="GET", url=_URL, json={"response": ""}, status=404))
    provider = AdsbdbProvider()
    assert provider.fetch_flight_info(_ICAO) is None

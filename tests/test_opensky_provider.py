"""Tests for the OpenSky provider."""

from unittest.mock import patch

import responses

from flight_tracker.providers.opensky_provider import (
    AUTH_URL,
    OPENSKY_API,
    OpenSkyProvider,
    _load_auth,
)


def _mock_response(json_data, status_code=200):
    resp = responses.Response(method="GET", url=OPENSKY_API, json=json_data, status=status_code)
    return resp

@responses.activate
def test_fetch_states_returns_parsed_dtos():
    raw_states = [
        ["abc123", "UAL1  ", "US", 1234567890, 1234567890,
             -70.0, 40.0, 10000.0, False, 250.0, 180.0, 0.0,
             None, None, None, None, None, None],
    ]
    responses.add(
        responses.Response(method="GET", url=OPENSKY_API, json={"states": raw_states}, status=200)
    )
    provider = OpenSkyProvider()
    results = provider.fetch_states()
    assert len(results) == 1
    dto = results[0]
    assert dto.icao24 == "abc123"
    assert dto.callsign == "UAL1"
    assert dto.origin_country == "US"
    assert dto.longitude == -70.0
    assert dto.latitude == 40.0
    assert dto.baro_altitude == 10000.0
    assert dto.velocity == 250.0
    assert dto.heading == 180.0
    assert dto.on_ground is False
    assert dto.vertical_rate == 0.0


@responses.activate
def test_fetch_states_passes_bbox_params():
    responses.add(
        responses.Response(
            method="POST", url=AUTH_URL,
            json={"access_token": "t", "expires_in": 1800}, status=200,
        )
    )
    responses.add(
        responses.Response(method="GET", url=OPENSKY_API, json={"states": []}, status=200)
    )
    with patch("flight_tracker.providers.opensky_provider._load_auth", return_value=("id", "sec")):
        provider = OpenSkyProvider()
        provider.fetch_states(bbox="10,20,30,40")
    states_req = [c for c in responses.calls if c.request.url.startswith(OPENSKY_API)][0].request
    assert "lamin" in states_req.params
    assert float(states_req.params["lamin"]) == 10.0
    assert float(states_req.params["lamax"]) == 20.0
    assert float(states_req.params["lomin"]) == 30.0
    assert float(states_req.params["lomax"]) == 40.0


@responses.activate
def test_fetch_states_skips_invalid_rows():
    raw_states = [
        None,
        ["abc123", None, "US", 1234567890, 1234567890, None, None, None, None, None, None],
        ["abc123", "UAL1", "US", 1234567890, 1234567890, -70.0, 40.0, 10000.0, False, 250.0, 180.0],
    ]
    responses.add(
        responses.Response(method="GET", url=OPENSKY_API, json={"states": raw_states}, status=200)
    )
    provider = OpenSkyProvider()
    results = provider.fetch_states()
    assert len(results) == 2


@responses.activate
def test_fetch_states_handles_429():
    responses.add(
        responses.Response(method="GET", url=OPENSKY_API, json={}, status=429)
    )
    provider = OpenSkyProvider()
    result = provider.fetch_states()
    assert result == []


@responses.activate
def test_returns_empty_on_bad_status():
    responses.add(
        responses.Response(method="GET", url=OPENSKY_API, json={}, status=500)
    )
    provider = OpenSkyProvider()
    result = provider.fetch_states()
    assert result == []


@responses.activate
def test_retries_on_timeout():
    responses.add(
        responses.Response(method="GET", url=OPENSKY_API, json={}, status=200),
    )
    # Patch requests.get to raise Timeout twice then succeed
    original_get = __import__("requests").get

    call_count = 0

    def _fake_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise __import__("requests").ConnectionError("timeout")
        return original_get(*args, **kwargs)

    with patch("flight_tracker.providers.opensky_provider.requests.get", _fake_get):
        provider = OpenSkyProvider()
        result = provider.fetch_states()
    assert result == []
    assert call_count == 3


@responses.activate
def test_fetch_states_uses_bearer_token_when_credentials_available():
    responses.add(
        responses.Response(
            method="POST",
            url=AUTH_URL,
            json={"access_token": "tok123", "expires_in": 1800},
            status=200,
        )
    )
    responses.add(
        responses.Response(method="GET", url=OPENSKY_API, json={"states": []}, status=200)
    )
    with patch("flight_tracker.providers.opensky_provider._load_auth", return_value=("id", "sec")):
        provider = OpenSkyProvider()
        provider.fetch_states()
    req = responses.calls[1].request
    assert req.headers.get("Authorization") == "Bearer tok123"


@responses.activate
def test_fetch_states_anonymous_when_no_credentials():
    responses.add(
        responses.Response(method="GET", url=OPENSKY_API, json={"states": []}, status=200)
    )
    with patch("flight_tracker.providers.opensky_provider._load_auth", return_value=None):
        provider = OpenSkyProvider()
        provider.fetch_states()
    req = responses.calls[0].request
    assert req.headers.get("Authorization") is None


@patch("flight_tracker.providers.opensky_provider.pathlib.Path")
def test_load_auth_returns_credentials_from_json(mock_path_cls):
    mock_creds = (
        mock_path_cls.return_value.resolve.return_value.parent.parent.parent.parent.__truediv__.return_value
    )
    mock_creds.exists.return_value = True
    mock_creds.read_text.return_value = '{"clientId": "api-client", "clientSecret": "s3cret"}'
    result = _load_auth()
    assert result == ("api-client", "s3cret")


@patch("flight_tracker.providers.opensky_provider.pathlib.Path")
def test_load_auth_falls_back_to_settings(mock_path_cls):
    mock_creds = (
        mock_path_cls.return_value.resolve.return_value.parent.parent.parent.parent.__truediv__.return_value
    )
    mock_creds.exists.return_value = False
    with patch("flight_tracker.config.settings") as mock_settings:
        mock_settings.opensky_username = "bob"
        mock_settings.opensky_password = "hunter2"
        result = _load_auth()
    assert result == ("bob", "hunter2")


@patch("flight_tracker.providers.opensky_provider.pathlib.Path")
def test_load_auth_returns_none_when_no_credentials(mock_path_cls):
    mock_creds = (
        mock_path_cls.return_value.resolve.return_value.parent.parent.parent.parent.__truediv__.return_value
    )
    mock_creds.exists.return_value = False
    with patch("flight_tracker.config.settings") as mock_settings:
        mock_settings.opensky_username = ""
        mock_settings.opensky_password = ""
        result = _load_auth()
    assert result is None

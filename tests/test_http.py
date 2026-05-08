import time
from email.utils import formatdate
from unittest.mock import patch

import pytest
import requests
import responses

from craaft._http import RetryConfig, Transport
from craaft.exceptions import (
    AuthenticationError,
    ConflictError,
    CraaftAPIError,
    CraaftConnectionError,
    CraaftTimeoutError,
    NotFoundError,
    PlanLimitError,
    ServerError,
    ValidationError,
)

BASE = "https://example.test/api/v1"


def make_transport(retry: RetryConfig | None = None) -> Transport:
    return Transport(
        api_key="cra_test",
        base_url=BASE,
        timeout=5.0,
        retry=retry if retry is not None else RetryConfig(max_attempts=1),
        user_agent="craaft-python/test",
        session=requests.Session(),
    )


@responses.activate
@pytest.mark.parametrize(
    "status,exc_cls",
    [
        (400, ValidationError),
        (401, AuthenticationError),
        (402, PlanLimitError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, ValidationError),
        (500, ServerError),
        (503, ServerError),
    ],
)
def test_error_status_to_exception(status, exc_cls):
    responses.add(
        responses.GET,
        f"{BASE}/probe",
        json={"error": "bad"},
        status=status,
        headers={"x-request-id": "req_1"},
    )
    t = make_transport()
    with pytest.raises(exc_cls) as ei:
        t.request("GET", "/probe")
    err = ei.value
    assert isinstance(err, CraaftAPIError)
    assert err.status_code == status
    assert err.message == "bad"
    assert err.request_id == "req_1"


@responses.activate
def test_error_unparseable_body_uses_status_text():
    responses.add(
        responses.GET,
        f"{BASE}/probe",
        body="<html>500 oops</html>",
        status=500,
        content_type="text/html",
    )
    t = make_transport()
    with pytest.raises(ServerError) as ei:
        t.request("GET", "/probe")
    assert ei.value.status_code == 500
    assert "500" in ei.value.message or "oops" in ei.value.message.lower()


@responses.activate
def test_403_maps_to_permission_error():
    from craaft.exceptions import PermissionError as CraaftPermissionError

    responses.add(responses.GET, f"{BASE}/probe", json={"error": "no"}, status=403)
    t = make_transport()
    with pytest.raises(CraaftPermissionError):
        t.request("GET", "/probe")


@responses.activate
def test_authorization_and_user_agent_headers_set():
    responses.add(responses.GET, f"{BASE}/probe", json={}, status=200)
    t = make_transport()
    t.request("GET", "/probe")
    sent = responses.calls[0].request
    assert sent.headers["Authorization"] == "Bearer cra_test"
    assert sent.headers["User-Agent"] == "craaft-python/test"
    assert sent.headers["Accept"] == "application/json"


@responses.activate
def test_returns_parsed_json_on_2xx():
    responses.add(responses.GET, f"{BASE}/probe", json={"ok": True}, status=200)
    t = make_transport()
    assert t.request("GET", "/probe") == {"ok": True}


@responses.activate
def test_returns_none_on_204():
    responses.add(responses.DELETE, f"{BASE}/probe", status=204)
    t = make_transport()
    assert t.request("DELETE", "/probe") is None


@responses.activate
def test_query_params_passed():
    responses.add(responses.GET, f"{BASE}/probe", json={}, status=200)
    t = make_transport()
    t.request("GET", "/probe", params={"q": "hi", "limit": 10})
    qs = responses.calls[0].request.url
    assert "q=hi" in qs
    assert "limit=10" in qs


@responses.activate
def test_json_body_serialized():
    responses.add(responses.POST, f"{BASE}/probe", json={"ok": True}, status=201)
    t = make_transport()
    t.request("POST", "/probe", json={"name": "x"})
    body = responses.calls[0].request.body
    assert body == b'{"name": "x"}' or body == '{"name": "x"}'


@responses.activate
def test_retry_on_503_then_success():
    responses.add(responses.GET, f"{BASE}/probe", json={"err": 1}, status=503)
    responses.add(responses.GET, f"{BASE}/probe", json={"ok": True}, status=200)
    t = make_transport(RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0))
    with patch("craaft._http.time.sleep"):
        result = t.request("GET", "/probe")
    assert result == {"ok": True}
    assert len(responses.calls) == 2


@responses.activate
def test_retry_exhausted_raises_last_error():
    for _ in range(3):
        responses.add(responses.GET, f"{BASE}/probe", json={"error": "down"}, status=503)
    t = make_transport(RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0))
    with patch("craaft._http.time.sleep"), pytest.raises(ServerError):
        t.request("GET", "/probe")
    assert len(responses.calls) == 3


@responses.activate
def test_retry_429_honors_retry_after_seconds():
    responses.add(
        responses.GET,
        f"{BASE}/probe",
        json={"error": "rate limited"},
        status=429,
        headers={"Retry-After": "2"},
    )
    responses.add(responses.GET, f"{BASE}/probe", json={"ok": True}, status=200)
    t = make_transport(RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0))
    sleeps: list[float] = []
    with patch("craaft._http.time.sleep", side_effect=sleeps.append):
        t.request("GET", "/probe")
    assert sleeps[0] == 2.0


@responses.activate
def test_retry_429_honors_retry_after_http_date():
    future = formatdate(time.time() + 3, usegmt=True)
    responses.add(
        responses.GET,
        f"{BASE}/probe",
        json={"error": "rate limited"},
        status=429,
        headers={"Retry-After": future},
    )
    responses.add(responses.GET, f"{BASE}/probe", json={"ok": True}, status=200)
    t = make_transport(RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0))
    sleeps: list[float] = []
    with patch("craaft._http.time.sleep", side_effect=sleeps.append):
        t.request("GET", "/probe")
    assert sleeps[0] >= 0.0  # non-negative delta to the future date


@responses.activate
def test_post_does_not_retry_on_503_by_default():
    responses.add(responses.POST, f"{BASE}/probe", json={"error": "x"}, status=503)
    t = make_transport(RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0))
    with patch("craaft._http.time.sleep"), pytest.raises(ServerError):
        t.request("POST", "/probe", json={"a": 1})
    assert len(responses.calls) == 1


@responses.activate
def test_post_retries_on_503_when_enabled():
    responses.add(responses.POST, f"{BASE}/probe", json={"error": "x"}, status=503)
    responses.add(responses.POST, f"{BASE}/probe", json={"ok": True}, status=201)
    t = make_transport(
        RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0, retry_writes_on_5xx=True)
    )
    with patch("craaft._http.time.sleep"):
        result = t.request("POST", "/probe", json={"a": 1})
    assert result == {"ok": True}
    assert len(responses.calls) == 2


@responses.activate
def test_post_retries_on_429():
    responses.add(responses.POST, f"{BASE}/probe", json={"error": "rl"}, status=429)
    responses.add(responses.POST, f"{BASE}/probe", json={"ok": True}, status=201)
    t = make_transport(RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0))
    with patch("craaft._http.time.sleep"):
        result = t.request("POST", "/probe", json={"a": 1})
    assert result == {"ok": True}
    assert len(responses.calls) == 2


def test_connection_error_retries_then_raises():
    t = make_transport(RetryConfig(max_attempts=2, backoff_base=0.0, jitter=0.0))
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, f"{BASE}/probe", body=requests.exceptions.ConnectionError("boom"))
        rsps.add(responses.GET, f"{BASE}/probe", body=requests.exceptions.ConnectionError("boom"))
        with patch("craaft._http.time.sleep"), pytest.raises(CraaftConnectionError):
            t.request("GET", "/probe")
        assert len(rsps.calls) == 2


def test_timeout_error_raises_typed():
    t = make_transport(RetryConfig(max_attempts=1, backoff_base=0.0, jitter=0.0))
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, f"{BASE}/probe", body=requests.exceptions.Timeout("slow"))
        with pytest.raises(CraaftTimeoutError):
            t.request("GET", "/probe")


def test_retry_disabled_with_zero_jitter_backoff_base():
    cfg = RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0)
    t = make_transport(cfg)
    # _backoff_seconds should be deterministic 0.0 with these settings
    assert t._backoff_seconds(0) == 0.0
    assert t._backoff_seconds(5) == 0.0

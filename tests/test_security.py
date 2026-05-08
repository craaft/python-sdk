"""Tests for the hardening fixes (token leakage, URL validation, retry safety)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests
import responses

from craaft import CraaftClient, CraaftError, RetryConfig
from craaft._http import (
    _MAX_RETRY_AFTER_SECONDS,
    Transport,
    _parse_message,
    _parse_retry_after,
)

# ---------------------------------------------------------------------------
# Token leakage: Transport.__repr__ must never expose api_key
# ---------------------------------------------------------------------------


def test_transport_repr_does_not_leak_api_key():
    t = Transport(
        api_key="cra_supersecret",
        base_url="https://example.test/api/v1",
        timeout=5.0,
        retry=RetryConfig(max_attempts=1),
        user_agent="ua/1",
        session=requests.Session(),
    )
    r = repr(t)
    assert "cra_supersecret" not in r
    assert "api_key" not in r


def test_client_transport_repr_does_not_leak_api_key():
    c = CraaftClient(api_key="cra_supersecret_token_123")
    assert "cra_supersecret_token_123" not in repr(c._transport)


# ---------------------------------------------------------------------------
# Base URL validation: require https except for localhost
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/api/v1",
        "ftp://example.com/api/v1",
        "javascript:alert(1)",
        "://noscheme",
    ],
)
def test_base_url_rejects_non_https(url):
    with pytest.raises(CraaftError):
        CraaftClient(api_key="cra_x", base_url=url)


def test_base_url_rejects_http_env_downgrade(monkeypatch):
    monkeypatch.setenv("CRAAFT_BASE_URL", "http://craaft.io/api/v1")
    with pytest.raises(CraaftError, match="https"):
        CraaftClient(api_key="cra_x")


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8080/api/v1",
        "http://127.0.0.1:8080/api/v1",
    ],
)
def test_base_url_allows_http_localhost(url):
    c = CraaftClient(api_key="cra_x", base_url=url)
    assert c._transport.base_url == url


# ---------------------------------------------------------------------------
# Token validation: shape, whitespace
# ---------------------------------------------------------------------------


def test_token_strip_whitespace():
    c = CraaftClient(api_key="  cra_abc123  ")
    assert c._transport.api_key == "cra_abc123"


@pytest.mark.parametrize("bad", ["", "   ", "not-a-token", "abc_xyz", "cra_"])
def test_token_rejects_bad_shape(bad):
    with pytest.raises(CraaftError):
        CraaftClient(api_key=bad)


# ---------------------------------------------------------------------------
# User-Agent validation: no control characters
# ---------------------------------------------------------------------------


def test_user_agent_rejects_crlf_injection():
    with pytest.raises(CraaftError):
        CraaftClient(api_key="cra_x", user_agent="ua\r\nX-Admin: true")


def test_user_agent_rejects_null_byte():
    with pytest.raises(CraaftError):
        CraaftClient(api_key="cra_x", user_agent="ua\x00X")


# ---------------------------------------------------------------------------
# session.verify must remain enabled
# ---------------------------------------------------------------------------


def test_refuses_session_with_verify_disabled():
    sess = requests.Session()
    sess.verify = False
    with pytest.raises(CraaftError, match="verify"):
        CraaftClient(api_key="cra_x", session=sess)


def test_accepts_session_with_custom_ca_bundle_path():
    # A path string for verify is fine - it's how custom CAs are loaded.
    sess = requests.Session()
    sess.verify = "/etc/ssl/some-ca.pem"
    c = CraaftClient(api_key="cra_x", session=sess)
    assert c._transport.session.verify == "/etc/ssl/some-ca.pem"


# ---------------------------------------------------------------------------
# Retry-After cap and naive-datetime handling
# ---------------------------------------------------------------------------


def test_retry_after_seconds_is_capped():
    assert _parse_retry_after("99999999") == _MAX_RETRY_AFTER_SECONDS


def test_retry_after_negative_clamps_to_zero():
    assert _parse_retry_after("-5") == 0.0


def test_retry_after_http_date_naive_treated_as_utc():
    # parsedate_to_datetime returns a naive datetime when input has no tz.
    # We must not let .timestamp() interpret it in local time.
    result = _parse_retry_after("Wed, 21 Oct 2099 07:28:00")  # no GMT/UTC suffix
    assert result is not None
    assert result <= _MAX_RETRY_AFTER_SECONDS


# ---------------------------------------------------------------------------
# Error message scrubbing (log-injection defense)
# ---------------------------------------------------------------------------


def test_parse_message_strips_control_chars():
    msg = _parse_message(b'{"error":"oops\nFAKE LOG ENTRY\rextra"}')
    assert "\n" not in msg
    assert "\r" not in msg


def test_parse_message_keeps_tabs():
    msg = _parse_message(b'{"error":"col1\tcol2"}')
    assert "\t" in msg


# ---------------------------------------------------------------------------
# RetryConfig is frozen and not shared across default clients
# ---------------------------------------------------------------------------


def test_retry_config_is_frozen():
    import dataclasses

    cfg = RetryConfig()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.max_attempts = 999  # type: ignore[misc]


def test_default_retry_configs_are_independent_instances():
    c1 = CraaftClient(api_key="cra_x")
    c2 = CraaftClient(api_key="cra_y")
    assert c1._transport.retry is not c2._transport.retry


# ---------------------------------------------------------------------------
# Connection-error retry on writes is OFF by default
# ---------------------------------------------------------------------------


def test_post_does_not_retry_on_connection_error_by_default():
    from craaft.exceptions import CraaftConnectionError

    t = Transport(
        api_key="cra_x",
        base_url="https://example.test/api/v1",
        timeout=5.0,
        retry=RetryConfig(max_attempts=3, backoff_base=0.0, jitter=0.0),
        user_agent="ua/1",
        session=requests.Session(),
    )
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://example.test/api/v1/probe",
            body=requests.exceptions.ConnectionError("boom"),
        )
        with patch("craaft._http.time.sleep"), pytest.raises(CraaftConnectionError):
            t.request("POST", "/probe", json={"a": 1})
        assert len(rsps.calls) == 1


def test_post_retries_on_connection_error_when_opted_in():
    t = Transport(
        api_key="cra_x",
        base_url="https://example.test/api/v1",
        timeout=5.0,
        retry=RetryConfig(
            max_attempts=3,
            backoff_base=0.0,
            jitter=0.0,
            retry_writes_on_network_error=True,
        ),
        user_agent="ua/1",
        session=requests.Session(),
    )
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://example.test/api/v1/probe",
            body=requests.exceptions.ConnectionError("boom"),
        )
        rsps.add(
            responses.POST,
            "https://example.test/api/v1/probe",
            json={"ok": True},
            status=201,
        )
        with patch("craaft._http.time.sleep"):
            result = t.request("POST", "/probe", json={"a": 1})
        assert result == {"ok": True}
        assert len(rsps.calls) == 2


# ---------------------------------------------------------------------------
# Path injection: IDs with ?, /, # must be safely encoded
# ---------------------------------------------------------------------------


@responses.activate
def test_resource_id_with_query_chars_is_url_encoded():
    # If unencoded, project_id would smuggle "?force=1" as a query string.
    responses.add(
        responses.GET,
        "https://craaft.io/api/v1/projects/abc%3Fforce%3D1",
        json={"error": "not found"},
        status=404,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(CraaftError):
        c.projects.get("abc?force=1")
    # The URL that was hit should be encoded, not raw.
    assert any("%3Fforce%3D1" in call.request.url for call in responses.calls)


@responses.activate
def test_resource_id_with_path_traversal_is_encoded():
    responses.add(
        responses.GET,
        "https://craaft.io/api/v1/projects/abc%2F..%2Fadmin",
        json={"error": "not found"},
        status=404,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(CraaftError):
        c.projects.get("abc/../admin")
    assert any("%2F..%2Fadmin" in call.request.url for call in responses.calls)


def test_resource_id_empty_string_is_rejected():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError):
        c.projects.get("")


# ---------------------------------------------------------------------------
# Response body size cap
# ---------------------------------------------------------------------------


@responses.activate
def test_response_size_cap_raises():
    big = b"x" * (1024 * 1024)  # 1 MiB
    responses.add(
        responses.GET,
        "https://craaft.io/api/v1/projects",
        body=big,
        content_type="application/json",
        status=200,
    )
    # Override the cap to something tiny.
    c = CraaftClient(api_key="cra_x")
    c._transport.max_response_bytes = 1024
    with pytest.raises(CraaftError, match="exceeded maximum size"):
        c.projects.list()


# ---------------------------------------------------------------------------
# Redirects are refused, not silently followed
# ---------------------------------------------------------------------------


@responses.activate
def test_redirect_is_not_followed():
    responses.add(
        responses.GET,
        "https://craaft.io/api/v1/projects",
        status=302,
        headers={"Location": "https://evil.example.com/steal"},
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(CraaftError, match="redirect"):
        c.projects.list()
    # And exactly one request was made (no follow).
    assert len(responses.calls) == 1


# ---------------------------------------------------------------------------
# Malformed JSON on 2xx surfaces as CraaftError, not a raw JSONDecodeError
# ---------------------------------------------------------------------------


@responses.activate
def test_malformed_json_2xx_raises_craaft_error():
    responses.add(
        responses.GET,
        "https://craaft.io/api/v1/projects",
        body=b"this is not JSON",
        content_type="application/json",
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(CraaftError, match="non-JSON"):
        c.projects.list()


# ---------------------------------------------------------------------------
# SSLError is surfaced immediately, not retried
# ---------------------------------------------------------------------------


def test_ssl_error_is_not_retried():
    from craaft.exceptions import CraaftConnectionError

    t = Transport(
        api_key="cra_x",
        base_url="https://example.test/api/v1",
        timeout=5.0,
        retry=RetryConfig(max_attempts=5, backoff_base=0.0, jitter=0.0),
        user_agent="ua/1",
        session=requests.Session(),
    )
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://example.test/api/v1/probe",
            body=requests.exceptions.SSLError("bad cert"),
        )
        with pytest.raises(CraaftConnectionError):
            t.request("GET", "/probe")
        # Exactly one attempt, no retries.
        assert len(rsps.calls) == 1

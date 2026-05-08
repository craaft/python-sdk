from unittest.mock import patch

import pytest
import requests
import responses

from craaft import CraaftClient
from craaft._http import RetryConfig
from craaft.exceptions import CraaftError


def test_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("CRAAFT_API_TOKEN", raising=False)
    with pytest.raises(CraaftError, match="API key required"):
        CraaftClient()


def test_init_uses_env_var(monkeypatch):
    monkeypatch.setenv("CRAAFT_API_TOKEN", "cra_env")
    c = CraaftClient()
    assert c._transport.api_key == "cra_env"


def test_init_arg_overrides_env(monkeypatch):
    monkeypatch.setenv("CRAAFT_API_TOKEN", "cra_env")
    c = CraaftClient(api_key="cra_arg")
    assert c._transport.api_key == "cra_arg"


def test_default_base_url(monkeypatch):
    monkeypatch.delenv("CRAAFT_BASE_URL", raising=False)
    c = CraaftClient(api_key="cra_x")
    assert c._transport.base_url == "https://craaft.io/api/v1"


def test_custom_base_url():
    c = CraaftClient(api_key="cra_x", base_url="http://localhost:8080/api/v1")
    assert c._transport.base_url == "http://localhost:8080/api/v1"


def test_base_url_from_env(monkeypatch):
    monkeypatch.setenv("CRAAFT_BASE_URL", "https://staging.example.com/api/v1")
    c = CraaftClient(api_key="cra_x")
    assert c._transport.base_url == "https://staging.example.com/api/v1"


def test_base_url_arg_overrides_env(monkeypatch):
    monkeypatch.setenv("CRAAFT_BASE_URL", "https://staging.example.com/api/v1")
    c = CraaftClient(api_key="cra_x", base_url="https://prod.example.com/api/v1")
    assert c._transport.base_url == "https://prod.example.com/api/v1"


def test_default_user_agent_includes_version():
    from craaft import __version__

    c = CraaftClient(api_key="cra_x")
    assert __version__ in c._transport.user_agent
    assert "craaft-python" in c._transport.user_agent


def test_custom_user_agent():
    c = CraaftClient(api_key="cra_x", user_agent="my-app/1.0")
    assert c._transport.user_agent == "my-app/1.0"


def test_retry_none_disables_retries():
    c = CraaftClient(api_key="cra_x", retry=None)
    assert c._transport.retry.max_attempts == 1


def test_custom_retry_config():
    cfg = RetryConfig(max_attempts=5)
    c = CraaftClient(api_key="cra_x", retry=cfg)
    assert c._transport.retry.max_attempts == 5


def test_resource_sub_clients_present():
    c = CraaftClient(api_key="cra_x")
    assert c.me is not None
    assert c.projects is not None
    assert c.cards is not None
    assert c.comments is not None
    assert c.columns is not None


def test_context_manager_closes():
    with patch.object(requests.Session, "close") as close_mock:
        with CraaftClient(api_key="cra_x") as c:
            assert c is not None
        close_mock.assert_called_once()


def test_close_closes_session():
    with patch.object(requests.Session, "close") as close_mock:
        c = CraaftClient(api_key="cra_x")
        c.close()
        close_mock.assert_called_once()


def test_inject_session():
    sess = requests.Session()
    c = CraaftClient(api_key="cra_x", session=sess)
    assert c._transport.session is sess


@responses.activate
def test_end_to_end_authorization_header():
    responses.add(
        responses.GET,
        "https://craaft.io/api/v1/me",
        json={
            "id": "u1",
            "email": "a@b.co",
            "name": "A",
            "username": "a",
            "avatarUrl": None,
            "hasPassword": True,
        },
        status=200,
    )
    c = CraaftClient(api_key="cra_test")
    c.me.get()
    assert responses.calls[0].request.headers["Authorization"] == "Bearer cra_test"

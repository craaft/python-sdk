import json

import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import CraaftPermissionError, PlanLimitError, ValidationError

BASE = "https://craaft.io/api/v1"


def _webhook(extras: dict | None = None) -> dict:
    base = {
        "id": "wh1",
        "endpointId": "ep1",
        "url": "https://example.com/hook",
        "secret": "shh-its-a-secret",
        "description": "CI notifier",
        "format": "craaft",
        "events": [],
        "active": True,
        "createdAt": "2026-07-18T10:00:00Z",
        "recentDeliveries": [],
    }
    if extras:
        base.update(extras)
    return base


@responses.activate
def test_list_for_project():
    responses.add(
        responses.GET,
        f"{BASE}/projects/p1/webhooks",
        json={"webhooks": [_webhook()], "eventCatalogue": ["card.created", "card.updated"]},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    result = c.webhooks.list_for_project("p1")
    assert result.webhooks[0].id == "wh1"
    assert result.webhooks[0].secret == "shh-its-a-secret"
    assert result.event_catalogue == ["card.created", "card.updated"]


@responses.activate
def test_list_for_project_402_for_free_plan():
    responses.add(
        responses.GET,
        f"{BASE}/projects/p1/webhooks",
        json={"error": "webhooks are a paid feature"},
        status=402,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(PlanLimitError):
        c.webhooks.list_for_project("p1")


@responses.activate
def test_list_for_project_403_for_non_admin():
    responses.add(
        responses.GET,
        f"{BASE}/projects/p1/webhooks",
        json={"error": "requires board admin"},
        status=403,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(CraaftPermissionError):
        c.webhooks.list_for_project("p1")


@responses.activate
def test_create_required_fields_only():
    responses.add(
        responses.POST, f"{BASE}/projects/p1/webhooks", json=_webhook(), status=201
    )
    c = CraaftClient(api_key="cra_x")
    w = c.webhooks.create("p1", url="https://example.com/hook")
    assert w.id == "wh1"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"url": "https://example.com/hook"}


@responses.activate
def test_create_with_all_fields():
    responses.add(
        responses.POST,
        f"{BASE}/projects/p1/webhooks",
        json=_webhook({"format": "slack", "events": ["card.created"]}),
        status=201,
    )
    c = CraaftClient(api_key="cra_x")
    c.webhooks.create(
        "p1",
        url="https://hooks.slack.com/services/x",
        description="Slack alerts",
        format="slack",
        events=["card.created"],
    )
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "url": "https://hooks.slack.com/services/x",
        "description": "Slack alerts",
        "format": "slack",
        "events": ["card.created"],
    }


@responses.activate
def test_create_400_bad_url():
    responses.add(
        responses.POST,
        f"{BASE}/projects/p1/webhooks",
        json={"error": "invalid webhook url: private address"},
        status=400,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError):
        c.webhooks.create("p1", url="http://127.0.0.1/hook")


@responses.activate
def test_update_partial():
    responses.add(
        responses.PATCH, f"{BASE}/webhooks/wh1", json=_webhook({"active": False}), status=200
    )
    c = CraaftClient(api_key="cra_x")
    w = c.webhooks.update("wh1", active=False)
    assert w.active is False
    body = json.loads(responses.calls[0].request.body)
    assert body == {"active": False}


@responses.activate
def test_update_omits_unspecified_fields():
    responses.add(responses.PATCH, f"{BASE}/webhooks/wh1", json=_webhook(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.webhooks.update("wh1", url="https://example.com/new-hook")
    body = json.loads(responses.calls[0].request.body)
    assert body == {"url": "https://example.com/new-hook"}


@responses.activate
def test_update_402_when_downgraded_to_free():
    responses.add(
        responses.PATCH,
        f"{BASE}/webhooks/wh1",
        json={"error": "integrations need Pro"},
        status=402,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(PlanLimitError):
        c.webhooks.update("wh1", active=True)


@responses.activate
def test_delete_returns_none():
    responses.add(responses.DELETE, f"{BASE}/webhooks/wh1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.webhooks.delete("wh1") is None


@responses.activate
def test_delete_not_plan_gated_even_on_free():
    # Delete has no 402 path - a downgraded workspace can still clean up.
    responses.add(responses.DELETE, f"{BASE}/webhooks/wh1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.webhooks.delete("wh1") is None
    assert responses.calls[0].request.method == "DELETE"

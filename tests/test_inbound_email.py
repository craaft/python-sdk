import json

import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import ConflictError, PlanLimitError

BASE = "https://craaft.io/api/v1"


def _address(extras: dict | None = None) -> dict:
    base = {
        "email": "in-abc123@mail.craaft.io",
        "token": "abc123",
        "targetColumn": None,
        "active": True,
        "createdAt": "2026-07-18T10:00:00Z",
    }
    if extras:
        base.update(extras)
    return base


@responses.activate
def test_get_disabled():
    responses.add(
        responses.GET,
        f"{BASE}/projects/p1/inbound-email",
        json={"enabled": False, "address": None},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    status = c.inbound_email.get("p1")
    assert status.enabled is False
    assert status.address is None


@responses.activate
def test_get_enabled():
    responses.add(
        responses.GET,
        f"{BASE}/projects/p1/inbound-email",
        json={"enabled": True, "address": _address()},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    status = c.inbound_email.get("p1")
    assert status.enabled is True
    assert status.address is not None
    assert status.address.token == "abc123"


@responses.activate
def test_get_402_for_free_plan():
    responses.add(
        responses.GET,
        f"{BASE}/projects/p1/inbound-email",
        json={"error": "email-to-card is a paid feature"},
        status=402,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(PlanLimitError):
        c.inbound_email.get("p1")


@responses.activate
def test_enable_without_target_column():
    responses.add(
        responses.POST, f"{BASE}/projects/p1/inbound-email", json=_address(), status=201
    )
    c = CraaftClient(api_key="cra_x")
    addr = c.inbound_email.enable("p1")
    assert addr.email == "in-abc123@mail.craaft.io"
    body = json.loads(responses.calls[0].request.body)
    assert body == {}


@responses.activate
def test_enable_with_target_column():
    responses.add(
        responses.POST,
        f"{BASE}/projects/p1/inbound-email",
        json=_address({"targetColumn": "todo"}),
        status=201,
    )
    c = CraaftClient(api_key="cra_x")
    addr = c.inbound_email.enable("p1", target_column="todo")
    assert addr.target_column == "todo"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"targetColumn": "todo"}


@responses.activate
def test_enable_409_when_already_enabled():
    responses.add(
        responses.POST,
        f"{BASE}/projects/p1/inbound-email",
        json={"error": "inbound email already enabled for this board"},
        status=409,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ConflictError):
        c.inbound_email.enable("p1")


@responses.activate
def test_update_active_only():
    responses.add(
        responses.PATCH,
        f"{BASE}/projects/p1/inbound-email",
        json=_address({"active": False}),
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    addr = c.inbound_email.update("p1", active=False)
    assert addr.active is False
    body = json.loads(responses.calls[0].request.body)
    assert body == {"active": False}


@responses.activate
def test_update_target_column_empty_string_clears_it():
    responses.add(
        responses.PATCH,
        f"{BASE}/projects/p1/inbound-email",
        json=_address({"targetColumn": None}),
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    c.inbound_email.update("p1", target_column="")
    body = json.loads(responses.calls[0].request.body)
    assert body == {"targetColumn": ""}


@responses.activate
def test_update_omits_target_column_when_unset():
    responses.add(responses.PATCH, f"{BASE}/projects/p1/inbound-email", json=_address(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.inbound_email.update("p1", active=True)
    body = json.loads(responses.calls[0].request.body)
    assert "targetColumn" not in body
    assert body == {"active": True}


@responses.activate
def test_update_rotate_mints_a_new_token():
    responses.add(
        responses.PATCH,
        f"{BASE}/projects/p1/inbound-email",
        json=_address({"token": "newtoken456"}),
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    addr = c.inbound_email.update("p1", rotate=True)
    assert addr.token == "newtoken456"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"rotate": True}


@responses.activate
def test_disable_returns_none():
    responses.add(responses.DELETE, f"{BASE}/projects/p1/inbound-email", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.inbound_email.disable("p1") is None

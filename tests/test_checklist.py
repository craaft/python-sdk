import json

import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import NotFoundError, ValidationError

BASE = "https://craaft.io/api/v1"


def _item(extras: dict | None = None) -> dict:
    base = {
        "id": "cl1",
        "cardId": "card1",
        "text": "write tests",
        "done": False,
        "position": 1.0,
        "createdAt": "2026-07-18T10:00:00Z",
        "updatedAt": "2026-07-18T10:00:00Z",
    }
    if extras:
        base.update(extras)
    return base


@responses.activate
def test_update_translates_fields():
    responses.add(
        responses.PATCH, f"{BASE}/checklist/cl1", json=_item({"done": True}), status=200
    )
    c = CraaftClient(api_key="cra_x")
    item = c.checklist.update("cl1", text="write more tests", done=True)
    assert item.done is True
    body = json.loads(responses.calls[0].request.body)
    assert body == {"text": "write more tests", "done": True}


@responses.activate
def test_update_omits_unspecified():
    responses.add(responses.PATCH, f"{BASE}/checklist/cl1", json=_item(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.checklist.update("cl1", done=False)
    body = json.loads(responses.calls[0].request.body)
    assert body == {"done": False}


@responses.activate
def test_update_400_text_too_long():
    responses.add(
        responses.PATCH,
        f"{BASE}/checklist/cl1",
        json={"error": "text too long"},
        status=400,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError):
        c.checklist.update("cl1", text="x" * 1001)


@responses.activate
def test_delete():
    responses.add(responses.DELETE, f"{BASE}/checklist/cl1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.checklist.delete("cl1") is None


@responses.activate
def test_delete_404():
    responses.add(
        responses.DELETE, f"{BASE}/checklist/missing", json={"error": "nope"}, status=404
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(NotFoundError):
        c.checklist.delete("missing")

import json

import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import ConflictError

BASE = "https://craaft.io/api/v1"


def _col():
    return {
        "id": "c1",
        "key": "todo",
        "title": "Doing",
        "color": "#bbb",
        "position": 2.0,
        "isDone": True,
        "cardLimit": 5,
    }


@responses.activate
def test_update_translates_fields():
    responses.add(responses.PATCH, f"{BASE}/columns/c1", json=_col(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.columns.update(
        "c1", title="Doing", color="#bbb", position=2.0, is_done=True, card_limit=5
    )
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "title": "Doing",
        "color": "#bbb",
        "position": 2.0,
        "isDone": True,
        "cardLimit": 5,
    }


@responses.activate
def test_update_omits_card_limit_when_unset():
    responses.add(responses.PATCH, f"{BASE}/columns/c1", json=_col(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.columns.update("c1", title="x")
    body = json.loads(responses.calls[0].request.body)
    assert "cardLimit" not in body


@responses.activate
def test_delete():
    responses.add(responses.DELETE, f"{BASE}/columns/c1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.columns.delete("c1") is None


@responses.activate
def test_delete_409_conflict():
    responses.add(
        responses.DELETE, f"{BASE}/columns/c1", json={"error": "non-empty"}, status=409
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ConflictError):
        c.columns.delete("c1")

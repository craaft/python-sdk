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
def test_archive():
    responses.add(
        responses.POST, f"{BASE}/columns/c1/archive", json={"archived": 3}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    assert c.columns.archive("c1") == 3


@responses.activate
def test_archive_non_done_column_returns_zero():
    # Non-done columns still answer 200 with an empty result rather than an
    # error - the caller checks the count, not the status code.
    responses.add(
        responses.POST, f"{BASE}/columns/c1/archive", json={"archived": 0}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    assert c.columns.archive("c1") == 0


@responses.activate
def test_archive_with_ids():
    responses.add(
        responses.POST,
        f"{BASE}/columns/c1/archive",
        json={"archived": 3, "ids": ["card1", "card2", "card3"]},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    result = c.columns.archive_with_ids("c1")
    assert result.archived == 3
    assert result.ids == ["card1", "card2", "card3"]


@responses.activate
def test_archive_with_ids_non_done_column_returns_zero():
    # Non-done columns still answer 200 with an empty result rather than an
    # error - the caller checks the count, not the status code.
    responses.add(
        responses.POST, f"{BASE}/columns/c1/archive", json={"archived": 0, "ids": []}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    result = c.columns.archive_with_ids("c1")
    assert result.archived == 0
    assert result.ids == []


@responses.activate
def test_delete_409_conflict():
    responses.add(
        responses.DELETE, f"{BASE}/columns/c1", json={"error": "non-empty"}, status=409
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ConflictError):
        c.columns.delete("c1")

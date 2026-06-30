import json

import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import ValidationError

BASE = "https://craaft.io/api/v1"


def _card(extras: dict | None = None) -> dict:
    base = {
        "id": "card1",
        "projectId": "p1",
        "column": "todo",
        "title": "x",
        "position": 1.0,
        "description": None,
        "dueDate": None,
        "assignedUserId": None,
        "size": None,
        "priority": None,
        "createdBy": None,
        "attachmentCount": 0,
        "tags": [],
        "createdAt": "2026-05-08T10:00:00Z",
        "updatedAt": "2026-05-08T10:00:00Z",
    }
    if extras:
        base.update(extras)
    return base


def _summary(extras: dict | None = None) -> dict:
    base = {
        "id": "card1",
        "projectId": "p1",
        "projectName": "Demo",
        "columnKey": "todo",
        "columnTitle": "To Do",
        "title": "x",
    }
    if extras:
        base.update(extras)
    return base


def _comment():
    return {
        "id": "cm1",
        "cardId": "card1",
        "authorId": "u1",
        "body": "hi",
        "createdAt": "2026-05-08T10:00:00Z",
        "updatedAt": "2026-05-08T10:00:00Z",
    }


@responses.activate
def test_update_translates_fields():
    responses.add(responses.PATCH, f"{BASE}/cards/card1", json=_card(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.cards.update(
        "card1",
        title="New",
        description="d",
        column="doing",
        position=2.0,
        due_date="2026-06-01T10:00:00+00:00",
        assigned_user_id="u2",
        size=5,
        priority="urgent",
        tags=["launch"],
    )
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "title": "New",
        "description": "d",
        "column": "doing",
        "position": 2.0,
        "dueDate": "2026-06-01T10:00:00+00:00",
        "assignedUserId": "u2",
        "size": 5,
        "priority": "urgent",
        "tags": ["launch"],
    }


@responses.activate
def test_update_serializes_datetime_with_tz():
    from datetime import datetime, timezone

    responses.add(responses.PATCH, f"{BASE}/cards/card1", json=_card(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.cards.update(
        "card1", due_date=datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    body = json.loads(responses.calls[0].request.body)
    assert body["dueDate"] == "2026-06-01T10:00:00+00:00"


@responses.activate
def test_update_serializes_naive_datetime_as_utc():
    from datetime import datetime

    responses.add(responses.PATCH, f"{BASE}/cards/card1", json=_card(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.cards.update("card1", due_date=datetime(2026, 6, 1, 10, 0, 0))
    body = json.loads(responses.calls[0].request.body)
    assert body["dueDate"] == "2026-06-01T10:00:00+00:00"


@responses.activate
def test_update_omits_unspecified():
    responses.add(responses.PATCH, f"{BASE}/cards/card1", json=_card(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.cards.update("card1", title="x")
    body = json.loads(responses.calls[0].request.body)
    assert body == {"title": "x"}


@responses.activate
def test_delete():
    responses.add(responses.DELETE, f"{BASE}/cards/card1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.cards.delete("card1") is None


@responses.activate
def test_upcoming():
    payload = [
        _summary(
            {
                "dueDate": "2026-05-05T00:00:00+02:00",
                "assignedUserId": "u1",
                "priority": "high",
            }
        )
    ]
    responses.add(responses.GET, f"{BASE}/cards/upcoming", json=payload, status=200)
    c = CraaftClient(api_key="cra_x")
    cards = c.cards.upcoming()
    assert cards[0].project_name == "Demo"
    assert cards[0].column_title == "To Do"
    assert cards[0].column_key == "todo"
    assert cards[0].priority == "high"
    assert cards[0].due_date is not None


@responses.activate
def test_search_default_limit():
    responses.add(responses.GET, f"{BASE}/search", json={"cards": [_summary()]}, status=200)
    c = CraaftClient(api_key="cra_x")
    cards = c.cards.search(q="hello")
    assert len(cards) == 1
    assert cards[0].column_key == "todo"
    qs = responses.calls[0].request.url
    assert "q=hello" in qs
    assert "limit=20" in qs


@responses.activate
def test_search_custom_limit():
    responses.add(responses.GET, f"{BASE}/search", json={"cards": []}, status=200)
    c = CraaftClient(api_key="cra_x")
    c.cards.search(q="hello", limit=5)
    qs = responses.calls[0].request.url
    assert "limit=5" in qs


def test_search_limit_validation():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError):
        c.cards.search(q="x", limit=0)
    with pytest.raises(ValueError):
        c.cards.search(q="x", limit=51)


@responses.activate
def test_search_400_raises_validation():
    responses.add(responses.GET, f"{BASE}/search", json={"error": "bad q"}, status=400)
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError):
        c.cards.search(q="")


@responses.activate
def test_list_comments():
    responses.add(responses.GET, f"{BASE}/cards/card1/comments", json=[_comment()], status=200)
    c = CraaftClient(api_key="cra_x")
    comments = c.cards.list_comments("card1")
    assert comments[0].body == "hi"


@responses.activate
def test_add_comment():
    responses.add(responses.POST, f"{BASE}/cards/card1/comments", json=_comment(), status=201)
    c = CraaftClient(api_key="cra_x")
    cm = c.cards.add_comment("card1", body="hi")
    assert cm.id == "cm1"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"body": "hi"}

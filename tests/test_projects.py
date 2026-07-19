import json

import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import (
    CraaftPermissionError,
    NotFoundError,
    PlanLimitError,
    ValidationError,
)

BASE = "https://craaft.io/api/v1"


def _proj():
    return {
        "id": "p1",
        "workspaceId": "w1",
        "name": "Demo",
        "description": None,
        "isFavorite": False,
        "publicToken": None,
        "backgroundImage": None,
        "backgroundColor": None,
        "colorScheme": None,
        "textColor": "light",
        "canUploadAttachments": False,
        "totalCards": 0,
        "columnCounts": {},
        "columns": [],
        "createdAt": "2026-05-08T10:00:00Z",
        "updatedAt": "2026-05-08T10:00:00Z",
    }


def _card():
    return {
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


def _col():
    return {
        "id": "c1",
        "key": "todo",
        "title": "To Do",
        "color": "#aaa",
        "position": 1.0,
        "isDone": False,
        "cardLimit": None,
    }


@responses.activate
def test_list():
    responses.add(responses.GET, f"{BASE}/projects", json=[_proj()], status=200)
    c = CraaftClient(api_key="cra_x")
    projects = c.projects.list()
    assert len(projects) == 1
    assert projects[0].id == "p1"


@responses.activate
def test_get():
    responses.add(responses.GET, f"{BASE}/projects/p1", json=_proj(), status=200)
    c = CraaftClient(api_key="cra_x")
    p = c.projects.get("p1")
    assert p.id == "p1"


@responses.activate
def test_get_404_raises_not_found():
    responses.add(responses.GET, f"{BASE}/projects/missing", json={"error": "nope"}, status=404)
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(NotFoundError):
        c.projects.get("missing")


@responses.activate
def test_create():
    responses.add(responses.POST, f"{BASE}/projects", json=_proj(), status=201)
    c = CraaftClient(api_key="cra_x")
    p = c.projects.create(name="Demo", description="d")
    assert p.id == "p1"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "Demo", "description": "d"}


@responses.activate
def test_create_omits_unset_description():
    responses.add(responses.POST, f"{BASE}/projects", json=_proj(), status=201)
    c = CraaftClient(api_key="cra_x")
    c.projects.create(name="Demo")
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "Demo"}


@responses.activate
def test_create_402_raises_plan_limit():
    responses.add(responses.POST, f"{BASE}/projects", json={"error": "limit"}, status=402)
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(PlanLimitError):
        c.projects.create(name="Demo")


@responses.activate
def test_update_translates_snake_case_to_camel_case():
    responses.add(responses.PATCH, f"{BASE}/projects/p1", json=_proj(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.projects.update(
        "p1",
        name="New",
        description="d",
        is_favorite=True,
        background_image="https://example.com/bg.png",
        background_color="#aabbcc",
        color_scheme="midnight",
        text_color="dark",
        visibility="workspace",
    )
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "name": "New",
        "description": "d",
        "isFavorite": True,
        "backgroundImage": "https://example.com/bg.png",
        "backgroundColor": "#aabbcc",
        "colorScheme": "midnight",
        "textColor": "dark",
        "visibility": "workspace",
    }


@responses.activate
def test_update_omits_unspecified_fields():
    responses.add(responses.PATCH, f"{BASE}/projects/p1", json=_proj(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.projects.update("p1", name="N")
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "N"}


@responses.activate
def test_delete_returns_none():
    responses.add(responses.DELETE, f"{BASE}/projects/p1", status=204)
    c = CraaftClient(api_key="cra_x")
    result = c.projects.delete("p1")
    assert result is None


@responses.activate
def test_list_cards():
    responses.add(responses.GET, f"{BASE}/projects/p1/cards", json=[_card()], status=200)
    c = CraaftClient(api_key="cra_x")
    cards = c.projects.list_cards("p1")
    assert cards[0].id == "card1"


@responses.activate
def test_create_card_required_fields_only():
    responses.add(responses.POST, f"{BASE}/projects/p1/cards", json=_card(), status=201)
    c = CraaftClient(api_key="cra_x")
    c.projects.create_card("p1", title="x", column="todo", position=1.0)
    body = json.loads(responses.calls[0].request.body)
    assert body == {"title": "x", "column": "todo", "position": 1.0}


@responses.activate
def test_create_card_with_description():
    responses.add(responses.POST, f"{BASE}/projects/p1/cards", json=_card(), status=201)
    c = CraaftClient(api_key="cra_x")
    c.projects.create_card(
        "p1",
        title="x",
        column="todo",
        position=1.0,
        description="d",
    )
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "title": "x",
        "column": "todo",
        "position": 1.0,
        "description": "d",
    }


def _milestone(extras: dict | None = None) -> dict:
    base = {
        "id": "m1",
        "projectId": "p1",
        "name": "Beta launch",
        "dueOn": "2026-09-01",
        "achievedAt": None,
        "createdAt": "2026-07-18T10:00:00Z",
        "updatedAt": "2026-07-18T10:00:00Z",
    }
    if extras:
        base.update(extras)
    return base


@responses.activate
def test_bulk_create_cards():
    payload = {"cards": [_card(), dict(_card(), id="card2")]}
    responses.add(
        responses.POST, f"{BASE}/projects/p1/cards/bulk", json=payload, status=201
    )
    c = CraaftClient(api_key="cra_x")
    cards = c.projects.bulk_create_cards(
        "p1",
        [
            {"title": "Ship it", "column": "todo"},
            {
                "title": "Review copy",
                "column": "doing",
                "position": 2.5,
                "description": "Markdown ok",
                "assignedUserId": "u2",
                "size": 3,
                "priority": "high",
                "tags": ["launch"],
            },
        ],
    )
    assert [card.id for card in cards] == ["card1", "card2"]
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "cards": [
            {"title": "Ship it", "column": "todo"},
            {
                "title": "Review copy",
                "column": "doing",
                "position": 2.5,
                "description": "Markdown ok",
                "assignedUserId": "u2",
                "size": 3,
                "priority": "high",
                "tags": ["launch"],
            },
        ]
    }


@responses.activate
def test_bulk_create_cards_serializes_datetime_due_date():
    from datetime import datetime, timezone

    responses.add(
        responses.POST,
        f"{BASE}/projects/p1/cards/bulk",
        json={"cards": [_card()]},
        status=201,
    )
    c = CraaftClient(api_key="cra_x")
    c.projects.bulk_create_cards(
        "p1",
        [
            {
                "title": "x",
                "column": "todo",
                "dueDate": datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc),
            }
        ],
    )
    body = json.loads(responses.calls[0].request.body)
    assert body["cards"][0]["dueDate"] == "2026-08-01T12:00:00+00:00"


def test_bulk_create_cards_item_count_validation():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError):
        c.projects.bulk_create_cards("p1", [])
    with pytest.raises(ValueError):
        c.projects.bulk_create_cards(
            "p1", [{"title": str(i), "column": "todo"} for i in range(101)]
        )


@responses.activate
def test_bulk_create_cards_400_names_offending_index():
    responses.add(
        responses.POST,
        f"{BASE}/projects/p1/cards/bulk",
        json={"error": "cards[3]: title is required"},
        status=400,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError) as exc_info:
        c.projects.bulk_create_cards("p1", [{"title": "", "column": "todo"}])
    assert exc_info.value.message == "cards[3]: title is required"


@responses.activate
def test_list_milestones():
    responses.add(
        responses.GET,
        f"{BASE}/projects/p1/milestones",
        json=[_milestone(), _milestone({"id": "m2", "achievedAt": "2026-07-01T09:00:00Z"})],
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    milestones = c.projects.list_milestones("p1")
    assert [m.id for m in milestones] == ["m1", "m2"]
    assert milestones[0].achieved_at is None
    assert milestones[1].achieved_at is not None
    assert str(milestones[0].due_on) == "2026-09-01"


@responses.activate
def test_add_milestone_with_date_object():
    from datetime import date

    responses.add(
        responses.POST, f"{BASE}/projects/p1/milestones", json=_milestone(), status=201
    )
    c = CraaftClient(api_key="cra_x")
    m = c.projects.add_milestone("p1", name="Beta launch", due_on=date(2026, 9, 1))
    assert m.name == "Beta launch"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "Beta launch", "dueOn": "2026-09-01"}


@responses.activate
def test_add_milestone_with_string_date():
    responses.add(
        responses.POST, f"{BASE}/projects/p1/milestones", json=_milestone(), status=201
    )
    c = CraaftClient(api_key="cra_x")
    c.projects.add_milestone("p1", name="Beta launch", due_on="2026-09-01")
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "Beta launch", "dueOn": "2026-09-01"}


@responses.activate
def test_add_milestone_403_for_non_admin():
    responses.add(
        responses.POST,
        f"{BASE}/projects/p1/milestones",
        json={"error": "board admin required"},
        status=403,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(CraaftPermissionError):
        c.projects.add_milestone("p1", name="Beta launch", due_on="2026-09-01")


@responses.activate
def test_add_column():
    responses.add(responses.POST, f"{BASE}/projects/p1/columns", json=_col(), status=201)
    c = CraaftClient(api_key="cra_x")
    col = c.projects.add_column("p1", title="To Do")
    assert col.title == "To Do"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"title": "To Do"}

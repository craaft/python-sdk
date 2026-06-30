import json

import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import NotFoundError, PlanLimitError

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


@responses.activate
def test_add_column():
    responses.add(responses.POST, f"{BASE}/projects/p1/columns", json=_col(), status=201)
    c = CraaftClient(api_key="cra_x")
    col = c.projects.add_column("p1", title="To Do")
    assert col.title == "To Do"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"title": "To Do"}

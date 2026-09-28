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
def test_archive_posts_and_returns_none():
    responses.add(
        responses.POST,
        f"{BASE}/cards/card1/archive",
        json={"archived": True, "id": "card1"},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    assert c.cards.archive("card1") is None
    assert responses.calls[0].request.method == "POST"


@responses.activate
def test_archive_already_archived_raises_not_found():
    from craaft.exceptions import NotFoundError

    responses.add(
        responses.POST,
        f"{BASE}/cards/card1/archive",
        json={"error": "card not found"},
        status=404,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(NotFoundError):
        c.cards.archive("card1")


@responses.activate
def test_restore_returns_the_full_card():
    responses.add(
        responses.POST,
        f"{BASE}/cards/card1/restore",
        json=_card({"title": "Back on the board"}),
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    card = c.cards.restore("card1")
    assert card.title == "Back on the board"
    assert responses.calls[0].request.method == "POST"


@responses.activate
def test_restore_not_archived_raises_not_found():
    from craaft.exceptions import NotFoundError

    responses.add(
        responses.POST,
        f"{BASE}/cards/card1/restore",
        json={"error": "card not archived"},
        status=404,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(NotFoundError):
        c.cards.restore("card1")


@responses.activate
def test_upcoming():
    from craaft.models import UpcomingCard

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
    assert isinstance(cards[0], UpcomingCard)
    assert cards[0].project_name == "Demo"
    assert cards[0].column_title == "To Do"
    assert cards[0].column_key == "todo"
    assert cards[0].priority == "high"
    assert cards[0].due_date is not None
    # Deprecated fields the upcoming endpoint never sends: present, but
    # always their default rather than raising AttributeError.
    assert cards[0].description is None
    assert cards[0].updated_at is None
    assert cards[0].archived is False


@responses.activate
def test_upcoming_assignee_fields_omitted_when_unset():
    from craaft.models import UpcomingCard

    payload = [_summary({"dueDate": "2026-05-05T00:00:00+02:00"})]
    responses.add(responses.GET, f"{BASE}/cards/upcoming", json=payload, status=200)
    c = CraaftClient(api_key="cra_x")
    cards = c.cards.upcoming()
    assert isinstance(cards[0], UpcomingCard)
    assert cards[0].assigned_user_id is None
    assert cards[0].priority is None


@responses.activate
def test_focus_due_bucket_uses_upcoming_card_shape():
    from craaft.models import UpcomingCard

    responses.add(
        responses.GET,
        f"{BASE}/cards/focus",
        json={
            "due": [_summary({"dueDate": "2026-05-05T00:00:00+02:00", "priority": "high"})],
            "attention": [],
            "hygiene": {"ghosts": 0, "longInProgress": 0, "mineNoDate": 0},
        },
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    focus = c.cards.focus()
    assert isinstance(focus.due[0], UpcomingCard)
    assert focus.due[0].priority == "high"
    assert focus.attention == []
    assert focus.hygiene.ghosts == 0


@responses.activate
def test_search_default_limit():
    from craaft.models import SearchResult

    responses.add(
        responses.GET,
        f"{BASE}/search",
        json={"cards": [_summary({"description": "snippet", "archived": True})]},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    cards = c.cards.search(q="hello")
    assert len(cards) == 1
    assert isinstance(cards[0], SearchResult)
    assert cards[0].column_key == "todo"
    assert cards[0].description == "snippet"
    assert cards[0].archived is True
    # Deprecated fields the search endpoint never sends: present, but
    # always their default rather than raising AttributeError.
    assert cards[0].due_date is None
    assert cards[0].assigned_user_id is None
    assert cards[0].priority is None
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


def _checklist_item(extras: dict | None = None) -> dict:
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
def test_bulk_update_passes_items_verbatim():
    payload = {"cards": [_card(), _card({"id": "card2"})]}
    responses.add(responses.PATCH, f"{BASE}/cards/bulk", json=payload, status=200)
    c = CraaftClient(api_key="cra_x")
    cards = c.cards.bulk_update(
        [
            {"id": "card1", "title": "Renamed", "priority": "urgent"},
            {"id": "card2", "column": "done", "position": 12.0},
        ]
    )
    assert [card.id for card in cards] == ["card1", "card2"]
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "cards": [
            {"id": "card1", "title": "Renamed", "priority": "urgent"},
            {"id": "card2", "column": "done", "position": 12.0},
        ]
    }


@responses.activate
def test_bulk_update_sends_null_to_clear():
    responses.add(
        responses.PATCH, f"{BASE}/cards/bulk", json={"cards": [_card()]}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    c.cards.bulk_update([{"id": "card1", "dueDate": None, "assignedUserId": None}])
    # A key present with None must survive as JSON null (clear), and absent
    # keys must stay absent (leave alone).
    body = json.loads(responses.calls[0].request.body)
    assert body["cards"][0] == {"id": "card1", "dueDate": None, "assignedUserId": None}
    assert "priority" not in body["cards"][0]


@responses.activate
def test_bulk_update_serializes_datetime_due_date():
    from datetime import datetime, timezone

    responses.add(
        responses.PATCH, f"{BASE}/cards/bulk", json={"cards": [_card()]}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    items = [{"id": "card1", "dueDate": datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)}]
    c.cards.bulk_update(items)
    body = json.loads(responses.calls[0].request.body)
    assert body["cards"][0]["dueDate"] == "2026-08-01T12:00:00+00:00"
    # The caller's dict must not be mutated.
    assert isinstance(items[0]["dueDate"], datetime)


def test_bulk_update_item_count_validation():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError):
        c.cards.bulk_update([])
    with pytest.raises(ValueError):
        c.cards.bulk_update([{"id": str(i)} for i in range(101)])


@responses.activate
def test_bulk_update_400_names_offending_index():
    responses.add(
        responses.PATCH,
        f"{BASE}/cards/bulk",
        json={"error": "cards[3]: title is required"},
        status=400,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError) as exc_info:
        c.cards.bulk_update([{"id": "card1", "title": ""}])
    assert exc_info.value.message == "cards[3]: title is required"


@responses.activate
def test_bulk_move_same_board():
    payload = {"cards": [_card({"column": "done"})]}
    responses.add(responses.POST, f"{BASE}/cards/bulk/move", json=payload, status=200)
    c = CraaftClient(api_key="cra_x")
    cards = c.cards.bulk_move(["card1"], column="done")
    assert cards[0].column == "done"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"ids": ["card1"], "column": "done"}


@responses.activate
def test_bulk_move_to_other_board():
    payload = {"cards": [_card({"projectId": "p2", "column": "todo"})]}
    responses.add(responses.POST, f"{BASE}/cards/bulk/move", json=payload, status=200)
    c = CraaftClient(api_key="cra_x")
    cards = c.cards.bulk_move(["card1"], column="todo", target_project_id="p2")
    assert cards[0].project_id == "p2"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"ids": ["card1"], "column": "todo", "targetProjectId": "p2"}


def test_bulk_move_item_count_validation():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError):
        c.cards.bulk_move([], column="done")
    with pytest.raises(ValueError):
        c.cards.bulk_move([str(i) for i in range(101)], column="done")


@responses.activate
def test_bulk_move_400_when_ids_span_boards():
    responses.add(
        responses.POST,
        f"{BASE}/cards/bulk/move",
        json={"error": "cards must belong to the same project"},
        status=400,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError):
        c.cards.bulk_move(["card1", "card2"], column="done")


@responses.activate
def test_bulk_move_422_unknown_column():
    responses.add(
        responses.POST,
        f"{BASE}/cards/bulk/move",
        json={"error": "column does not exist"},
        status=422,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError):
        c.cards.bulk_move(["card1"], column="nope", target_project_id="p2")


@responses.activate
def test_list_checklist():
    responses.add(
        responses.GET,
        f"{BASE}/cards/card1/checklist",
        json=[_checklist_item(), _checklist_item({"id": "cl2", "done": True})],
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    items = c.cards.list_checklist("card1")
    assert [i.id for i in items] == ["cl1", "cl2"]
    assert items[0].done is False
    assert items[1].done is True
    assert items[0].card_id == "card1"


@responses.activate
def test_add_checklist_item():
    responses.add(
        responses.POST,
        f"{BASE}/cards/card1/checklist",
        json=_checklist_item(),
        status=201,
    )
    c = CraaftClient(api_key="cra_x")
    item = c.cards.add_checklist_item("card1", text="write tests")
    assert item.text == "write tests"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"text": "write tests"}


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


@responses.activate
def test_get_fetches_a_single_card():
    responses.add(
        responses.GET,
        f"{BASE}/cards/card1",
        json=_card({"title": "Fetched"}),
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    card = c.cards.get("card1")
    assert card.id == "card1"
    assert card.title == "Fetched"
    assert responses.calls[0].request.method == "GET"


@responses.activate
def test_get_escapes_the_id():
    # Ids arrive from callers unvalidated; a traversal-shaped one must not
    # rewrite the request path.
    responses.add(responses.GET, f"{BASE}/cards/..%2F..%2Fadmin", json=_card())
    c = CraaftClient(api_key="cra_x")
    c.cards.get("../../admin")
    assert "/cards/..%2F..%2Fadmin" in responses.calls[0].request.url


@responses.activate
def test_card_reads_following_flag():
    # The API has always returned `following`; the model used to drop it.
    responses.add(responses.GET, f"{BASE}/cards/card1", json=_card({"following": True}))
    c = CraaftClient(api_key="cra_x")
    assert c.cards.get("card1").following is True


@responses.activate
def test_card_following_defaults_false_when_absent():
    responses.add(responses.GET, f"{BASE}/cards/card1", json=_card())
    c = CraaftClient(api_key="cra_x")
    assert c.cards.get("card1").following is False


@responses.activate
def test_follow_and_unfollow_send_204_shaped_calls():
    responses.add(responses.POST, f"{BASE}/cards/card1/follow", status=204)
    responses.add(responses.DELETE, f"{BASE}/cards/card1/follow", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.cards.follow("card1") is None
    assert c.cards.unfollow("card1") is None
    assert responses.calls[0].request.method == "POST"
    assert responses.calls[1].request.method == "DELETE"


@responses.activate
def test_detail_fetches_the_card_with_its_collections():
    responses.add(
        responses.GET,
        f"{BASE}/cards/card1/detail",
        json={
            "card": _card({"title": "Detailed"}),
            "comments": [
                {
                    "id": "cm1",
                    "cardId": "card1",
                    "authorId": "u1",
                    "body": "hi",
                    "createdAt": "2026-05-08T10:00:00Z",
                }
            ],
            "events": [
                {
                    "id": "ev1",
                    "type": "moved",
                    "fromValue": "todo",
                    "toValue": "doing",
                    "createdAt": "2026-05-08T10:00:00Z",
                }
            ],
            "checklist": [
                {
                    "id": "ck1",
                    "cardId": "card1",
                    "text": "t",
                    "done": False,
                    "position": 1.0,
                    "createdAt": "2026-05-08T10:00:00Z",
                    "updatedAt": "2026-05-08T10:00:00Z",
                }
            ],
            "attachments": [],
        },
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    d = c.cards.detail("card1")
    assert d.card.title == "Detailed"
    assert [x.body for x in d.comments] == ["hi"]
    assert d.events[0].to_value == "doing"
    assert d.checklist[0].text == "t"
    assert d.attachments == []
    assert responses.calls[0].request.method == "GET"

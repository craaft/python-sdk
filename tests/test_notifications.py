import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from craaft import CraaftClient, Notification, NotificationPage
from craaft.exceptions import ValidationError

BASE = "https://craaft.io/api/v1"

ID1 = "11111111-1111-4111-8111-111111111111"
ID2 = "22222222-2222-4222-8222-222222222222"
CARD = "33333333-3333-4333-8333-333333333333"


def _row(extras: dict | None = None) -> dict:
    base = {
        "ids": [ID1],
        "kind": "mention",
        "kinds": ["mention"],
        "details": ["comment"],
        "card": {
            "id": CARD,
            "title": "Ship it",
            "projectId": "p1",
            "projectName": "Launch",
            "archived": False,
        },
        "commentId": "c1",
        "actors": [{"id": "u1", "name": "Alice"}],
        "excerpt": "@bob can you look?",
        "count": 1,
        "createdAt": "2026-07-18T10:00:00.123456Z",
        "seen": False,
        "read": False,
    }
    if extras:
        base.update(extras)
    return base


def _query(call_index: int = 0) -> dict[str, list[str]]:
    return parse_qs(urlparse(responses.calls[call_index].request.url).query)


@responses.activate
def test_list_defaults():
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [_row()], "nextBefore": None},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    page = c.notifications.list()
    assert isinstance(page, NotificationPage)
    assert page.next_before is None
    assert _query() == {"limit": ["30"]}


@responses.activate
def test_list_parses_rows():
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [_row()], "nextBefore": "2026-07-18T09:00:00.5Z"},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    page = c.notifications.list()
    n = page.items[0]
    assert isinstance(n, Notification)
    assert n.ids == [ID1]
    assert n.kind == "mention"
    assert n.kinds == ["mention"]
    assert n.details == ["comment"]
    assert n.card.id == CARD
    assert n.card.title == "Ship it"
    assert n.card.project_id == "p1"
    assert n.card.project_name == "Launch"
    assert n.card.archived is False
    assert n.comment_id == "c1"
    assert n.actors[0].id == "u1"
    assert n.actors[0].name == "Alice"
    assert n.excerpt == "@bob can you look?"
    assert n.count == 1
    assert n.created_at == datetime(2026, 7, 18, 10, 0, 0, 123456, tzinfo=timezone.utc)
    assert n.seen is False
    assert n.read is False
    # The cursor is passed through as the server's string, not reparsed.
    assert page.next_before == "2026-07-18T09:00:00.5Z"


@responses.activate
def test_list_parses_group_and_due_rows():
    group = _row(
        {
            "ids": [ID1, ID2],
            "kind": "group",
            "kinds": ["comment", "moved"],
            "details": ["", "column"],
            "count": 2,
            "seen": True,
        }
    )
    del group["commentId"]
    del group["excerpt"]
    due = _row({"kind": "due", "kinds": ["due"], "details": ["today"], "actors": []})
    del due["commentId"]
    del due["excerpt"]
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [group, due], "nextBefore": None},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    g, d = c.notifications.list().items
    assert g.kind == "group"
    assert g.ids == [ID1, ID2]
    assert g.kinds == ["comment", "moved"]
    assert g.details == ["", "column"]
    assert g.count == 2
    assert g.seen is True
    assert g.comment_id is None
    assert g.excerpt is None
    assert d.kind == "due"
    assert d.actors == []


@responses.activate
def test_list_all_filters():
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [], "nextBefore": None},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    c.notifications.list(
        before="2026-07-18T09:00:00.123456789Z", limit=10, unread=True, kind="mention"
    )
    assert _query() == {
        "before": ["2026-07-18T09:00:00.123456789Z"],
        "limit": ["10"],
        "unread": ["1"],
        "kind": ["mention"],
    }


@responses.activate
def test_list_before_datetime_is_serialized():
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [], "nextBefore": None},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    c.notifications.list(before=datetime(2026, 7, 18, 9, 0))
    assert _query()["before"] == ["2026-07-18T09:00:00+00:00"]


@responses.activate
def test_list_unread_false_omits_param():
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [], "nextBefore": None},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    c.notifications.list(unread=False)
    assert "unread" not in _query()


def test_list_limit_validation():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError):
        c.notifications.list(limit=0)
    with pytest.raises(ValueError):
        c.notifications.list(limit=51)


@responses.activate
def test_list_400_on_unknown_kind():
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"error": "kind must be mention, assigned, comment, moved, updated or due"},
        status=400,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError):
        c.notifications.list(kind="group")  # type: ignore[arg-type]


@responses.activate
def test_iter_all_follows_next_before_not_created_at():
    # Each page's cursor deliberately differs from its last row's createdAt,
    # as it does for a grouped row; the helper must send the cursor.
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={
            "items": [_row({"ids": [ID1], "createdAt": "2026-07-18T10:00:00Z"})],
            "nextBefore": "2026-07-18T08:00:00.000000123Z",
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={
            "items": [_row({"ids": [ID2], "createdAt": "2026-07-18T07:00:00Z"})],
            "nextBefore": None,
        },
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    rows = list(c.notifications.iter_all(kind="mention"))
    assert [r.ids for r in rows] == [[ID1], [ID2]]
    assert len(responses.calls) == 2
    assert _query(0) == {"limit": ["50"], "kind": ["mention"]}
    assert _query(1) == {
        "before": ["2026-07-18T08:00:00.000000123Z"],
        "limit": ["50"],
        "kind": ["mention"],
    }


@responses.activate
def test_iter_all_keeps_paging_past_empty_page():
    # Grouping can leave a page empty while older rows still exist.
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [], "nextBefore": "2026-07-18T08:00:00Z"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [_row()], "nextBefore": None},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    rows = list(c.notifications.iter_all(unread=True, limit=5))
    assert len(rows) == 1
    assert _query(0) == {"limit": ["5"], "unread": ["1"]}
    assert _query(1) == {
        "before": ["2026-07-18T08:00:00Z"],
        "limit": ["5"],
        "unread": ["1"],
    }


@responses.activate
def test_iter_all_is_lazy():
    responses.add(
        responses.GET,
        f"{BASE}/me/notifications",
        json={"items": [_row()], "nextBefore": None},
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    it = c.notifications.iter_all()
    assert len(responses.calls) == 0
    next(it)
    assert len(responses.calls) == 1


@responses.activate
def test_count():
    responses.add(
        responses.GET, f"{BASE}/me/notifications/count", json={"unseen": 4}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    assert c.notifications.count() == 4
    assert responses.calls[0].request.method == "GET"


@responses.activate
def test_mark_seen_string():
    responses.add(
        responses.POST, f"{BASE}/me/notifications/seen", json={"unseen": 0}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    assert c.notifications.mark_seen("2026-07-18T10:00:00.123456Z") == 0
    body = json.loads(responses.calls[0].request.body)
    assert body == {"upTo": "2026-07-18T10:00:00.123456Z"}


@responses.activate
def test_mark_seen_datetime():
    responses.add(
        responses.POST, f"{BASE}/me/notifications/seen", json={"unseen": 2}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    up_to = datetime(2026, 7, 18, 10, 0, 0, 123456, tzinfo=timezone.utc)
    assert c.notifications.mark_seen(up_to) == 2
    body = json.loads(responses.calls[0].request.body)
    assert body == {"upTo": "2026-07-18T10:00:00.123456+00:00"}


@responses.activate
def test_mark_read_ids():
    responses.add(
        responses.POST, f"{BASE}/me/notifications/read", json={"unseen": 1}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    assert c.notifications.mark_read([ID1, ID2]) == 1
    body = json.loads(responses.calls[0].request.body)
    assert body == {"ids": [ID1, ID2]}


@responses.activate
def test_mark_read_card_id():
    responses.add(
        responses.POST, f"{BASE}/me/notifications/read", json={"unseen": 0}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    assert c.notifications.mark_read(card_id=CARD) == 0
    body = json.loads(responses.calls[0].request.body)
    assert body == {"cardId": CARD}


@responses.activate
def test_mark_read_both():
    responses.add(
        responses.POST, f"{BASE}/me/notifications/read", json={"unseen": 0}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    c.notifications.mark_read([ID1], card_id=CARD)
    body = json.loads(responses.calls[0].request.body)
    assert body == {"ids": [ID1], "cardId": CARD}


def test_mark_read_requires_ids_or_card_id():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError):
        c.notifications.mark_read()
    with pytest.raises(ValueError):
        c.notifications.mark_read([])
    with pytest.raises(ValueError):
        c.notifications.mark_read(card_id="")


def test_mark_read_max_ids():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError):
        c.notifications.mark_read([ID1] * 201)


@responses.activate
def test_mark_read_200_ids_allowed():
    responses.add(
        responses.POST, f"{BASE}/me/notifications/read", json={"unseen": 0}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    c.notifications.mark_read([ID1] * 200)
    body = json.loads(responses.calls[0].request.body)
    assert len(body["ids"]) == 200


@responses.activate
def test_mark_read_400_bad_uuid():
    responses.add(
        responses.POST,
        f"{BASE}/me/notifications/read",
        json={"error": "ids must be UUIDs"},
        status=400,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError):
        c.notifications.mark_read(["not-a-uuid"])


@responses.activate
def test_read_all():
    responses.add(
        responses.POST, f"{BASE}/me/notifications/read-all", json={"unseen": 0}, status=200
    )
    c = CraaftClient(api_key="cra_x")
    assert c.notifications.read_all() == 0
    assert responses.calls[0].request.method == "POST"
    assert not responses.calls[0].request.body

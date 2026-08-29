import responses

from craaft import CraaftClient

BASE = "https://craaft.io/api/v1"


def _board():
    return {
        "project": {
            "id": "p1",
            "name": "Roadmap",
            "description": "Public plan",
            "backgroundImage": "",
            "backgroundColor": "#101820",
            "colorScheme": "midnight",
            "textColor": "light",
            "updatedAt": "2026-05-08T10:00:00Z",
        },
        "columns": [
            {"key": "todo", "title": "To Do", "color": "", "position": 1.0},
            {
                "key": "done",
                "title": "Done",
                "color": "green",
                "position": 2.0,
                "isDone": True,
            },
        ],
        "cards": [
            {
                "id": "c1",
                "column": "todo",
                "position": 1.0,
                "title": "Ship it",
                "priority": "high",
                "assignedUserName": "Ava",
            }
        ],
    }


@responses.activate
def test_public_board_maps_the_trimmed_projection():
    responses.add(responses.GET, f"{BASE}/public/projects/tok123", json=_board())
    c = CraaftClient(api_key="cra_x")
    board = c.public.board("tok123")
    assert board.project.name == "Roadmap"
    assert board.project.text_color == "light"
    assert [col.key for col in board.columns] == ["todo", "done"]
    assert board.columns[1].is_done is True
    assert board.cards[0].priority == "high"
    assert board.cards[0].assigned_user_name == "Ava"


@responses.activate
def test_public_board_defaults_missing_optionals():
    payload = _board()
    payload["project"] = {
        "id": "p1",
        "name": "Bare",
        "updatedAt": "2026-05-08T10:00:00Z",
    }
    payload["cards"] = []
    responses.add(responses.GET, f"{BASE}/public/projects/tok123", json=payload)
    c = CraaftClient(api_key="cra_x")
    board = c.public.board("tok123")
    assert board.project.description is None
    assert board.project.color_scheme is None
    assert board.cards == []


@responses.activate
def test_public_board_escapes_the_token():
    responses.add(responses.GET, f"{BASE}/public/projects/a%2Fb", json=_board())
    c = CraaftClient(api_key="cra_x")
    c.public.board("a/b")
    assert "/public/projects/a%2Fb" in responses.calls[0].request.url


@responses.activate
def test_public_board_background_returns_bytes():
    responses.add(
        responses.GET,
        f"{BASE}/public/projects/tok123/background-image",
        body=b"\x89PNG\r\n",
        content_type="image/png",
    )
    c = CraaftClient(api_key="cra_x")
    assert c.public.board_background("tok123") == b"\x89PNG\r\n"


@responses.activate
def test_avatar_returns_bytes():
    responses.add(
        responses.GET,
        f"{BASE}/users/u1/avatar",
        body=b"\xff\xd8\xff",
        content_type="image/jpeg",
    )
    c = CraaftClient(api_key="cra_x")
    assert c.public.avatar("u1") == b"\xff\xd8\xff"


@responses.activate
def test_version_returns_the_payload():
    responses.add(responses.GET, f"{BASE}/version", json={"version": "1.2.3"})
    c = CraaftClient(api_key="cra_x")
    assert c.version() == {"version": "1.2.3"}

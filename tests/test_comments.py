import json

import responses

from craaft import CraaftClient

BASE = "https://craaft.io/api/v1"


def _comment():
    return {
        "id": "cm1",
        "cardId": "card1",
        "authorId": "u1",
        "body": "edited",
        "createdAt": "2026-05-08T10:00:00Z",
        "updatedAt": "2026-05-08T11:00:00Z",
    }


@responses.activate
def test_update():
    responses.add(responses.PATCH, f"{BASE}/comments/cm1", json=_comment(), status=200)
    c = CraaftClient(api_key="cra_x")
    cm = c.comments.update("cm1", body="edited")
    assert cm.body == "edited"
    sent = json.loads(responses.calls[0].request.body)
    assert sent == {"body": "edited"}


@responses.activate
def test_delete():
    responses.add(responses.DELETE, f"{BASE}/comments/cm1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.comments.delete("cm1") is None

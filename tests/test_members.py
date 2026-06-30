import json

import responses

from craaft import CraaftClient

BASE = "https://craaft.io/api/v1"


@responses.activate
def test_list_members():
    payload = [
        {
            "userId": "u1",
            "email": "a@b.co",
            "name": "Alice",
            "role": "owner",
            "avatarUrl": "",
            "joinedAt": "2026-05-08T10:00:00Z",
        }
    ]
    responses.add(responses.GET, f"{BASE}/members", json=payload, status=200)
    c = CraaftClient(api_key="cra_x")
    members = c.members.list()
    assert members[0].user_id == "u1"
    assert members[0].role == "owner"


@responses.activate
def test_create_invitation_with_board_grants():
    payload = {
        "id": "inv1",
        "email": "new@b.co",
        "role": "member",
        "invitedBy": "u1",
        "invitedByName": "Alice",
        "createdAt": "2026-05-08T10:00:00Z",
        "expiresAt": "2026-06-08T10:00:00Z",
        "boardGrants": [{"projectId": "p1", "name": "Demo", "role": "contributor"}],
    }
    responses.add(responses.POST, f"{BASE}/invitations", json=payload, status=201)
    c = CraaftClient(api_key="cra_x")
    inv = c.members.create_invitation(
        email="new@b.co",
        role="member",
        board_grants=[("p1", "contributor")],
    )
    assert inv.email == "new@b.co"
    body = json.loads(responses.calls[0].request.body)
    assert body["boardGrants"] == [{"projectId": "p1", "role": "contributor"}]

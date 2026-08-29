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


@responses.activate
def test_update_role_patches_the_workspace_role():
    payload = {
        "userId": "u2",
        "email": "b@c.co",
        "name": "Bob",
        "role": "admin",
        "avatarUrl": "",
        "joinedAt": "2026-05-08T10:00:00Z",
    }
    responses.add(responses.PATCH, f"{BASE}/members/u2", json=payload, status=200)
    c = CraaftClient(api_key="cra_x")
    member = c.members.update_role("u2", role="admin")
    assert member.role == "admin"
    assert json.loads(responses.calls[0].request.body) == {"role": "admin"}


@responses.activate
def test_remove_member_deletes():
    responses.add(responses.DELETE, f"{BASE}/members/u2", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.members.remove("u2") is None
    assert responses.calls[0].request.method == "DELETE"


@responses.activate
def test_revoke_invitation_deletes():
    responses.add(responses.DELETE, f"{BASE}/invitations/inv1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.members.revoke_invitation("inv1") is None


@responses.activate
def test_member_ids_are_escaped():
    responses.add(responses.DELETE, f"{BASE}/members/..%2Fadmin", status=204)
    c = CraaftClient(api_key="cra_x")
    c.members.remove("../admin")
    assert "/members/..%2Fadmin" in responses.calls[0].request.url

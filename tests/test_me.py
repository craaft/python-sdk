import responses

from craaft import CraaftClient

BASE = "https://craaft.io/api/v1"


def _user_payload():
    return {
        "id": "u1",
        "email": "a@b.co",
        "name": "Alice",
        "username": "alice",
        "avatarUrl": None,
        "hasPassword": True,
    }


@responses.activate
def test_me_get():
    responses.add(responses.GET, f"{BASE}/me", json=_user_payload(), status=200)
    c = CraaftClient(api_key="cra_x")
    user = c.me.get()
    assert user.id == "u1"
    assert user.email == "a@b.co"


@responses.activate
def test_me_update_sends_only_provided_fields():
    responses.add(responses.PATCH, f"{BASE}/me", json=_user_payload(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.me.update(name="Alice")
    body = responses.calls[0].request.body
    assert b'"name": "Alice"' in body
    assert b"email" not in body
    assert b"username" not in body


@responses.activate
def test_me_update_all_fields():
    responses.add(responses.PATCH, f"{BASE}/me", json=_user_payload(), status=200)
    c = CraaftClient(api_key="cra_x")
    c.me.update(name="Alice", email="a@b.co", username="alice")
    body = responses.calls[0].request.body
    assert b'"name": "Alice"' in body
    assert b'"email": "a@b.co"' in body
    assert b'"username": "alice"' in body


@responses.activate
def test_me_update_returns_user():
    responses.add(responses.PATCH, f"{BASE}/me", json=_user_payload(), status=200)
    c = CraaftClient(api_key="cra_x")
    u = c.me.update(name="Alice")
    assert u.id == "u1"

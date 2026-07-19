import json

import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import CraaftPermissionError, NotFoundError

BASE = "https://craaft.io/api/v1"


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
def test_update_translates_fields():
    from datetime import date

    responses.add(
        responses.PATCH,
        f"{BASE}/milestones/m1",
        json=_milestone({"name": "GA", "dueOn": "2026-10-01"}),
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    m = c.milestones.update("m1", name="GA", due_on=date(2026, 10, 1))
    assert m.name == "GA"
    assert str(m.due_on) == "2026-10-01"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "GA", "dueOn": "2026-10-01"}


@responses.activate
def test_update_achieved_true_stamps_achieved_at():
    responses.add(
        responses.PATCH,
        f"{BASE}/milestones/m1",
        json=_milestone({"achievedAt": "2026-07-18T10:00:00Z"}),
        status=200,
    )
    c = CraaftClient(api_key="cra_x")
    m = c.milestones.update("m1", achieved=True)
    assert m.achieved_at is not None
    body = json.loads(responses.calls[0].request.body)
    assert body == {"achieved": True}


@responses.activate
def test_update_achieved_false_clears_achieved_at():
    responses.add(
        responses.PATCH, f"{BASE}/milestones/m1", json=_milestone(), status=200
    )
    c = CraaftClient(api_key="cra_x")
    m = c.milestones.update("m1", achieved=False)
    assert m.achieved_at is None
    body = json.loads(responses.calls[0].request.body)
    assert body == {"achieved": False}


@responses.activate
def test_update_omits_unspecified():
    responses.add(
        responses.PATCH, f"{BASE}/milestones/m1", json=_milestone(), status=200
    )
    c = CraaftClient(api_key="cra_x")
    c.milestones.update("m1", name="GA")
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "GA"}


@responses.activate
def test_update_403_for_non_admin():
    responses.add(
        responses.PATCH,
        f"{BASE}/milestones/m1",
        json={"error": "board admin required"},
        status=403,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(CraaftPermissionError):
        c.milestones.update("m1", achieved=True)


@responses.activate
def test_delete():
    responses.add(responses.DELETE, f"{BASE}/milestones/m1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.milestones.delete("m1") is None


@responses.activate
def test_delete_404():
    responses.add(
        responses.DELETE, f"{BASE}/milestones/missing", json={"error": "nope"}, status=404
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(NotFoundError):
        c.milestones.delete("missing")

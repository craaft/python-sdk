import pytest
import responses

from craaft import CraaftClient
from craaft.exceptions import NotFoundError, PlanLimitError, ValidationError

BASE = "https://craaft.io/api/v1"


def _att():
    return {
        "id": "att1",
        "cardId": "card1",
        "name": "screenshot.png",
        "size": 1234,
        "contentType": "image/png",
        "uploadedBy": "u1",
        "uploadedByName": "Alice",
        "createdAt": "2026-05-08T10:00:00Z",
    }


@responses.activate
def test_list_for_card():
    responses.add(
        responses.GET, f"{BASE}/cards/card1/attachments", json=[_att()], status=200
    )
    c = CraaftClient(api_key="cra_x")
    rows = c.attachments.list_for_card("card1")
    assert rows[0].name == "screenshot.png"
    assert rows[0].size == 1234


@responses.activate
def test_upload_bytes():
    responses.add(
        responses.POST, f"{BASE}/cards/card1/attachments", json=_att(), status=201
    )
    c = CraaftClient(api_key="cra_x")
    att = c.attachments.upload("card1", file=b"png-bytes", filename="screenshot.png")
    assert att.id == "att1"
    req = responses.calls[0].request
    assert req.headers.get("Content-Type", "").startswith("multipart/form-data")
    assert b"screenshot.png" in req.body


@responses.activate
def test_upload_402_raises_plan_limit():
    responses.add(
        responses.POST,
        f"{BASE}/cards/card1/attachments",
        json={"error": "uploads are a paid feature", "limit": "attachments"},
        status=402,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(PlanLimitError):
        c.attachments.upload("card1", file=b"x", filename="a.txt")


@responses.activate
def test_upload_empty_raises_value_error():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError, match="empty"):
        c.attachments.upload("card1", file=b"", filename="a.txt")


def test_upload_too_large_raises_value_error():
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValueError, match="25 MiB"):
        c.attachments.upload("card1", file=b"x" * (25 * 1024 * 1024 + 1))


@responses.activate
def test_download_returns_bytes():
    responses.add(
        responses.GET,
        f"{BASE}/attachments/att1",
        body=b"file-bytes",
        status=200,
        content_type="image/png",
    )
    c = CraaftClient(api_key="cra_x")
    data = c.attachments.download("att1")
    assert data == b"file-bytes"


@responses.activate
def test_download_404_raises_not_found():
    responses.add(responses.GET, f"{BASE}/attachments/missing", status=404)
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(NotFoundError):
        c.attachments.download("missing")


@responses.activate
def test_delete():
    responses.add(responses.DELETE, f"{BASE}/attachments/att1", status=204)
    c = CraaftClient(api_key="cra_x")
    assert c.attachments.delete("att1") is None


@responses.activate
def test_upload_413_raises_validation():
    responses.add(
        responses.POST,
        f"{BASE}/cards/card1/attachments",
        json={"error": "file exceeds 25 MiB limit"},
        status=413,
    )
    c = CraaftClient(api_key="cra_x")
    with pytest.raises(ValidationError):
        c.attachments.upload("card1", file=b"x", filename="big.bin")

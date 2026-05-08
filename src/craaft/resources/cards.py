from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from craaft.models import Card, CardSummary, Comment
from craaft.resources._base import BaseResource


def _serialize_dt(value: datetime | str | None) -> str | None:
    """Serialize a datetime for the API. Naive datetimes are assumed UTC."""
    if value is None or isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class CardsResource(BaseResource):
    """Endpoints under ``/cards`` (and ``/search``, since it returns cards)."""

    def update(
        self,
        card_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        column: str | None = None,
        position: float | None = None,
        due_date: datetime | str | None = None,
        assigned_user_id: str | None = None,
        size: Literal["xs", "s", "m", "l", "xl"] | None = None,
        priority: Literal["low", "normal", "high", "urgent"] | None = None,
    ) -> Card:
        body: dict[str, object] = {}
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if column is not None:
            body["column"] = column
        if position is not None:
            body["position"] = position
        if due_date is not None:
            body["dueDate"] = _serialize_dt(due_date)
        if assigned_user_id is not None:
            body["assignedUserId"] = assigned_user_id
        if size is not None:
            body["size"] = size
        if priority is not None:
            body["priority"] = priority
        data = self._transport.request("PATCH", f"/cards/{card_id}", json=body)
        return Card.from_api(data)

    def delete(self, card_id: str) -> None:
        self._transport.request("DELETE", f"/cards/{card_id}")

    def upcoming(self) -> list[CardSummary]:
        data = self._transport.request("GET", "/cards/upcoming")
        return [CardSummary.from_api(c) for c in data]

    def search(self, *, q: str, limit: int = 20) -> list[CardSummary]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        data = self._transport.request("GET", "/search", params={"q": q, "limit": limit})
        return [CardSummary.from_api(c) for c in data.get("cards", [])]

    def list_comments(self, card_id: str) -> list[Comment]:
        data = self._transport.request("GET", f"/cards/{card_id}/comments")
        return [Comment.from_api(c) for c in data]

    def add_comment(self, card_id: str, *, body: str) -> Comment:
        data = self._transport.request(
            "POST", f"/cards/{card_id}/comments", json={"body": body}
        )
        return Comment.from_api(data)

from __future__ import annotations

from builtins import list as _list
from datetime import datetime

from craaft.models import (
    AttentionCard,
    Card,
    CardEvent,
    CardSummary,
    Comment,
    FocusResponse,
    HygieneType,
    Priority,
)
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg, serialize_dt


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
        size: int | None = None,
        priority: Priority | None = None,
        tags: list[str] | None = None,
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
            body["dueDate"] = serialize_dt(due_date)
        if assigned_user_id is not None:
            body["assignedUserId"] = assigned_user_id
        if size is not None:
            body["size"] = size
        if priority is not None:
            body["priority"] = priority
        if tags is not None:
            body["tags"] = tags
        data = self._transport.request("PATCH", f"/cards/{id_seg(card_id)}", json=body)
        return Card.from_api(data)

    def delete(self, card_id: str) -> None:
        self._transport.request("DELETE", f"/cards/{id_seg(card_id)}")

    def move(
        self, card_id: str, *, target_project_id: str, column: str
    ) -> Card:
        data = self._transport.request(
            "POST",
            f"/cards/{id_seg(card_id)}/move",
            json={"targetProjectId": target_project_id, "column": column},
        )
        return Card.from_api(data)

    def upcoming(self) -> _list[CardSummary]:
        data = self._transport.request("GET", "/cards/upcoming")
        return [CardSummary.from_api(c) for c in data]

    def focus(self) -> FocusResponse:
        data = self._transport.request("GET", "/cards/focus")
        return FocusResponse.from_api(data)

    def hygiene(self, *, type: HygieneType) -> _list[AttentionCard]:
        data = self._transport.request(
            "GET", "/cards/hygiene", params={"type": type}
        )
        return [AttentionCard.from_api(c) for c in data]

    def list_events(self, card_id: str) -> _list[CardEvent]:
        data = self._transport.request("GET", f"/cards/{id_seg(card_id)}/events")
        return [CardEvent.from_api(e) for e in data]

    def search(self, *, q: str, limit: int = 20) -> _list[CardSummary]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        data = self._transport.request("GET", "/search", params={"q": q, "limit": limit})
        return [CardSummary.from_api(c) for c in data.get("cards", [])]

    def list_comments(self, card_id: str) -> _list[Comment]:
        data = self._transport.request("GET", f"/cards/{id_seg(card_id)}/comments")
        return [Comment.from_api(c) for c in data]

    def add_comment(self, card_id: str, *, body: str) -> Comment:
        data = self._transport.request(
            "POST", f"/cards/{id_seg(card_id)}/comments", json={"body": body}
        )
        return Comment.from_api(data)

"""Dataclass models mirroring the Craaft API resource schemas.

Each class has a ``from_api`` classmethod that maps the camelCase JSON
payload into snake_case Python attributes, parses ISO 8601 timestamps,
and tolerates extra unknown keys (forward-compat with new server fields).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


def _parse_dt(value: str) -> datetime:
    # datetime.fromisoformat accepts the trailing "Z" only on Python 3.11+.
    # Normalize for 3.10 compatibility.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _parse_dt_optional(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _parse_dt(value)


Size = Literal["xs", "s", "m", "l", "xl"]
Priority = Literal["low", "normal", "high", "urgent"]
TextColor = Literal["dark", "light"]


@dataclass(frozen=True, slots=True, kw_only=True)
class User:
    id: str
    email: str
    name: str
    username: str
    avatar_url: str | None
    has_password: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> User:
        return cls(
            id=data["id"],
            email=data["email"],
            name=data["name"],
            username=data["username"],
            avatar_url=data.get("avatarUrl"),
            has_password=bool(data.get("hasPassword", False)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Column:
    id: str
    key: str
    title: str
    color: str
    position: float
    is_done: bool
    card_limit: int | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Column:
        return cls(
            id=data["id"],
            key=data["key"],
            title=data["title"],
            color=data["color"],
            position=float(data["position"]),
            is_done=bool(data["isDone"]),
            card_limit=data.get("cardLimit"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Card:
    id: str
    project_id: str
    column: str
    title: str
    position: float
    description: str | None
    due_date: datetime | None
    assigned_user_id: str | None
    size: Size | None
    priority: Priority | None
    created_by: str | None
    attachment_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Card:
        return cls(
            id=data["id"],
            project_id=data["projectId"],
            column=data["column"],
            title=data["title"],
            position=float(data["position"]),
            description=data.get("description"),
            due_date=_parse_dt_optional(data.get("dueDate")),
            # Server returns assignedUserId; the older spec used assigneeId.
            # Accept both for forward/backward compat.
            assigned_user_id=data.get("assignedUserId") or data.get("assigneeId"),
            size=data.get("size"),
            priority=data.get("priority"),
            created_by=data.get("createdBy"),
            attachment_count=int(data.get("attachmentCount", 0)),
            created_at=_parse_dt(data["createdAt"]),
            updated_at=_parse_dt(data["updatedAt"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CardSummary:
    """Lightweight card preview returned by ``/cards/upcoming`` and ``/search``.

    These endpoints denormalize the project and column names and omit
    most card fields. Use :class:`Card` when you need the full record.
    """

    id: str
    project_id: str
    project_name: str
    column_key: str
    column_title: str
    title: str
    description: str | None = None
    due_date: datetime | None = None
    assigned_user_id: str | None = None
    priority: Priority | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CardSummary:
        return cls(
            id=data["id"],
            project_id=data["projectId"],
            project_name=data.get("projectName", ""),
            column_key=data["columnKey"],
            column_title=data.get("columnTitle", ""),
            title=data["title"],
            description=data.get("description"),
            due_date=_parse_dt_optional(data.get("dueDate")),
            assigned_user_id=data.get("assignedUserId") or data.get("assigneeId"),
            priority=data.get("priority"),
            updated_at=_parse_dt_optional(data.get("updatedAt")),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Comment:
    id: str
    card_id: str
    author_id: str
    body: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Comment:
        return cls(
            id=data["id"],
            card_id=data["cardId"],
            author_id=data["authorId"],
            body=data["body"],
            created_at=_parse_dt(data["createdAt"]),
            updated_at=_parse_dt(data["updatedAt"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Project:
    id: str
    workspace_id: str
    name: str
    description: str | None
    is_favorite: bool
    public_token: str | None
    custom_css: str | None
    background_image: str | None
    color_scheme: str | None
    text_color: TextColor
    total_cards: int
    column_counts: dict[str, int]
    columns: list[Column]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Project:
        cols_raw = data.get("columns") or []
        return cls(
            id=data["id"],
            workspace_id=data["workspaceId"],
            name=data["name"],
            description=data.get("description"),
            is_favorite=bool(data.get("isFavorite", False)),
            public_token=data.get("publicToken"),
            custom_css=data.get("customCss"),
            background_image=data.get("backgroundImage"),
            color_scheme=data.get("colorScheme"),
            text_color=data.get("textColor", "light"),
            total_cards=int(data.get("totalCards", 0)),
            column_counts=dict(data.get("columnCounts") or {}),
            columns=[Column.from_api(c) for c in cols_raw],
            created_at=_parse_dt(data["createdAt"]),
            updated_at=_parse_dt(data["updatedAt"]),
        )

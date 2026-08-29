"""Dataclass models mirroring the Craaft API resource schemas.

Each class has a ``from_api`` classmethod that maps the camelCase JSON
payload into snake_case Python attributes, parses ISO 8601 timestamps,
and tolerates extra unknown keys (forward-compat with new server fields).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _parse_dt_optional(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _parse_dt(value)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


Priority = Literal["low", "medium", "high", "urgent"]
TextColor = Literal["dark", "light"]
WorkspaceRole = Literal["owner", "admin", "member"]
BoardRole = Literal["admin", "contributor"]
Visibility = Literal["private", "workspace"]
BoardMemberSource = Literal["explicit", "workspace-admin", "workspace-visible"]
HygieneType = Literal["ghosts", "stuck", "mine_no_date"]
CardEventType = Literal["moved", "priority", "assignee"]


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
            avatar_url=data.get("avatarUrl") or None,
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
            color=data.get("color", ""),
            position=float(data["position"]),
            is_done=bool(data.get("isDone", False)),
            card_limit=data.get("cardLimit"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectMemberPreview:
    id: str
    name: str
    avatar_url: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectMemberPreview:
        return cls(
            id=data["id"],
            name=data["name"],
            avatar_url=data.get("avatarUrl", ""),
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
    assigned_user_name: str | None
    size: int | None
    priority: Priority | None
    created_by: str | None
    created_by_name: str | None
    updated_by: str | None
    updated_by_name: str | None
    attachment_count: int
    checklist_done: int
    checklist_total: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    # Whether the authenticated caller follows this card. Scoped to the
    # token's user, so it differs per caller for the same card.
    following: bool = False

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Card:
        raw_tags = data.get("tags")
        tags = list(raw_tags) if raw_tags is not None else []
        return cls(
            id=data["id"],
            project_id=data["projectId"],
            column=data["column"],
            title=data["title"],
            position=float(data["position"]),
            description=data.get("description"),
            due_date=_parse_dt_optional(data.get("dueDate")),
            assigned_user_id=data.get("assignedUserId") or data.get("assigneeId"),
            assigned_user_name=data.get("assignedUserName"),
            size=data.get("size"),
            priority=data.get("priority"),
            created_by=data.get("createdBy"),
            created_by_name=data.get("createdByName"),
            updated_by=data.get("updatedBy"),
            updated_by_name=data.get("updatedByName"),
            attachment_count=int(data.get("attachmentCount", 0)),
            checklist_done=int(data.get("checklistDone", 0)),
            checklist_total=int(data.get("checklistTotal", 0)),
            tags=tags,
            created_at=_parse_dt(data["createdAt"]),
            updated_at=_parse_dt(data["updatedAt"]),
            following=bool(data.get("following", False)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CardSummary:
    """Lightweight card preview returned by ``/cards/upcoming`` and ``/search``."""

    id: str
    project_id: str
    project_name: str
    column_key: str
    column_title: str
    title: str
    description: str | None = None
    due_date: datetime | None = None
    assigned_user_id: str | None = None
    assigned_user_name: str | None = None
    priority: Priority | None = None
    updated_at: datetime | None = None
    archived: bool = False

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CardSummary:
        return cls(
            id=data["id"],
            project_id=data["projectId"],
            project_name=data.get("projectName", ""),
            column_key=data.get("columnKey", data.get("column", "")),
            column_title=data.get("columnTitle", ""),
            title=data["title"],
            description=data.get("description"),
            due_date=_parse_dt_optional(data.get("dueDate")),
            assigned_user_id=data.get("assignedUserId") or data.get("assigneeId"),
            assigned_user_name=data.get("assignedUserName"),
            priority=data.get("priority"),
            updated_at=_parse_dt_optional(data.get("updatedAt")),
            archived=bool(data.get("archived", False)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AttentionCard:
    id: str
    project_id: str
    project_name: str
    column_key: str
    column_title: str
    title: str
    updated_at: datetime
    assigned_user_id: str | None
    assigned_user_name: str | None
    priority: Priority | None
    stale_in_progress: bool
    high_priority: bool
    idle_by_me: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AttentionCard:
        return cls(
            id=data["id"],
            project_id=data["projectId"],
            project_name=data.get("projectName", ""),
            column_key=data.get("columnKey", ""),
            column_title=data.get("columnTitle", ""),
            title=data["title"],
            updated_at=_parse_dt(data["updatedAt"]),
            assigned_user_id=data.get("assignedUserId"),
            assigned_user_name=data.get("assignedUserName"),
            priority=data.get("priority"),
            stale_in_progress=bool(data.get("staleInProgress", False)),
            high_priority=bool(data.get("highPriority", False)),
            idle_by_me=bool(data.get("idleByMe", False)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class HygieneCounts:
    ghosts: int
    long_in_progress: int
    mine_no_date: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> HygieneCounts:
        return cls(
            ghosts=int(data.get("ghosts", 0)),
            long_in_progress=int(data.get("longInProgress", 0)),
            mine_no_date=int(data.get("mineNoDate", 0)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusResponse:
    due: list[CardSummary]
    attention: list[AttentionCard]
    hygiene: HygieneCounts

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> FocusResponse:
        return cls(
            due=[CardSummary.from_api(c) for c in data.get("due", [])],
            attention=[AttentionCard.from_api(c) for c in data.get("attention", [])],
            hygiene=HygieneCounts.from_api(data.get("hygiene", {})),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CardEvent:
    id: str
    type: CardEventType
    created_at: datetime
    from_value: str | None = None
    to_value: str | None = None
    from_name: str | None = None
    to_name: str | None = None
    actor_id: str | None = None
    actor_name: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CardEvent:
        return cls(
            id=data["id"],
            type=data["type"],
            created_at=_parse_dt(data["createdAt"]),
            from_value=data.get("fromValue"),
            to_value=data.get("toValue"),
            from_name=data.get("fromName"),
            to_name=data.get("toName"),
            actor_id=data.get("actorId"),
            actor_name=data.get("actorName"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Attachment:
    id: str
    card_id: str
    name: str
    size: int
    content_type: str
    uploaded_by: str
    uploaded_by_name: str
    created_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Attachment:
        return cls(
            id=data["id"],
            card_id=data["cardId"],
            name=data["name"],
            size=int(data["size"]),
            content_type=data["contentType"],
            uploaded_by=data["uploadedBy"],
            uploaded_by_name=data.get("uploadedByName", ""),
            created_at=_parse_dt(data["createdAt"]),
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
            updated_at=_parse_dt(data.get("updatedAt", data["createdAt"])),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ChecklistItem:
    id: str
    card_id: str
    text: str
    done: bool
    position: float
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ChecklistItem:
        return cls(
            id=data["id"],
            card_id=data["cardId"],
            text=data["text"],
            done=bool(data.get("done", False)),
            position=float(data["position"]),
            created_at=_parse_dt(data["createdAt"]),
            updated_at=_parse_dt(data["updatedAt"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Milestone:
    id: str
    project_id: str
    name: str
    due_on: date
    achieved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Milestone:
        return cls(
            id=data["id"],
            project_id=data["projectId"],
            name=data["name"],
            due_on=_parse_date(data["dueOn"]),
            achieved_at=_parse_dt_optional(data.get("achievedAt")),
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
    background_image: str | None
    background_color: str | None
    color_scheme: str | None
    text_color: TextColor
    my_role: WorkspaceRole | None
    visibility: Visibility | None
    my_board_role: BoardRole | None
    can_upload_attachments: bool
    workspace_name: str | None
    total_cards: int
    column_counts: dict[str, int]
    columns: list[Column]
    members: list[ProjectMemberPreview]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Project:
        cols_raw = data.get("columns") or []
        members_raw = data.get("members") or []
        return cls(
            id=data["id"],
            workspace_id=data["workspaceId"],
            name=data["name"],
            description=data.get("description"),
            is_favorite=bool(data.get("isFavorite", False)),
            public_token=data.get("publicToken") or None,
            background_image=data.get("backgroundImage") or None,
            background_color=data.get("backgroundColor") or None,
            color_scheme=data.get("colorScheme") or None,
            text_color=data.get("textColor", "light"),
            my_role=data.get("myRole"),
            visibility=data.get("visibility"),
            my_board_role=data.get("myBoardRole"),
            can_upload_attachments=bool(data.get("canUploadAttachments", False)),
            workspace_name=data.get("workspaceName"),
            total_cards=int(data.get("totalCards", 0)),
            column_counts=dict(data.get("columnCounts") or {}),
            columns=[Column.from_api(c) for c in cols_raw],
            members=[ProjectMemberPreview.from_api(m) for m in members_raw],
            created_at=_parse_dt(data["createdAt"]),
            updated_at=_parse_dt(data["updatedAt"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class BoardMemberGrant:
    user_id: str
    role: BoardRole
    created_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BoardMemberGrant:
        return cls(
            user_id=data["userId"],
            role=data["role"],
            created_at=_parse_dt(data["createdAt"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class BoardMember:
    user_id: str
    name: str
    email: str
    username: str
    avatar_url: str
    role: BoardRole
    source: BoardMemberSource
    created_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BoardMember:
        return cls(
            user_id=data["userId"],
            name=data["name"],
            email=data["email"],
            username=data.get("username", ""),
            avatar_url=data.get("avatarUrl", ""),
            role=data["role"],
            source=data["source"],
            created_at=_parse_dt(data["createdAt"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class BoardAccess:
    project_id: str
    name: str
    role: BoardRole

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BoardAccess:
        return cls(
            project_id=data["projectId"],
            name=data["name"],
            role=data["role"],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceMember:
    user_id: str
    email: str
    name: str
    role: WorkspaceRole
    avatar_url: str
    joined_at: datetime
    board_access: list[BoardAccess] | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> WorkspaceMember:
        ba_raw = data.get("boardAccess")
        board_access = None
        if ba_raw is not None:
            board_access = [BoardAccess.from_api(b) for b in ba_raw]
        return cls(
            user_id=data["userId"],
            email=data["email"],
            name=data["name"],
            role=data["role"],
            avatar_url=data.get("avatarUrl", ""),
            joined_at=_parse_dt(data["joinedAt"]),
            board_access=board_access,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class InvitationGrant:
    project_id: str
    name: str
    role: BoardRole

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> InvitationGrant:
        return cls(
            project_id=data["projectId"],
            name=data["name"],
            role=data["role"],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Invitation:
    id: str
    email: str
    role: Literal["admin", "member"]
    invited_by: str
    invited_by_name: str
    created_at: datetime
    expires_at: datetime
    board_grants: list[InvitationGrant]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Invitation:
        return cls(
            id=data["id"],
            email=data["email"],
            role=data["role"],
            invited_by=data["invitedBy"],
            invited_by_name=data.get("invitedByName", ""),
            created_at=_parse_dt(data["createdAt"]),
            expires_at=_parse_dt(data["expiresAt"]),
            board_grants=[InvitationGrant.from_api(g) for g in data.get("boardGrants", [])],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExportUser:
    username: str
    name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectExportUser:
        return cls(username=data["username"], name=data["name"])


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExportComment:
    author: ProjectExportUser
    body: str
    created_at: datetime

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectExportComment:
        return cls(
            author=ProjectExportUser.from_api(data["author"]),
            body=data["body"],
            created_at=_parse_dt(data["createdAt"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExportAttachment:
    filename: str
    size: int
    uploaded_at: datetime
    uploader: ProjectExportUser | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectExportAttachment:
        uploader_raw = data.get("uploader")
        return cls(
            filename=data["filename"],
            size=int(data["size"]),
            uploaded_at=_parse_dt(data["uploadedAt"]),
            uploader=ProjectExportUser.from_api(uploader_raw) if uploader_raw else None,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExportCard:
    id: str
    title: str
    column_key: str
    position: float
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    due_date: datetime | None = None
    priority: str | None = None
    size: int | None = None
    assignee: ProjectExportUser | None = None
    created_by: ProjectExportUser | None = None
    comments: list[ProjectExportComment] = field(default_factory=list)
    attachments: list[ProjectExportAttachment] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectExportCard:
        assignee_raw = data.get("assignee")
        created_by_raw = data.get("createdBy")
        return cls(
            id=data["id"],
            title=data["title"],
            column_key=data["columnKey"],
            position=float(data["position"]),
            created_at=_parse_dt(data["createdAt"]),
            updated_at=_parse_dt(data["updatedAt"]),
            description=data.get("description"),
            due_date=_parse_dt_optional(data.get("dueDate")),
            priority=data.get("priority"),
            size=data.get("size"),
            assignee=ProjectExportUser.from_api(assignee_raw) if assignee_raw else None,
            created_by=ProjectExportUser.from_api(created_by_raw) if created_by_raw else None,
            comments=[ProjectExportComment.from_api(c) for c in data.get("comments", [])],
            attachments=[ProjectExportAttachment.from_api(a) for a in data.get("attachments", [])],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExportColumn:
    key: str
    name: str
    position: float
    color: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectExportColumn:
        return cls(
            key=data["key"],
            name=data["name"],
            position=float(data["position"]),
            color=data.get("color") or None,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExportProject:
    id: str
    name: str
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    description: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectExportProject:
        return cls(
            id=data["id"],
            name=data["name"],
            is_favorite=bool(data.get("isFavorite", False)),
            created_at=_parse_dt(data["createdAt"]),
            updated_at=_parse_dt(data["updatedAt"]),
            description=data.get("description"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExport:
    version: int
    exported_at: datetime
    project: ProjectExportProject
    columns: list[ProjectExportColumn]
    cards: list[ProjectExportCard]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectExport:
        return cls(
            version=int(data["version"]),
            exported_at=_parse_dt(data["exportedAt"]),
            project=ProjectExportProject.from_api(data["project"]),
            columns=[ProjectExportColumn.from_api(c) for c in data.get("columns", [])],
            cards=[ProjectExportCard.from_api(c) for c in data.get("cards", [])],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicBoardProject:
    """The project half of a public share snapshot.

    Deliberately thinner than :class:`Project` - the public endpoint omits
    workspace, ownership and membership fields.
    """

    id: str
    name: str
    updated_at: datetime
    description: str | None = None
    background_image: str | None = None
    background_color: str | None = None
    color_scheme: str | None = None
    text_color: TextColor | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PublicBoardProject:
        return cls(
            id=data["id"],
            name=data["name"],
            updated_at=_parse_dt(data["updatedAt"]),
            description=data.get("description"),
            background_image=data.get("backgroundImage") or None,
            background_color=data.get("backgroundColor") or None,
            color_scheme=data.get("colorScheme") or None,
            text_color=data.get("textColor") or None,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicBoardColumn:
    key: str
    title: str
    position: float
    color: str | None = None
    is_done: bool = False

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PublicBoardColumn:
        return cls(
            key=data["key"],
            title=data["title"],
            position=float(data["position"]),
            color=data.get("color") or None,
            is_done=bool(data.get("isDone", False)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicBoardCard:
    """A card as it appears on a public board.

    Carries no due date, size, tags, checklist or attachment counts - the
    public projection stops at priority and assignee.
    """

    id: str
    column: str
    position: float
    title: str
    description: str | None = None
    priority: Priority | None = None
    assigned_user_id: str | None = None
    assigned_user_name: str | None = None
    assigned_user_avatar_url: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PublicBoardCard:
        return cls(
            id=data["id"],
            column=data["column"],
            position=float(data["position"]),
            title=data["title"],
            description=data.get("description"),
            priority=data.get("priority"),
            assigned_user_id=data.get("assignedUserId"),
            assigned_user_name=data.get("assignedUserName"),
            assigned_user_avatar_url=data.get("assignedUserAvatarUrl") or None,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicBoard:
    project: PublicBoardProject
    columns: list[PublicBoardColumn]
    cards: list[PublicBoardCard]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PublicBoard:
        return cls(
            project=PublicBoardProject.from_api(data["project"]),
            columns=[PublicBoardColumn.from_api(c) for c in data.get("columns", [])],
            cards=[PublicBoardCard.from_api(c) for c in data.get("cards", [])],
        )

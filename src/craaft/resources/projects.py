from __future__ import annotations

from builtins import list as _list
from datetime import date
from io import BytesIO
from os import PathLike
from typing import Any, BinaryIO, Literal

from craaft.models import (
    BoardMember,
    BoardMemberGrant,
    BoardRole,
    BoardTemplate,
    Card,
    Column,
    Milestone,
    Project,
    ProjectExport,
    Visibility,
)
from craaft.resources._base import BaseResource
from craaft.resources._utils import (
    id_seg,
    prepare_bulk_cards,
    resolve_upload,
    serialize_date,
)

# Server cap for board backgrounds in internal/projects - lower than the
# 25 MiB attachment cap because a background is decoded on every board load.
_MAX_BACKGROUND_BYTES = 10 * 1024 * 1024
_MAX_BACKGROUND_DOWNLOAD_BYTES = _MAX_BACKGROUND_BYTES + (1 << 20)
# The server both checks the declared type against this set AND sniffs the
# leading bytes, so a renamed file is rejected rather than stored.
_BACKGROUND_CONTENT_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/webp", "image/gif"}
)


class ProjectsResource(BaseResource):
    """Endpoints under ``/projects``."""

    def list(self) -> _list[Project]:
        data = self._transport.request("GET", "/projects")
        return [Project.from_api(p) for p in data]

    def get(self, project_id: str) -> Project:
        data = self._transport.request("GET", f"/projects/{id_seg(project_id)}")
        return Project.from_api(data)

    def list_templates(self) -> _list[BoardTemplate]:
        """List the fixed catalogue of board templates.

        Any authenticated user may read this, no plan gate. Pass a
        template's ``key`` as ``template=`` to :meth:`create` to seed a new
        board with its column layout instead of the default Kanban three.
        """
        data = self._transport.request("GET", "/board-templates")
        return [BoardTemplate.from_api(t) for t in data]

    def create(
        self, *, name: str, description: str | None = None, template: str | None = None
    ) -> Project:
        """Create a project under the caller's personal workspace.

        ``template`` is a key from :meth:`list_templates`; omit it (or pass
        an empty string) for the default Kanban layout. An unrecognised key
        raises :class:`~craaft.exceptions.ValidationError` (400).
        """
        body: dict[str, object] = {"name": name}
        if description is not None:
            body["description"] = description
        if template is not None:
            body["template"] = template
        data = self._transport.request("POST", "/projects", json=body)
        return Project.from_api(data)

    def update(
        self,
        project_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        is_favorite: bool | None = None,
        background_image: str | None = None,
        background_color: str | None = None,
        color_scheme: str | None = None,
        text_color: Literal["dark", "light"] | None = None,
        visibility: Visibility | None = None,
    ) -> Project:
        body: dict[str, object] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if is_favorite is not None:
            body["isFavorite"] = is_favorite
        if background_image is not None:
            body["backgroundImage"] = background_image
        if background_color is not None:
            body["backgroundColor"] = background_color
        if color_scheme is not None:
            body["colorScheme"] = color_scheme
        if text_color is not None:
            body["textColor"] = text_color
        if visibility is not None:
            body["visibility"] = visibility
        data = self._transport.request(
            "PATCH", f"/projects/{id_seg(project_id)}", json=body
        )
        return Project.from_api(data)

    def delete(self, project_id: str) -> None:
        self._transport.request("DELETE", f"/projects/{id_seg(project_id)}")

    def export(self, project_id: str) -> ProjectExport:
        """Export the board as structured JSON."""
        data = self._transport.request(
            "GET",
            f"/projects/{id_seg(project_id)}/export",
            params={"format": "json"},
        )
        return ProjectExport.from_api(data)

    def export_csv(self, project_id: str) -> bytes:
        """Export the board as CSV bytes.

        The CSV is the flat card list only - it can't carry the nested
        columns, comments and attachment metadata that :meth:`export`
        returns, so prefer JSON unless a spreadsheet is the destination.
        """
        data = self._transport.request(
            "GET",
            f"/projects/{id_seg(project_id)}/export",
            params={"format": "csv"},
            parse_json=False,
        )
        assert isinstance(data, bytes)
        return data

    def list_tags(self, project_id: str) -> _list[str]:
        data = self._transport.request("GET", f"/projects/{id_seg(project_id)}/tags")
        return _list(data)

    def enable_share(self, project_id: str) -> str:
        data = self._transport.request("POST", f"/projects/{id_seg(project_id)}/share")
        return str(data["publicToken"])

    def disable_share(self, project_id: str) -> None:
        self._transport.request("DELETE", f"/projects/{id_seg(project_id)}/share")

    def list_cards(self, project_id: str) -> _list[Card]:
        data = self._transport.request(
            "GET", f"/projects/{id_seg(project_id)}/cards"
        )
        return [Card.from_api(c) for c in data]

    def list_archived_cards(self, project_id: str) -> _list[Card]:
        """List a board's archived cards, most recently archived first.

        Same board-list projection as :meth:`list_cards` (no description)
        plus ``archived_at``, capped at 200 rows - older archived cards stay
        reachable through :meth:`~craaft.resources.cards.CardsResource.search`.
        An inaccessible board reads as an empty list rather than a 404.
        """
        data = self._transport.request(
            "GET", f"/projects/{id_seg(project_id)}/cards/archived"
        )
        return [Card.from_api(c) for c in data]

    def create_card(
        self,
        project_id: str,
        *,
        title: str,
        column: str,
        position: float,
        description: str | None = None,
    ) -> Card:
        body: dict[str, object] = {
            "title": title,
            "column": column,
            "position": position,
        }
        if description is not None:
            body["description"] = description
        data = self._transport.request(
            "POST", f"/projects/{id_seg(project_id)}/cards", json=body
        )
        return Card.from_api(data)

    def bulk_create_cards(
        self, project_id: str, cards: _list[dict[str, Any]]
    ) -> _list[Card]:
        """Create up to 100 cards in one all-or-nothing transaction.

        Each item is a dict with the API's camelCase key names: ``title`` and
        ``column`` are required; ``description``, ``position`` (omit to append
        to the end of the column), ``dueDate``, ``assignedUserId``, ``size``,
        ``priority``, and ``tags`` are optional. ``datetime`` values under
        ``dueDate`` are serialized for you. Unlike :meth:`create_card`, the
        assignee is NOT defaulted to the caller. One invalid item fails the
        whole batch with a :class:`~craaft.exceptions.ValidationError` whose
        message names the offending index (``cards[3]: ...``). Bulk requests
        never send notification emails. Returns the created cards in request
        order.
        """
        body = {"cards": prepare_bulk_cards(cards)}
        data = self._transport.request(
            "POST", f"/projects/{id_seg(project_id)}/cards/bulk", json=body
        )
        return [Card.from_api(c) for c in data["cards"]]

    def rebalance_cards(
        self, project_id: str, ids: _list[str], *, column: str
    ) -> _list[Card]:
        """Renumber cards onto one column as positions 1, 2, 3, ... in order.

        This is board maintenance, not an import path: it exists for when
        repeated midpoint inserts have squeezed the gap between two
        neighbours down to nothing, so a drop has no representable position
        left. Every id must already be on this board (otherwise
        :class:`~craaft.exceptions.NotFoundError`), and the whole call is
        one all-or-nothing transaction that sends no notification emails.
        Sized for a real column - up to 10 000 ids. To create cards, use
        :meth:`bulk_create_cards`.
        """
        if not 1 <= len(ids) <= 10_000:
            raise ValueError("ids must contain between 1 and 10000 items")
        data = self._transport.request(
            "POST",
            f"/projects/{id_seg(project_id)}/cards/rebalance",
            json={"ids": _list(ids), "column": column},
        )
        return [Card.from_api(c) for c in data["cards"]]

    def upload_background(
        self,
        project_id: str,
        *,
        file: str | PathLike[str] | BinaryIO | bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> Project:
        """Set the board's background image. Board admins only.

        Accepts a path, bytes, or a binary file-like object, capped at
        10 MiB. The type must be PNG, JPEG, WebP or GIF, and the server
        additionally sniffs the leading bytes - a mislabelled file is
        rejected, not stored. Setting a background clears any
        ``background_color``; the two are mutually exclusive. Returns the
        updated project.
        """
        name, raw, ct = resolve_upload(
            file,
            filename=filename,
            content_type=content_type,
            max_bytes=_MAX_BACKGROUND_BYTES,
            limit_label="10 MiB",
            default_name="background",
        )
        if ct not in _BACKGROUND_CONTENT_TYPES:
            allowed = ", ".join(sorted(_BACKGROUND_CONTENT_TYPES))
            raise ValueError(
                f"background content type {ct!r} is not one of: {allowed}"
            )
        data = self._transport.request(
            "POST",
            f"/projects/{id_seg(project_id)}/background-image",
            files={"file": (name, BytesIO(raw), ct)},
        )
        return Project.from_api(data)

    def download_background(self, project_id: str) -> bytes:
        """Fetch the board background bytes.

        Raises :class:`~craaft.exceptions.NotFoundError` when the board has
        no background set, which is the same status you get for a board you
        can't reach.
        """
        data = self._transport.request(
            "GET",
            f"/projects/{id_seg(project_id)}/background-image",
            parse_json=False,
            max_response_bytes=_MAX_BACKGROUND_DOWNLOAD_BYTES,
        )
        assert isinstance(data, bytes)
        return data

    def delete_background(self, project_id: str) -> Project:
        """Remove the board background. Board admins only.

        Returns the updated project rather than 204, so the caller can see
        the cleared state without a re-fetch.
        """
        data = self._transport.request(
            "DELETE", f"/projects/{id_seg(project_id)}/background-image"
        )
        return Project.from_api(data)

    def list_milestones(self, project_id: str) -> _list[Milestone]:
        data = self._transport.request(
            "GET", f"/projects/{id_seg(project_id)}/milestones"
        )
        return [Milestone.from_api(m) for m in data]

    def add_milestone(
        self, project_id: str, *, name: str, due_on: date | str
    ) -> Milestone:
        """Add a milestone (board admins only - non-admin members get a 403).

        ``due_on`` is a plain calendar date (``YYYY-MM-DD``); a ``date``
        instance is serialized for you.
        """
        data = self._transport.request(
            "POST",
            f"/projects/{id_seg(project_id)}/milestones",
            json={"name": name, "dueOn": serialize_date(due_on)},
        )
        return Milestone.from_api(data)

    def add_column(self, project_id: str, *, title: str) -> Column:
        data = self._transport.request(
            "POST",
            f"/projects/{id_seg(project_id)}/columns",
            json={"title": title},
        )
        return Column.from_api(data)

    def list_members(self, project_id: str) -> _list[BoardMember]:
        data = self._transport.request(
            "GET", f"/projects/{id_seg(project_id)}/members"
        )
        return [BoardMember.from_api(m) for m in data]

    def add_member(
        self, project_id: str, *, user_id: str, role: BoardRole
    ) -> BoardMemberGrant:
        data = self._transport.request(
            "POST",
            f"/projects/{id_seg(project_id)}/members",
            json={"userId": user_id, "role": role},
        )
        return BoardMemberGrant.from_api(data)

    def update_member(
        self, project_id: str, user_id: str, *, role: BoardRole
    ) -> BoardMemberGrant:
        data = self._transport.request(
            "PATCH",
            f"/projects/{id_seg(project_id)}/members/{id_seg(user_id)}",
            json={"role": role},
        )
        return BoardMemberGrant.from_api(data)

    def remove_member(self, project_id: str, user_id: str) -> None:
        self._transport.request(
            "DELETE",
            f"/projects/{id_seg(project_id)}/members/{id_seg(user_id)}",
        )

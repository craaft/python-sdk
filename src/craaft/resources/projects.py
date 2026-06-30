from __future__ import annotations

from builtins import list as _list
from typing import Literal

from craaft.models import (
    BoardMember,
    BoardMemberGrant,
    BoardRole,
    Card,
    Column,
    Project,
    ProjectExport,
    Visibility,
)
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg


class ProjectsResource(BaseResource):
    """Endpoints under ``/projects``."""

    def list(self) -> _list[Project]:
        data = self._transport.request("GET", "/projects")
        return [Project.from_api(p) for p in data]

    def get(self, project_id: str) -> Project:
        data = self._transport.request("GET", f"/projects/{id_seg(project_id)}")
        return Project.from_api(data)

    def create(self, *, name: str, description: str | None = None) -> Project:
        body: dict[str, object] = {"name": name}
        if description is not None:
            body["description"] = description
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
        data = self._transport.request("GET", f"/projects/{id_seg(project_id)}/export")
        return ProjectExport.from_api(data)

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

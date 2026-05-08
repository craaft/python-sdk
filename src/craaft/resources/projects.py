from __future__ import annotations

from builtins import list as _list
from datetime import datetime
from typing import Literal

from craaft.models import Card, Column, Project
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg, serialize_dt


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
        custom_css: str | None = None,
        background_image: str | None = None,
        color_scheme: str | None = None,
        text_color: Literal["dark", "light"] | None = None,
    ) -> Project:
        body: dict[str, object] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if is_favorite is not None:
            body["isFavorite"] = is_favorite
        if custom_css is not None:
            body["customCss"] = custom_css
        if background_image is not None:
            body["backgroundImage"] = background_image
        if color_scheme is not None:
            body["colorScheme"] = color_scheme
        if text_color is not None:
            body["textColor"] = text_color
        data = self._transport.request(
            "PATCH", f"/projects/{id_seg(project_id)}", json=body
        )
        return Project.from_api(data)

    def delete(self, project_id: str) -> None:
        self._transport.request("DELETE", f"/projects/{id_seg(project_id)}")

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
        due_date: datetime | str | None = None,
        assigned_user_id: str | None = None,
        size: Literal["xs", "s", "m", "l", "xl"] | None = None,
        priority: Literal["low", "normal", "high", "urgent"] | None = None,
    ) -> Card:
        body: dict[str, object] = {
            "title": title,
            "column": column,
            "position": position,
        }
        if description is not None:
            body["description"] = description
        if due_date is not None:
            body["dueDate"] = serialize_dt(due_date)
        if assigned_user_id is not None:
            body["assignedUserId"] = assigned_user_id
        if size is not None:
            body["size"] = size
        if priority is not None:
            body["priority"] = priority
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

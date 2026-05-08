from __future__ import annotations

from craaft.models import Column
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg


class ColumnsResource(BaseResource):
    """Endpoints under ``/columns``."""

    def update(
        self,
        column_id: str,
        *,
        title: str | None = None,
        color: str | None = None,
        position: float | None = None,
        is_done: bool | None = None,
        card_limit: int | None = None,
    ) -> Column:
        body: dict[str, object] = {}
        if title is not None:
            body["title"] = title
        if color is not None:
            body["color"] = color
        if position is not None:
            body["position"] = position
        if is_done is not None:
            body["isDone"] = is_done
        if card_limit is not None:
            body["cardLimit"] = card_limit
        data = self._transport.request(
            "PATCH", f"/columns/{id_seg(column_id)}", json=body
        )
        return Column.from_api(data)

    def delete(self, column_id: str) -> None:
        self._transport.request("DELETE", f"/columns/{id_seg(column_id)}")

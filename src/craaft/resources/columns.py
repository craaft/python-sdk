from __future__ import annotations

from craaft.models import Column, ColumnArchiveResult
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

    def archive(self, column_id: str) -> int:
        """Archive every live card in a column, returning the count archived.

        Only takes effect on a column flagged ``is_done`` - any other column
        still answers with ``archived=0`` rather than an error, so check the
        count instead of relying on the status code. Use
        :meth:`archive_with_ids` instead of this method when you need the
        archived card ids, for example to offer an undo via
        :meth:`~craaft.resources.cards.CardsResource.restore`.
        """
        data = self._transport.request(
            "POST", f"/columns/{id_seg(column_id)}/archive"
        )
        return int(data["archived"])

    def archive_with_ids(self, column_id: str) -> ColumnArchiveResult:
        """Archive every live card in a column, same as :meth:`archive` but
        also returning the archived card ids.

        ``ids`` is useful for offering an undo via
        :meth:`~craaft.resources.cards.CardsResource.restore`. Same
        is-done-column caveat as :meth:`archive` applies.
        """
        data = self._transport.request(
            "POST", f"/columns/{id_seg(column_id)}/archive"
        )
        return ColumnArchiveResult.from_api(data)

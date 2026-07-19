from __future__ import annotations

from craaft.models import ChecklistItem
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg


class ChecklistResource(BaseResource):
    """Endpoints under ``/checklist``.

    Card-scoped listing and creation live on
    :meth:`~craaft.resources.cards.CardsResource.list_checklist` and
    :meth:`~craaft.resources.cards.CardsResource.add_checklist_item`.
    """

    def update(
        self,
        item_id: str,
        *,
        text: str | None = None,
        done: bool | None = None,
    ) -> ChecklistItem:
        body: dict[str, object] = {}
        if text is not None:
            body["text"] = text
        if done is not None:
            body["done"] = done
        data = self._transport.request(
            "PATCH", f"/checklist/{id_seg(item_id)}", json=body
        )
        return ChecklistItem.from_api(data)

    def delete(self, item_id: str) -> None:
        self._transport.request("DELETE", f"/checklist/{id_seg(item_id)}")

from __future__ import annotations

from datetime import date

from craaft.models import Milestone
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg, serialize_date


class MilestonesResource(BaseResource):
    """Endpoints under ``/milestones``.

    Project-scoped listing and creation live on
    :meth:`~craaft.resources.projects.ProjectsResource.list_milestones` and
    :meth:`~craaft.resources.projects.ProjectsResource.add_milestone`.
    Writes are board-admin only - non-admin members get a 403.
    """

    def update(
        self,
        milestone_id: str,
        *,
        name: str | None = None,
        due_on: date | str | None = None,
        achieved: bool | None = None,
    ) -> Milestone:
        """Partially update a milestone.

        Setting ``achieved=True`` stamps ``achieved_at`` once (re-sending
        ``True`` keeps the original stamp); ``achieved=False`` clears it.
        """
        body: dict[str, object] = {}
        if name is not None:
            body["name"] = name
        if due_on is not None:
            body["dueOn"] = serialize_date(due_on)
        if achieved is not None:
            body["achieved"] = achieved
        data = self._transport.request(
            "PATCH", f"/milestones/{id_seg(milestone_id)}", json=body
        )
        return Milestone.from_api(data)

    def delete(self, milestone_id: str) -> None:
        self._transport.request("DELETE", f"/milestones/{id_seg(milestone_id)}")

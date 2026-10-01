from __future__ import annotations

from craaft.models import InboundEmailAddress, InboundEmailStatus
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg


class InboundEmailResource(BaseResource):
    """Email-to-card endpoints, all under ``/projects/{id}/inbound-email``.

    Board admins on a Pro plan manage a board's intake address; get/enable/
    update all 402 on Free, but disable stays open so a downgraded board can
    still turn it off.
    """

    def get(self, project_id: str) -> InboundEmailStatus:
        """Fetch the board's inbound address, or ``enabled=False`` if none is set up."""
        data = self._transport.request(
            "GET", f"/projects/{id_seg(project_id)}/inbound-email"
        )
        return InboundEmailStatus.from_api(data)

    def enable(
        self,
        project_id: str,
        *,
        target_column: str | None = None,
        ai_enrich: bool | None = None,
    ) -> InboundEmailAddress:
        """Mint the board's inbound address.

        ``target_column`` is a column key; omit it to file inbound cards
        into the board's first column. Raises
        :class:`~craaft.exceptions.ConflictError` if the board already has
        an address - use :meth:`update` or :meth:`disable` instead.

        ``ai_enrich`` turns AI cards for email threads on or off. Turning it
        on returns a 409 when the server has no AI key.
        """
        body: dict[str, object] = {}
        if target_column is not None:
            body["targetColumn"] = target_column
        if ai_enrich is not None:
            body["aiEnrich"] = ai_enrich
        data = self._transport.request(
            "POST", f"/projects/{id_seg(project_id)}/inbound-email", json=body
        )
        return InboundEmailAddress.from_api(data)

    def update(
        self,
        project_id: str,
        *,
        active: bool | None = None,
        target_column: str | None = None,
        rotate: bool | None = None,
        ai_enrich: bool | None = None,
    ) -> InboundEmailAddress:
        """Partially update the board's inbound email configuration.

        ``target_column`` follows the server's three-state contract: leave
        it unset (``None``) to keep the current column, pass an empty
        string ``""`` to clear it back to the board's first column, or pass
        a column key to target that column. ``rotate=True`` mints a new
        token (and therefore a new email address) while keeping the rest of
        the configuration. ``ai_enrich`` turns AI cards for email threads on
        or off. Turning it on returns a 409 when the server has no AI key.
        """
        body: dict[str, object] = {}
        if active is not None:
            body["active"] = active
        if target_column is not None:
            body["targetColumn"] = target_column
        if rotate is not None:
            body["rotate"] = rotate
        if ai_enrich is not None:
            body["aiEnrich"] = ai_enrich
        data = self._transport.request(
            "PATCH", f"/projects/{id_seg(project_id)}/inbound-email", json=body
        )
        return InboundEmailAddress.from_api(data)

    def disable(self, project_id: str) -> None:
        """Disable inbound email for a board. Board admin only, not plan-gated."""
        self._transport.request(
            "DELETE", f"/projects/{id_seg(project_id)}/inbound-email"
        )

from __future__ import annotations

from builtins import list as _list
from collections.abc import Iterator
from datetime import datetime

from craaft.models import Notification, NotificationKind, NotificationPage
from craaft.resources._base import BaseResource
from craaft.resources._utils import serialize_dt

# Server cap on ids per mark-read request; mirrored client-side so an
# oversized batch fails fast without burning a request.
_MARK_READ_MAX_IDS = 200


class NotificationsResource(BaseResource):
    """The caller's notification inbox, under ``/me/notifications``.

    Every write returns the caller's new unseen count, so a badge can be
    updated without a follow-up :meth:`count` call.
    """

    def list(
        self,
        *,
        before: datetime | str | None = None,
        limit: int = 30,
        unread: bool = False,
        kind: NotificationKind | None = None,
    ) -> NotificationPage:
        """One page of the inbox, newest first.

        To page, pass the returned ``next_before`` back as ``before``, or
        use :meth:`iter_all`. A page can hold fewer than ``limit`` rows
        even when older ones exist, because rows are grouped after the
        limit is applied. ``limit`` must be between 1 and 50 inclusive.
        ``unread=True`` keeps only unread rows; ``kind`` keeps only one
        stored kind (``"group"`` is not a valid filter).
        """
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        params: dict[str, object] = {"limit": limit}
        if before is not None:
            params["before"] = serialize_dt(before)
        if unread:
            params["unread"] = "1"
        if kind is not None:
            params["kind"] = kind
        data = self._transport.request("GET", "/me/notifications", params=params)
        return NotificationPage.from_api(data)

    def iter_all(
        self,
        *,
        limit: int = 50,
        unread: bool = False,
        kind: NotificationKind | None = None,
    ) -> Iterator[Notification]:
        """Yield every row matching the filter, following ``next_before``
        until the server returns ``None``. ``limit`` is the page size."""
        before: str | None = None
        while True:
            page = self.list(before=before, limit=limit, unread=unread, kind=kind)
            yield from page.items
            if page.next_before is None:
                return
            before = page.next_before

    def count(self) -> int:
        """The caller's unseen notification count."""
        data = self._transport.request("GET", "/me/notifications/count")
        return int(data["unseen"])

    def mark_seen(self, up_to: datetime | str) -> int:
        """Mark every notification created at or before ``up_to`` as seen.

        Seen clears the badge; it is separate from read. Pass the newest
        row's ``created_at`` to clear everything the caller has been
        shown. A naive ``datetime`` is assumed UTC. Returns the new unseen
        count.
        """
        data = self._transport.request(
            "POST", "/me/notifications/seen", json={"upTo": serialize_dt(up_to)}
        )
        return int(data["unseen"])

    def mark_read(
        self,
        ids: _list[str] | None = None,
        *,
        card_id: str | None = None,
    ) -> int:
        """Mark notifications as read, by id, by card, or both.

        ``ids`` takes up to 200 notification ids (a row's ``ids``, so a
        group is marked in full). ``card_id`` marks every notification on
        that card. At least one is required. Returns the new unseen count.
        """
        if not ids and not card_id:
            raise ValueError("pass ids or card_id")
        if ids is not None and len(ids) > _MARK_READ_MAX_IDS:
            raise ValueError(f"ids must contain at most {_MARK_READ_MAX_IDS} items")
        body: dict[str, object] = {}
        if ids:
            body["ids"] = _list(ids)
        if card_id is not None:
            body["cardId"] = card_id
        data = self._transport.request("POST", "/me/notifications/read", json=body)
        return int(data["unseen"])

    def read_all(self) -> int:
        """Mark every notification as read. Returns the new unseen count."""
        data = self._transport.request("POST", "/me/notifications/read-all")
        return int(data["unseen"])

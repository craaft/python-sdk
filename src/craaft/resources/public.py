"""Endpoints that need no authentication.

These are reachable without a token at all. The SDK still sends the
client's bearer header (harmless - the server ignores it here), so the
same client instance works for both authenticated and public reads.
"""

from __future__ import annotations

from craaft.models import PublicBoard
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg

# Avatars and board backgrounds are both images; allow the larger of the
# two caps plus slack so a legitimate response is never truncated.
_MAX_IMAGE_BYTES = 10 * 1024 * 1024 + (1 << 20)


class PublicResource(BaseResource):
    """Unauthenticated reads: shared boards and avatars."""

    def board(self, token: str) -> PublicBoard:
        """Read a board that has public sharing enabled.

        The share token IS the access check. Revoking sharing, or
        re-enabling it (which mints a fresh token), invalidates old links
        immediately and this raises
        :class:`~craaft.exceptions.NotFoundError`. The snapshot is a
        trimmed projection: no workspace or ownership fields, and no card
        metadata beyond priority and assignee.
        """
        data = self._transport.request("GET", f"/public/projects/{id_seg(token)}")
        return PublicBoard.from_api(data)

    def board_background(self, token: str) -> bytes:
        """Fetch the background image bytes for a publicly shared board."""
        data = self._transport.request(
            "GET",
            f"/public/projects/{id_seg(token)}/background-image",
            parse_json=False,
            max_response_bytes=_MAX_IMAGE_BYTES,
        )
        assert isinstance(data, bytes)
        return data

    def avatar(self, user_id: str) -> bytes:
        """Fetch a user's uploaded avatar bytes.

        Raises :class:`~craaft.exceptions.NotFoundError` when the user has
        never uploaded one - the app renders a generated placeholder in
        that case, so callers should treat 404 as "use your own fallback"
        rather than as an error.
        """
        data = self._transport.request(
            "GET",
            f"/users/{id_seg(user_id)}/avatar",
            parse_json=False,
            max_response_bytes=_MAX_IMAGE_BYTES,
        )
        assert isinstance(data, bytes)
        return data

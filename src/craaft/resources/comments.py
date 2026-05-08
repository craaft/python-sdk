from __future__ import annotations

from craaft.models import Comment
from craaft.resources._base import BaseResource


class CommentsResource(BaseResource):
    """Endpoints under ``/comments``."""

    def update(self, comment_id: str, *, body: str) -> Comment:
        data = self._transport.request(
            "PATCH", f"/comments/{comment_id}", json={"body": body}
        )
        return Comment.from_api(data)

    def delete(self, comment_id: str) -> None:
        self._transport.request("DELETE", f"/comments/{comment_id}")

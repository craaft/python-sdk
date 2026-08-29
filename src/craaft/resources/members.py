from __future__ import annotations

from builtins import list as _list
from collections.abc import Sequence
from typing import Literal

from craaft.models import BoardRole, Invitation, WorkspaceMember
from craaft.resources._base import BaseResource
from craaft.resources._utils import id_seg


class MembersResource(BaseResource):
    """Workspace member and invitation endpoints."""

    def list(self) -> Sequence[WorkspaceMember]:
        data = self._transport.request("GET", "/members")
        return [WorkspaceMember.from_api(m) for m in data]

    def list_invitations(self) -> Sequence[Invitation]:
        data = self._transport.request("GET", "/invitations")
        return [Invitation.from_api(i) for i in data]

    def create_invitation(
        self,
        *,
        email: str,
        role: Literal["admin", "member"],
        board_grants: _list[tuple[str, BoardRole]] | None = None,
    ) -> Invitation:
        body: dict[str, object] = {"email": email, "role": role}
        if board_grants is not None:
            body["boardGrants"] = [
                {"projectId": project_id, "role": grant_role}
                for project_id, grant_role in board_grants
            ]
        data = self._transport.request("POST", "/invitations", json=body)
        return Invitation.from_api(data)

    def update_role(
        self, user_id: str, *, role: Literal["admin", "member"]
    ) -> WorkspaceMember:
        """Change a member's workspace role. Owner/admin only.

        Only ``admin`` and ``member`` are settable: ownership is a property
        of the workspace, not a role you can hand out, so the API rejects
        ``owner`` here. This is also the workspace-wide role, not a board
        grant - for per-board access use
        :meth:`ProjectsResource.update_member`.
        """
        if role not in ("admin", "member"):
            raise ValueError('role must be "admin" or "member"')
        data = self._transport.request(
            "PATCH", f"/members/{id_seg(user_id)}", json={"role": role}
        )
        return WorkspaceMember.from_api(data)

    def remove(self, user_id: str) -> None:
        """Remove a member from the workspace. Owner/admin only.

        Also closes any SSE streams that member has open, so their session
        stops receiving board updates immediately.
        """
        self._transport.request("DELETE", f"/members/{id_seg(user_id)}")

    def revoke_invitation(self, invitation_id: str) -> None:
        """Delete a pending invite so its accept link stops working.

        Owner/admin only. Has no effect on a member who already accepted -
        use :meth:`remove` for that.
        """
        self._transport.request("DELETE", f"/invitations/{id_seg(invitation_id)}")

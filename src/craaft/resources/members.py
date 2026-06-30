from __future__ import annotations

from builtins import list as _list
from collections.abc import Sequence
from typing import Literal

from craaft.models import BoardRole, Invitation, WorkspaceMember
from craaft.resources._base import BaseResource


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

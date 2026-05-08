from __future__ import annotations

from craaft.models import User
from craaft.resources._base import BaseResource


class MeResource(BaseResource):
    """Endpoints under ``/me``."""

    def get(self) -> User:
        data = self._transport.request("GET", "/me")
        return User.from_api(data)

    def update(
        self,
        *,
        name: str | None = None,
        email: str | None = None,
        username: str | None = None,
    ) -> User:
        body: dict[str, object] = {}
        if name is not None:
            body["name"] = name
        if email is not None:
            body["email"] = email
        if username is not None:
            body["username"] = username
        data = self._transport.request("PATCH", "/me", json=body)
        return User.from_api(data)

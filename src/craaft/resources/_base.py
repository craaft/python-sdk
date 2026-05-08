"""Shared base for resource sub-clients."""

from __future__ import annotations

from craaft._http import Transport


class BaseResource:
    """Holds the shared :class:`Transport` reference."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

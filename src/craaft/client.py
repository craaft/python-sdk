"""Top-level :class:`CraaftClient`.

Wires the HTTP transport, applies token resolution and defaults, and
exposes resource sub-clients as attributes.
"""

from __future__ import annotations

import os
from types import TracebackType

import requests

from craaft._http import RetryConfig, Transport
from craaft._version import __version__
from craaft.exceptions import CraaftError
from craaft.resources.cards import CardsResource
from craaft.resources.columns import ColumnsResource
from craaft.resources.comments import CommentsResource
from craaft.resources.me import MeResource
from craaft.resources.projects import ProjectsResource

DEFAULT_BASE_URL = "https://craaft.io/api/v1"
DEFAULT_TIMEOUT = 30.0
ENV_TOKEN = "CRAAFT_API_TOKEN"
ENV_BASE_URL = "CRAAFT_BASE_URL"

_DEFAULT_RETRY = RetryConfig()
_NO_RETRY = RetryConfig(max_attempts=1)


class CraaftClient:
    """Synchronous client for the Craaft API."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
        retry: RetryConfig | None = _DEFAULT_RETRY,
        user_agent: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        token = api_key or os.environ.get(ENV_TOKEN)
        if not token:
            raise CraaftError(
                "API key required: pass api_key=... or set the "
                f"{ENV_TOKEN} environment variable."
            )
        resolved_base_url = base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL
        ua = user_agent or f"craaft-python/{__version__}"
        retry_cfg = retry if retry is not None else _NO_RETRY
        self._transport = Transport(
            api_key=token,
            base_url=resolved_base_url,
            timeout=timeout,
            retry=retry_cfg,
            user_agent=ua,
            session=session if session is not None else requests.Session(),
        )

        self.me = MeResource(self._transport)
        self.projects = ProjectsResource(self._transport)
        self.cards = CardsResource(self._transport)
        self.comments = CommentsResource(self._transport)
        self.columns = ColumnsResource(self._transport)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> CraaftClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

"""Top-level :class:`CraaftClient`.

Wires the HTTP transport, applies token resolution and defaults, and
exposes resource sub-clients as attributes.
"""

from __future__ import annotations

import os
import re
from types import TracebackType
from typing import Any
from urllib.parse import urlparse

import requests

from craaft._http import RetryConfig, Transport
from craaft._version import __version__
from craaft.exceptions import CraaftError
from craaft.resources.attachments import AttachmentsResource
from craaft.resources.cards import CardsResource
from craaft.resources.checklist import ChecklistResource
from craaft.resources.columns import ColumnsResource
from craaft.resources.comments import CommentsResource
from craaft.resources.me import MeResource
from craaft.resources.members import MembersResource
from craaft.resources.milestones import MilestonesResource
from craaft.resources.projects import ProjectsResource

DEFAULT_BASE_URL = "https://craaft.io/api/v1"
DEFAULT_TIMEOUT = 30.0
ENV_TOKEN = "CRAAFT_API_TOKEN"
ENV_BASE_URL = "CRAAFT_BASE_URL"

# Hosts allowed to use plain http:// (development only). Anything else must
# be https:// to avoid leaking the bearer token.
_PLAINTEXT_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Token format documented as ``cra_<chars>``. Validated to catch obvious
# typos and stray whitespace before the first request goes out.
_TOKEN_RE = re.compile(r"\Acra_[A-Za-z0-9_\-]+\Z")

# Sentinel used to distinguish "retry kwarg omitted" from "retry=None passed".
_USE_DEFAULT_RETRY: Any = object()


def _resolve_base_url(base_url: str | None) -> str:
    resolved = base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL
    parsed = urlparse(resolved)
    if not parsed.hostname:
        raise CraaftError(f"base_url must include a hostname: {resolved!r}")
    if parsed.scheme == "https":
        return resolved
    if parsed.scheme == "http" and parsed.hostname in _PLAINTEXT_HOSTS:
        return resolved
    raise CraaftError(
        f"base_url must use https:// (got {parsed.scheme!r}). "
        "Plain http:// is only allowed for localhost during development."
    )


def _validate_token(token: str) -> str:
    stripped = token.strip()
    if not stripped:
        raise CraaftError("API key is empty.")
    if not _TOKEN_RE.match(stripped):
        raise CraaftError(
            "API key does not match the expected format `cra_<chars>`. "
            "Check for stray whitespace or a copy-paste error."
        )
    return stripped


def _validate_user_agent(user_agent: str) -> str:
    if any(ord(c) < 32 or ord(c) == 127 for c in user_agent):
        raise CraaftError("user_agent must not contain control characters.")
    return user_agent


class CraaftClient:
    """Synchronous client for the Craaft API.

    A single client instance is safe to use from multiple threads as long as
    the underlying ``requests.Session`` is not mutated and the server does
    not set cookies (Craaft does not). For strict isolation, create one
    client per thread.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
        retry: RetryConfig | None = _USE_DEFAULT_RETRY,
        user_agent: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        raw_token = api_key or os.environ.get(ENV_TOKEN)
        if not raw_token:
            raise CraaftError(
                "API key required: pass api_key=... or set the "
                f"{ENV_TOKEN} environment variable."
            )
        token = _validate_token(raw_token)
        resolved_base_url = _resolve_base_url(base_url)
        ua = _validate_user_agent(user_agent or f"craaft-python/{__version__}")

        if retry is _USE_DEFAULT_RETRY:
            retry_cfg = RetryConfig()
        elif retry is None:
            retry_cfg = RetryConfig(max_attempts=1)
        else:
            retry_cfg = retry

        if session is not None and getattr(session, "verify", True) is False:
            raise CraaftError(
                "session.verify must remain enabled; refusing to send "
                "bearer credentials over an unverified TLS connection."
            )

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
        self.attachments = AttachmentsResource(self._transport)
        self.comments = CommentsResource(self._transport)
        self.columns = ColumnsResource(self._transport)
        self.members = MembersResource(self._transport)
        self.checklist = ChecklistResource(self._transport)
        self.milestones = MilestonesResource(self._transport)

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

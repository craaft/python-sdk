"""HTTP transport for the Craaft client.

Single ``Transport`` class owns the ``requests.Session``, applies auth
headers, handles retries with backoff, and maps non-2xx responses to
typed exceptions defined in :mod:`craaft.exceptions`.
"""

from __future__ import annotations

import json as _json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from craaft import exceptions as exc

logger = logging.getLogger("craaft")

# Hard ceiling on Retry-After we will honor. A hostile or buggy server can
# otherwise pin a worker thread for arbitrary durations.
_MAX_RETRY_AFTER_SECONDS = 300.0

# Default cap on response body size when reading streaming responses.
_DEFAULT_MAX_RESPONSE_BYTES = 32 * 1024 * 1024

_STATUS_TO_EXC: dict[int, type[exc.CraaftAPIError]] = {
    400: exc.ValidationError,
    401: exc.AuthenticationError,
    402: exc.PlanLimitError,
    403: exc.CraaftPermissionError,
    404: exc.NotFoundError,
    409: exc.ConflictError,
    422: exc.ValidationError,
    429: exc.RateLimitError,
}


def _exc_for_status(status: int) -> type[exc.CraaftAPIError]:
    if status in _STATUS_TO_EXC:
        return _STATUS_TO_EXC[status]
    if 500 <= status < 600:
        return exc.ServerError
    return exc.CraaftAPIError


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for transient-failure retries.

    Frozen so default instances cannot be mutated by accident in long-running
    processes that share defaults across many clients.
    """

    max_attempts: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 30.0
    jitter: float = 0.25
    retry_writes_on_5xx: bool = False
    # Network failures (connection errors, timeouts) on writes can double-apply
    # the request - the server may have processed it before the connection
    # broke. Off by default; flip if your workload is safe to retry.
    retry_writes_on_network_error: bool = False
    retry_status: tuple[int, ...] = (429, 502, 503, 504)


_WRITE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})

# Control characters that should be stripped from server-supplied error
# messages to prevent log injection.
_CONTROL_CHARS = "".join(chr(c) for c in range(32) if chr(c) not in "\t")


def _scrub(text: str) -> str:
    """Strip control characters from server-supplied text before logging."""
    return text.translate({ord(c): None for c in _CONTROL_CHARS})


def _parse_message(body: bytes) -> str:
    if not body:
        return ""
    try:
        data = _json.loads(body)
    except (ValueError, _json.JSONDecodeError):
        return _scrub(body.decode("utf-8", errors="replace")[:200]).strip()
    if isinstance(data, dict):
        msg = data.get("error")
        if isinstance(msg, str):
            return _scrub(msg)
    return _scrub(body.decode("utf-8", errors="replace")[:200]).strip()


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        return min(max(0.0, seconds), _MAX_RETRY_AFTER_SECONDS)
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    # parsedate_to_datetime returns a naive datetime when the input has no
    # explicit timezone. Treat that as UTC rather than letting .timestamp()
    # interpret it in the host's local timezone.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt.timestamp() - time.time()
    return min(max(0.0, delta), _MAX_RETRY_AFTER_SECONDS)


def _raise_for_response(resp: requests.Response, body: bytes) -> None:
    request_id = resp.headers.get("x-request-id") or resp.headers.get("X-Request-Id")
    cls = _exc_for_status(resp.status_code)
    message = _parse_message(body)
    if not message:
        message = f"HTTP {resp.status_code}"
    if cls is exc.RateLimitError:
        retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
        raise exc.RateLimitError(
            status_code=resp.status_code,
            message=message,
            response_body=body,
            request_id=request_id,
            retry_after=retry_after,
        )
    raise cls(
        status_code=resp.status_code,
        message=message,
        response_body=body,
        request_id=request_id,
    )


def _read_body(resp: requests.Response, max_bytes: int) -> bytes:
    """Read the response body, refusing anything larger than ``max_bytes``."""
    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            resp.close()
            raise exc.CraaftError(
                f"response body exceeded maximum size of {max_bytes} bytes"
            )
        chunks.append(chunk)
    return b"".join(chunks)


@dataclass
class Transport:
    api_key: str = field(repr=False)
    base_url: str
    timeout: float | tuple[float, float]
    retry: RetryConfig
    user_agent: str
    session: requests.Session = field(default_factory=requests.Session, repr=False)
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES

    def __repr__(self) -> str:
        return (
            f"Transport(base_url={self.base_url!r}, "
            f"user_agent={self.user_agent!r}, "
            f"timeout={self.timeout!r})"
        )

    def __post_init__(self) -> None:
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            }
        )

    def close(self) -> None:
        self.session.close()

    def _backoff_seconds(self, attempt: int) -> float:
        base: float = min(self.retry.backoff_base * (2**attempt), self.retry.backoff_max)
        if self.retry.jitter > 0:
            jitter_amount = base * self.retry.jitter
            base = base + random.uniform(-jitter_amount, jitter_amount)
        return max(0.0, base)

    def _should_retry(
        self,
        method: str,
        attempt: int,
        status: int | None,
        exc_obj: BaseException | None,
    ) -> bool:
        if attempt + 1 >= self.retry.max_attempts:
            return False
        if exc_obj is not None:
            # Network errors on writes risk double-applying the change. Skip
            # the retry unless the caller has explicitly opted in.
            return not (
                method in _WRITE_METHODS
                and not self.retry.retry_writes_on_network_error
            )
        if status is None:
            return False
        if status not in self.retry.retry_status:
            return False
        return not (
            method in _WRITE_METHODS
            and 500 <= status < 600
            and not self.retry.retry_writes_on_5xx
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = self.base_url.rstrip("/") + path
        method = method.upper()
        attempts = max(1, self.retry.max_attempts)
        last_response: requests.Response | None = None
        last_response_body: bytes = b""
        last_exc: BaseException | None = None

        for attempt in range(attempts):
            start = time.monotonic()
            last_response = None
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    timeout=self.timeout,
                    # Don't follow redirects: cross-origin redirects could
                    # leak the bearer token, and the API doesn't redirect.
                    allow_redirects=False,
                    stream=True,
                )
            except requests.exceptions.SSLError as e:
                # TLS verification failures should never be retried - that
                # would just give a man-in-the-middle more chances.
                raise exc.CraaftConnectionError(str(e)) from e
            except requests.exceptions.Timeout as e:
                last_exc = e
                logger.debug(
                    "craaft request timeout method=%s path=%s attempt=%d",
                    method,
                    path,
                    attempt,
                )
                if not self._should_retry(method, attempt, None, e):
                    raise exc.CraaftTimeoutError(str(e)) from e
            except requests.exceptions.ConnectionError as e:
                last_exc = e
                logger.debug(
                    "craaft request conn-error method=%s path=%s attempt=%d",
                    method,
                    path,
                    attempt,
                )
                if not self._should_retry(method, attempt, None, e):
                    raise exc.CraaftConnectionError(str(e)) from e
            except requests.exceptions.RequestException as e:
                # Catch-all for ChunkedEncodingError, ContentDecodingError,
                # TooManyRedirects, etc. Treat as a connection-class failure.
                last_exc = e
                logger.debug(
                    "craaft request request-error method=%s path=%s attempt=%d type=%s",
                    method,
                    path,
                    attempt,
                    type(e).__name__,
                )
                if not self._should_retry(method, attempt, None, e):
                    raise exc.CraaftConnectionError(str(e)) from e
            else:
                try:
                    body = _read_body(resp, self.max_response_bytes)
                finally:
                    resp.close()
                last_response = resp
                last_response_body = body
                duration_ms = (time.monotonic() - start) * 1000
                logger.debug(
                    "craaft request method=%s path=%s status=%d duration_ms=%.1f attempt=%d",
                    method,
                    path,
                    resp.status_code,
                    duration_ms,
                    attempt,
                )
                if 200 <= resp.status_code < 300:
                    if resp.status_code == 204 or not body:
                        return None
                    try:
                        return _json.loads(body)
                    except (ValueError, _json.JSONDecodeError) as e:
                        raise exc.CraaftError(
                            f"server returned a 2xx response with non-JSON body: {e}"
                        ) from e
                if 300 <= resp.status_code < 400:
                    # Redirects shouldn't happen against the real API; surface
                    # them rather than silently following.
                    raise exc.CraaftError(
                        f"unexpected redirect: {resp.status_code} -> "
                        f"{resp.headers.get('Location')!r}"
                    )
                if not self._should_retry(method, attempt, resp.status_code, None):
                    _raise_for_response(resp, body)

            # Sleep before retry.
            if last_response is not None and last_response.status_code == 429:
                retry_after = _parse_retry_after(last_response.headers.get("Retry-After"))
                sleep_for = (
                    retry_after if retry_after is not None else self._backoff_seconds(attempt)
                )
            else:
                sleep_for = self._backoff_seconds(attempt)
            time.sleep(sleep_for)

        # Loop exited without returning - surface the last seen error. Falling
        # off the end with neither a response nor an exception isn't reachable
        # via _should_retry's logic, but we keep the assertion as a safety net.
        if last_response is not None:
            _raise_for_response(last_response, last_response_body)
        if last_exc is not None:
            if isinstance(last_exc, requests.exceptions.Timeout):
                raise exc.CraaftTimeoutError(str(last_exc)) from last_exc
            raise exc.CraaftConnectionError(str(last_exc)) from last_exc
        raise AssertionError(
            "Transport.request exited the retry loop with no response or exception"
        )

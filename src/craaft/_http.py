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
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from craaft import exceptions as exc

logger = logging.getLogger("craaft")

_STATUS_TO_EXC: dict[int, type[exc.CraaftAPIError]] = {
    400: exc.ValidationError,
    401: exc.AuthenticationError,
    402: exc.PlanLimitError,
    403: exc.PermissionError,
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


@dataclass
class RetryConfig:
    """Configuration for transient-failure retries."""

    max_attempts: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 30.0
    jitter: float = 0.25
    retry_writes_on_5xx: bool = False
    retry_status: tuple[int, ...] = (429, 502, 503, 504)


_WRITE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


def _parse_message(body: bytes) -> str:
    if not body:
        return ""
    try:
        data = _json.loads(body)
    except (ValueError, _json.JSONDecodeError):
        return body.decode("utf-8", errors="replace")[:200].strip()
    if isinstance(data, dict):
        msg = data.get("error")
        if isinstance(msg, str):
            return msg
    return body.decode("utf-8", errors="replace")[:200].strip()


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    delta = dt.timestamp() - time.time()
    return max(0.0, delta)


def _raise_for_response(resp: requests.Response) -> None:
    body = resp.content or b""
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


@dataclass
class Transport:
    api_key: str
    base_url: str
    timeout: float | tuple[float, float]
    retry: RetryConfig
    user_agent: str
    session: requests.Session = field(default_factory=requests.Session)

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
            return True  # connection / timeout errors always retry
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
                )
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
            else:
                last_response = resp
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
                    if resp.status_code == 204 or not resp.content:
                        return None
                    return resp.json()
                if not self._should_retry(method, attempt, resp.status_code, None):
                    _raise_for_response(resp)

            # Sleep before retry.
            if last_response is not None and last_response.status_code == 429:
                retry_after = _parse_retry_after(last_response.headers.get("Retry-After"))
                sleep_for = (
                    retry_after if retry_after is not None else self._backoff_seconds(attempt)
                )
            else:
                sleep_for = self._backoff_seconds(attempt)
            time.sleep(sleep_for)

        # Loop exited without returning - must surface the last seen error.
        if last_response is not None:
            _raise_for_response(last_response)
        if last_exc is not None:
            if isinstance(last_exc, requests.exceptions.Timeout):
                raise exc.CraaftTimeoutError(str(last_exc)) from last_exc
            raise exc.CraaftConnectionError(str(last_exc)) from last_exc
        raise exc.CraaftError("request failed without a response")

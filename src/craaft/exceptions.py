"""Exceptions raised by the Craaft client."""

from __future__ import annotations


class CraaftError(Exception):
    """Base class for all Craaft client exceptions."""


class CraaftAPIError(CraaftError):
    """An error response from the API."""

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        response_body: bytes,
        request_id: str | None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        self.request_id = request_id
        super().__init__(f"[{status_code}] {message}")


class AuthenticationError(CraaftAPIError):
    """401 Unauthorized."""


class PermissionError(CraaftAPIError):
    """403 Forbidden."""


class NotFoundError(CraaftAPIError):
    """404 Not Found."""


class ConflictError(CraaftAPIError):
    """409 Conflict."""


class PlanLimitError(CraaftAPIError):
    """402 Payment Required (plan limits)."""


class ValidationError(CraaftAPIError):
    """400 / 422 - request body or query parameters are invalid."""


class RateLimitError(CraaftAPIError):
    """429 Too Many Requests."""

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        response_body: bytes,
        request_id: str | None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            message=message,
            response_body=response_body,
            request_id=request_id,
        )
        self.retry_after = retry_after


class ServerError(CraaftAPIError):
    """5xx Server errors."""


class CraaftConnectionError(CraaftError):
    """Network failure (DNS, TLS, connection refused, broken pipe)."""


class CraaftTimeoutError(CraaftError):
    """Request timed out."""

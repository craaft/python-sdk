import pytest

from craaft.exceptions import (
    AuthenticationError,
    ConflictError,
    CraaftAPIError,
    CraaftConnectionError,
    CraaftError,
    CraaftTimeoutError,
    NotFoundError,
    PermissionError,
    PlanLimitError,
    RateLimitError,
    ServerError,
    ValidationError,
)


def test_base_hierarchy():
    assert issubclass(CraaftAPIError, CraaftError)
    assert issubclass(CraaftConnectionError, CraaftError)
    assert issubclass(CraaftTimeoutError, CraaftError)


@pytest.mark.parametrize(
    "cls",
    [
        AuthenticationError,
        PermissionError,
        NotFoundError,
        ConflictError,
        PlanLimitError,
        ValidationError,
        RateLimitError,
        ServerError,
    ],
)
def test_api_error_subclasses(cls):
    assert issubclass(cls, CraaftAPIError)


def test_api_error_carries_fields():
    err = CraaftAPIError(
        status_code=404,
        message="not found",
        response_body=b'{"error":"not found"}',
        request_id="req_123",
    )
    assert err.status_code == 404
    assert err.message == "not found"
    assert err.response_body == b'{"error":"not found"}'
    assert err.request_id == "req_123"
    assert "404" in str(err)
    assert "not found" in str(err)


def test_rate_limit_error_retry_after_default_none():
    err = RateLimitError(
        status_code=429,
        message="rate limited",
        response_body=b"",
        request_id=None,
    )
    assert err.retry_after is None


def test_rate_limit_error_retry_after_set():
    err = RateLimitError(
        status_code=429,
        message="rate limited",
        response_body=b"",
        request_id=None,
        retry_after=5.0,
    )
    assert err.retry_after == 5.0

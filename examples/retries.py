"""Configuring retry behavior.

The default `RetryConfig` retries 429 (honoring `Retry-After`), 502, 503,
504, and network/timeout errors with exponential backoff up to 3 attempts.
Write methods (POST/PATCH/DELETE) skip 5xx by default because the server
may have applied the change before responding.

You can tighten or loosen this per client, or disable it entirely.
"""

from __future__ import annotations

import time

from craaft import CraaftClient, RateLimitError, RetryConfig


def aggressive_client() -> CraaftClient:
    """Retry up to 5 times with a longer backoff."""
    return CraaftClient(
        retry=RetryConfig(
            max_attempts=5,
            backoff_base=1.0,
            backoff_max=60.0,
        )
    )


def write_retrying_client() -> CraaftClient:
    """Retry writes on 5xx too. Use this if your server is idempotent
    by request body or you've ruled out double-applies another way."""
    return CraaftClient(retry=RetryConfig(retry_writes_on_5xx=True))


def no_retries_client() -> CraaftClient:
    """No retries at all - surface every error immediately."""
    return CraaftClient(retry=None)


def manual_rate_limit_handling() -> None:
    """If you're driving the API hard and want to back off in your own
    code instead of letting the SDK retry, disable retries and use
    `RateLimitError.retry_after`.
    """
    client = CraaftClient(retry=None)
    while True:
        try:
            client.projects.list()
            break
        except RateLimitError as e:
            wait = e.retry_after or 1.0
            print(f"Rate limited. Sleeping {wait:.1f}s.")
            time.sleep(wait)


def main() -> None:
    with aggressive_client() as client:
        projects = client.projects.list()
        print(f"Listed {len(projects)} projects with aggressive retries.")


if __name__ == "__main__":
    main()

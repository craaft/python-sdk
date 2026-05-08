"""Configuring the client beyond the defaults.

Everything you can pass to `CraaftClient` and what it's good for. Useful
when you're integrating with an existing service that already has its own
HTTP setup, proxy rules, or logging conventions.
"""

from __future__ import annotations

import logging

import requests

from craaft import CraaftClient, RetryConfig


def with_custom_session() -> CraaftClient:
    """Inject a pre-configured `requests.Session`.

    Useful for a corporate proxy, a custom retry adapter, mTLS certs, or
    anything else you'd normally configure on a Session.
    """
    session = requests.Session()
    session.proxies.update({
        "https": "http://proxy.example.com:3128",
    })
    # session.verify = "/etc/ssl/certs/internal-ca.pem"
    return CraaftClient(session=session)


def with_named_user_agent() -> CraaftClient:
    """Set a User-Agent so server-side logs can tell your app apart from
    other consumers of the SDK."""
    return CraaftClient(user_agent="acme-sync-worker/2.4.1")


def with_separate_connect_and_read_timeouts() -> CraaftClient:
    """A short connect timeout and a longer read timeout is a sensible
    default when you want to fail fast on unreachable hosts but tolerate
    a slow response."""
    return CraaftClient(timeout=(3.0, 30.0))


def with_debug_logging() -> CraaftClient:
    """Turn on per-attempt logging.

    The `craaft` logger emits one DEBUG line per HTTP attempt with the
    method, path, status, duration, and attempt number. The Authorization
    header is never logged.
    """
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("craaft").setLevel(logging.DEBUG)
    return CraaftClient()


def main() -> None:
    with CraaftClient(
        timeout=(3.0, 30.0),
        user_agent="examples/advanced_client.py",
        retry=RetryConfig(max_attempts=4),
    ) as client:
        me = client.me.get()
        print(f"OK as {me.username}")


if __name__ == "__main__":
    main()

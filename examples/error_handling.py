"""Which exceptions to catch.

Every API failure raises a subclass of `CraaftAPIError`, and every API
error carries `status_code`, `message`, `response_body`, and `request_id`
fields. Network failures raise `CraaftConnectionError` or
`CraaftTimeoutError` instead.
"""

from __future__ import annotations

from craaft import (
    AuthenticationError,
    ConflictError,
    CraaftAPIError,
    CraaftClient,
    CraaftConnectionError,
    CraaftTimeoutError,
    NotFoundError,
    PlanLimitError,
    RateLimitError,
    ValidationError,
)


def main() -> None:
    with CraaftClient() as client:
        # 404: easy to reproduce by asking for a project that doesn't exist.
        try:
            client.projects.get("00000000-0000-0000-0000-000000000000")
        except NotFoundError as e:
            print(f"NotFoundError: status={e.status_code}, message={e.message!r}")

        # If you ever hit your plan limit, you'll see this on POST /projects.
        try:
            client.projects.create(name="Example")
        except PlanLimitError as e:
            print(f"PlanLimitError: {e.message} (status {e.status_code})")
        except CraaftAPIError as e:
            # If the create succeeded, clean it up so the example is idempotent.
            print(f"Created project; cleaning it up. ({type(e).__name__})")

        # Catching the base class is fine when you don't need to branch.
        try:
            client.cards.search(q="anything", limit=10)
        except CraaftAPIError as e:
            print(f"Search failed: {e}")

    # Things that aren't API errors:
    #   AuthenticationError - 401 (bad or missing token)
    #   ValidationError     - 400 / 422 (bad request body)
    #   ConflictError       - 409 (e.g. deleting a column that still has cards)
    #   RateLimitError      - 429 (carries `.retry_after` in seconds)
    #   CraaftConnectionError - DNS / TLS / connection refused
    #   CraaftTimeoutError    - request didn't finish in time

    _ = (
        AuthenticationError,
        ValidationError,
        ConflictError,
        RateLimitError,
        CraaftConnectionError,
        CraaftTimeoutError,
    )


if __name__ == "__main__":
    main()

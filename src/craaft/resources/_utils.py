"""Internal helpers shared by resource sub-clients."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

# Server-side cap on items per bulk request; mirrored client-side so an
# oversized batch fails fast without burning a request.
BULK_MAX_ITEMS = 100


def id_seg(value: str) -> str:
    """URL-encode a path segment so untrusted IDs cannot inject path or
    query characters.

    Empty strings are rejected because an empty segment usually indicates
    a programming error - a missing variable substitution - rather than a
    legitimate request.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("resource ID must be a non-empty string")
    return quote(value, safe="")


def serialize_dt(value: datetime | str | None) -> str | None:
    """Serialize a datetime for the API.

    The Craaft API requires ISO 8601 with a timezone offset for ``dueDate``.
    Strings pass through unchanged so callers can format them themselves.
    Naive ``datetime`` instances are assumed UTC.
    """
    if value is None or isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def serialize_date(value: date | str | None) -> str | None:
    """Serialize a plain calendar date for the API (``YYYY-MM-DD``).

    Milestones use timezone-less dates for ``dueOn``. Strings pass through
    unchanged so callers can format them themselves. A ``datetime`` is
    truncated to its date part.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat()


def prepare_bulk_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize the item list for a bulk card request.

    Items are passed through verbatim - keys use the API's camelCase field
    names, and a key present with value ``None`` is sent as JSON ``null``
    (which clears a nullable field on bulk update), while an absent key
    leaves the field alone. The one convenience applied: a ``datetime``
    under ``dueDate`` is serialized the same way single-card methods do.
    Returns shallow copies so caller dicts are never mutated.
    """
    if not 1 <= len(cards) <= BULK_MAX_ITEMS:
        raise ValueError(f"cards must contain between 1 and {BULK_MAX_ITEMS} items")
    prepared: list[dict[str, Any]] = []
    for item in cards:
        out = dict(item)
        if isinstance(out.get("dueDate"), datetime):
            out["dueDate"] = serialize_dt(out["dueDate"])
        prepared.append(out)
    return prepared

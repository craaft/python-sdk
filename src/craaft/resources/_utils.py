"""Internal helpers shared by resource sub-clients."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote


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

"""Exact UTC publication instants for SQLite text timestamps.

SQLite ``julianday()`` rounds to milliseconds and returns NULL for valid
values at the 9999-12-31 boundary. This owner converts stored ISO text to
integer microseconds since the Unix epoch so filters and ordering compare
exact instants (declared offsets applied; naive values read as UTC, matching
the previous julianday() semantics).
"""
from __future__ import annotations

from datetime import datetime, timedelta

_EPOCH = datetime(1970, 1, 1)
_ONE_US = timedelta(microseconds=1)
DAY_US = 86_400_000_000
SQL_FUNCTION = "lumenis_utc_us"


def utc_microseconds(parsed: datetime) -> int:
    """Integer UTC microseconds; never leaves datetime range at year 1/9999."""
    offset = parsed.utcoffset() or timedelta(0)
    return (parsed.replace(tzinfo=None) - _EPOCH) // _ONE_US - offset // _ONE_US


def stored_utc_microseconds(value):
    """Stored ISO text -> UTC microseconds, or None when absent/unparseable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00").replace("z", "+00:00"))
    except ValueError:
        return None
    return utc_microseconds(parsed)


def register_instant_function(conn) -> None:
    """Expose ``lumenis_utc_us(text)`` on this connection (idempotent)."""
    conn.create_function(SQL_FUNCTION, 1, stored_utc_microseconds, deterministic=True)

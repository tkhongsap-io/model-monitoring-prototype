"""Time-ordered IDs (uuid7, RFC 9562) for the rows of the batch MVP tables (S2-05).

The time part is the creation time in milliseconds, so the IDs sort by time. Prototype
tables keep their own IDs (S4-07 deletes them).
"""
from __future__ import annotations

import uuid

import uuid_utils


def new_id(at: float | None = None) -> str:
    """A uuid7 string. `at` (Unix seconds) sets the time part; default: now."""
    if at is None:
        return str(uuid_utils.uuid7())
    return str(uuid_utils.uuid7(nanoseconds=int(at * 1000) * 1_000_000))


def is_uuid7(value: str) -> bool:
    try:
        return uuid.UUID(value).version == 7
    except (ValueError, TypeError, AttributeError):
        return False

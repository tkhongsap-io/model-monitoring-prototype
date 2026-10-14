"""uuid7 IDs of the MVP tables (S2-05)."""
from __future__ import annotations

import uuid

from app import ids


def test_new_id_is_version_7():
    value = ids.new_id()
    parsed = uuid.UUID(value)
    assert parsed.version == 7 and parsed.variant == uuid.RFC_4122
    assert ids.is_uuid7(value)


def test_time_part_is_the_given_time():
    at = 1_760_000_000.123
    value = uuid.UUID(ids.new_id(at))
    millis = value.int >> 80
    assert millis == int(at * 1000)


def test_later_ids_sort_later():
    first, second = ids.new_id(1_760_000_000.0), ids.new_id(1_760_000_001.0)
    assert first < second
    made = [ids.new_id() for _ in range(50)]
    assert made == sorted(made)


def test_is_uuid7_rejects_other_values():
    assert not ids.is_uuid7(str(uuid.uuid5(uuid.NAMESPACE_URL, "x")))
    assert not ids.is_uuid7("not-a-uuid")
    assert not ids.is_uuid7("")

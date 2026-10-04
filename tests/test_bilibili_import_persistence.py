from __future__ import annotations

import database
from lumenis.system.collector.adapters.multi_platform_import import _to_note_payload
from lumenis.system.collector.adapters.platform_naming import to_canonical_record


def test_bilibili_native_unix_publication_survives_note_insert():
    # conftest points the app at a fresh copy of the explicit empty seed.
    database.init_db()
    raw = {
        "platform": "bilibili",
        "bvid": "BV1persistTime",
        "mid": "24680",
        "pubdate": 1789704000,
        "pubdate_ts": 1789704000,
        "title": "Source video",
        "description": "Source description",
        "url": "https://www.bilibili.com/video/BV1persistTime",
        "captured_at": "2026-10-02T00:00:00+00:00",
    }
    canonical = to_canonical_record(raw, "bilibili")
    payload = _to_note_payload(canonical, raw)

    with database.get_db() as con:
        row_id, inserted = database.insert_note(payload, connection=con)
        stored = con.execute(
            "SELECT note_id, publish_date, publish_datetime, captured_at FROM notes WHERE id=?",
            (row_id,),
        ).fetchone()

    assert inserted is True
    assert stored["note_id"] == "BV1persistTime"
    assert stored["publish_date"] == "2026-09-18T04:00:00+00:00"
    assert stored["publish_datetime"] == "2026-09-18T04:00:00+00:00"
    assert stored["captured_at"] == raw["captured_at"]
    assert raw["pubdate"] == raw["pubdate_ts"] == 1789704000

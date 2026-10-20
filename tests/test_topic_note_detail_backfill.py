from __future__ import annotations

import json
import sqlite3

import pytest

from topic_note_detail_backfill import extract_note_detail, update_note_detail


def _connection_with_note():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE topic_campaign_notes (
               note_id TEXT, campaign_key TEXT, topic TEXT,
               content TEXT, media_json TEXT, comments_json TEXT,
               evidence_quality TEXT, detail_captured_at TEXT
           )"""
    )
    conn.execute(
        """INSERT INTO topic_campaign_notes
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "note-1", "campaign-1", "topic-1", "preserved body",
            json.dumps([{"url": "https://image.example/old"}]),
            json.dumps([{"content": "preserved comment"}]),
            "full", "2026-10-01 12:00:00",
        ),
    )
    conn.commit()
    return conn


def _read_note(conn):
    row = conn.execute(
        """SELECT content, media_json, comments_json, evidence_quality, detail_captured_at
           FROM topic_campaign_notes WHERE note_id='note-1'"""
    ).fetchone()
    return dict(zip(
        ("content", "media_json", "comments_json", "evidence_quality", "detail_captured_at"),
        row,
    ))


def _detail(**changes):
    result = {
        "content": "new body",
        "media": [{"url": "https://image.example/new"}],
        "comments_detail": [{"content": "new comment"}],
        "detail_captured_at": "2026-10-20 02:30:00",
        "field_status": {
            "content": "AVAILABLE",
            "media": "AVAILABLE",
            "comments_detail": "AVAILABLE",
        },
        "field_errors": {},
    }
    result.update(changes)
    return result


def test_failed_navigation_returns_explicit_unknowns_without_overwriting_old_detail():
    class FailedPage:
        url = ""

        def goto(self, *_args, **_kwargs):
            raise TimeoutError("synthetic navigation failure")

        def evaluate(self, *_args, **_kwargs):
            raise AssertionError("no extraction should run after navigation fails")

    conn = _connection_with_note()
    before = _read_note(conn)
    detail = extract_note_detail(FailedPage(), "https://public.example/note-1")

    assert detail["field_status"] == {
        "content": "FAILED", "media": "FAILED", "comments_detail": "FAILED",
    }
    assert detail["field_errors"] == {"page": "TimeoutError"}
    assert update_note_detail(conn, "note-1", "campaign-1", "topic-1", detail) == (0, "failed")
    assert _read_note(conn) == before
    conn.close()


def test_partial_capture_merges_only_verified_fields_and_keeps_parent_evidence():
    conn = _connection_with_note()
    detail = _detail(
        content="",
        media=[{"url": "https://image.example/recovered"}],
        comments_detail=[],
        field_status={"content": "FAILED", "media": "AVAILABLE", "comments_detail": "EMPTY"},
        field_errors={"content": "TimeoutError"},
    )

    rowcount, outcome = update_note_detail(conn, "note-1", "campaign-1", "topic-1", detail)

    stored = _read_note(conn)
    assert rowcount == 1
    assert outcome == "partial"
    assert stored["content"] == "preserved body"
    assert json.loads(stored["media_json"]) == [{"url": "https://image.example/recovered"}]
    assert json.loads(stored["comments_json"]) == [{"content": "preserved comment"}]
    assert stored["evidence_quality"] == "full"
    assert stored["detail_captured_at"] == "2026-10-20 02:30:00"
    assert conn.in_transaction  # the caller still owns the transaction
    conn.close()


def test_successful_full_capture_updates_all_fields_and_recovers_after_failure():
    conn = _connection_with_note()
    failed = _detail(
        content="", media=[], comments_detail=[],
        field_status={"content": "FAILED", "media": "FAILED", "comments_detail": "FAILED"},
    )
    assert update_note_detail(conn, "note-1", "campaign-1", "topic-1", failed) == (0, "failed")

    recovered = _detail()
    assert update_note_detail(conn, "note-1", "campaign-1", "topic-1", recovered) == (1, "full")
    stored = _read_note(conn)
    assert stored["content"] == "new body"
    assert json.loads(stored["media_json"]) == recovered["media"]
    assert json.loads(stored["comments_json"]) == recovered["comments_detail"]
    assert stored["evidence_quality"] == "full"
    conn.close()


def test_new_valid_json_fields_replace_corrupt_legacy_values_and_recompute_quality():
    conn = _connection_with_note()
    conn.execute(
        """UPDATE topic_campaign_notes
           SET media_json='not-json', comments_json='{broken', evidence_quality='search_only'
           WHERE note_id='note-1'"""
    )
    detail = _detail()

    rowcount, outcome = update_note_detail(conn, "note-1", "campaign-1", "topic-1", detail)

    stored = _read_note(conn)
    assert (rowcount, outcome) == (1, "full")
    assert stored["content"] == detail["content"]
    assert json.loads(stored["media_json"]) == detail["media"]
    assert json.loads(stored["comments_json"]) == detail["comments_detail"]
    assert stored["evidence_quality"] == "full"
    conn.close()


def test_successful_empty_capture_is_distinct_and_never_deletes_saved_detail():
    conn = _connection_with_note()
    before = _read_note(conn)
    empty = _detail(
        content="", media=[], comments_detail=[],
        field_status={"content": "EMPTY", "media": "EMPTY", "comments_detail": "EMPTY"},
    )

    assert update_note_detail(conn, "note-1", "campaign-1", "topic-1", empty) == (0, "empty")
    assert _read_note(conn) == before
    conn.close()


def test_identical_successful_capture_is_not_reported_as_a_failure_or_rewritten():
    conn = _connection_with_note()
    before = _read_note(conn)
    same = _detail(
        content="preserved body",
        media=[{"url": "https://image.example/old"}],
        comments_detail=[{"content": "preserved comment"}],
    )

    assert update_note_detail(conn, "note-1", "campaign-1", "topic-1", same) == (0, "unchanged")
    assert _read_note(conn) == before
    conn.close()


def test_field_extraction_failure_is_reported_separately_from_successful_empty_and_data():
    class PartialPage:
        url = "https://public.example/note-1"

        def goto(self, *_args, **_kwargs):
            return None

        def wait_for_timeout(self, _duration):
            return None

        def evaluate(self, script):
            if "document.body" in script:
                return ""
            if "document.querySelector(s)" in script:
                raise TimeoutError("synthetic content read failure")
            if ".note-slider-img" in script:
                return [{"url": "https://image.example/available"}]
            if ".comment-item" in script:
                return []
            raise AssertionError("unexpected evaluation")

    detail = extract_note_detail(PartialPage(), "https://public.example/note-1")

    assert detail["content"] == ""
    assert detail["media"] == [{"url": "https://image.example/available"}]
    assert detail["comments_detail"] == []
    assert detail["field_status"] == {
        "content": "FAILED", "media": "AVAILABLE", "comments_detail": "EMPTY",
    }
    assert detail["field_errors"] == {"content": "TimeoutError"}


def test_verification_challenge_remains_a_terminal_rejection():
    class ChallengePage:
        url = ""

        def goto(self, *_args, **_kwargs):
            self.url = "https://public.example/captcha"

        def wait_for_timeout(self, _duration):
            return None

        def evaluate(self, _script):
            return "请完成验证"

    with pytest.raises(RuntimeError, match="DETAIL_CAPTCHA"):
        extract_note_detail(ChallengePage(), "https://public.example/note-1")

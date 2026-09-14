"""CTH secondary collection surface tests.

These tests exercise the product boundary with local fakes only.  They must
never start a browser, call a platform, or use the production database.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from platform_adapters.base import CollectionResult, CollectionStatus
from platform_adapters import secondary_collection as surface


def test_surface_has_exact_launch_allowlist(monkeypatch):
    monkeypatch.setattr(
        surface,
        "_adapter_health",
        lambda platform: {"status": "SUCCESS", "ready": True, "message": "ok", "metadata": {}},
    )
    monkeypatch.setattr(surface, "_last_run", lambda platform: None)

    result = surface.get_collection_surface()

    assert result["product"] == "LUMENIS"
    assert result["domain"] == "CTH"
    assert [item["platform"] for item in result["platforms"]] == [
        "douyin", "zhihu", "instagram"
    ]
    assert result["manual_only"] is True
    assert result["read_only"] is True
    assert result["external_write"] is False
    assert result["product_will_not_publish"] is True
    assert "xiaohongshu_cn" in result["paused_platforms"]
    assert "weibo" in result["paused_platforms"]
    assert "bilibili" not in [item["platform"] for item in result["platforms"]]


def test_surface_status_preserves_last_run_failure(monkeypatch):
    monkeypatch.setattr(
        surface,
        "_adapter_health",
        lambda platform: {"status": "SUCCESS", "ready": True, "message": "ok", "metadata": {}},
    )
    monkeypatch.setattr(
        surface,
        "_last_run",
        lambda platform: {
            "platform": platform,
            "state": "SESSION_EXPIRED",
            "fetched": 0,
            "accepted": 0,
            "rejected": 0,
            "error_recorded": True,
        } if platform == "instagram" else None,
    )

    result = surface.get_collection_surface()

    by_platform = {item["platform"]: item for item in result["platforms"]}
    assert by_platform["instagram"]["status"] == "SESSION_EXPIRED"
    assert by_platform["instagram"]["health"]["status"] == "SUCCESS"


def test_paused_weibo_is_not_collectable_from_product_surface():
    with pytest.raises(ValueError, match="微博"):
        surface.collect_search("weibo", "广州太古汇", operator="human")


def test_native_record_keeps_string_id_and_provenance():
    record = surface._native_record(
        {
            "platform_content_id": 1234567890123456789,
            "title": "太古汇活动",
            "content": "公开内容",
            "author_id": "author-1",
            "author_nickname": "作者",
            "publish_datetime": "2026-09-14 10:00:00",
            "likes": 3,
            "comments": 2,
            "shares": 1,
            "raw": {"engine": "fixture"},
        },
        "douyin",
        "广州太古汇",
        "2026-09-14 10:01:00",
    )

    assert record["aweme_id"] == "1234567890123456789"
    assert record["source_keyword"] == "广州太古汇"
    assert record["matched_keywords"] == "广州太古汇"
    assert record["engine"] == "fixture"


def test_collect_search_rejects_non_human_operator():
    with pytest.raises(PermissionError):
        surface.collect_search("douyin", "广州太古汇", operator="agent")


def test_collect_search_follows_read_only_import_and_evidence_chain(monkeypatch):
    class FakeAdapter:
        def health_check(self):
            return CollectionResult(
                status=CollectionStatus.SUCCESS,
                platform="douyin",
                metadata={"engine_ok": True, "cookie_exists": True},
            )

        def search(self, keyword, max_results=20):
            return CollectionResult(
                status=CollectionStatus.SUCCESS,
                platform="douyin",
                raw_count=1,
                items=[{
                    "platform_content_id": "777",
                    "title": "广州太古汇公开内容",
                    "content": "公开内容",
                    "author_id": "author",
                    "author_nickname": "作者",
                    "publish_datetime": "2026-09-14 10:00:00",
                    "url": "https://example.invalid/777",
                    "likes": 1,
                    "comments": 0,
                    "shares": 0,
                    "raw": {},
                }],
            )

    monkeypatch.setattr(surface, "get_adapter", lambda platform: FakeAdapter())
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(surface, "_write_evidence", lambda *args, **kwargs: 1)
    monkeypatch.setattr(surface, "_mark_subject_and_sync", lambda *args, **kwargs: {
        "subject_matches": 1, "canonical_synced": 1, "subjects": [],
    })
    monkeypatch.setattr(
        "platform_adapters.multi_platform_import.import_multi_platform_records",
        lambda records: {"imported": 1, "updated": 0, "failed": 0,
                         "details": [{"status": "imported", "note_id": "777"}]},
    )

    result = surface.collect_search("douyin", "广州太古汇", max_results=1, operator="human")

    assert result["ok"] is True
    assert result["read_only"] is True
    assert result["external_write"] is False
    assert result["publish_authority"] == "human_manual_only"
    assert result["imported"] == 1
    assert result["evidence_recorded"] is True


def test_product_route_requires_explicit_human_read_only_confirmation():
    from flask import Flask
    import experience_runtime

    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)
    client = app.test_client()

    denied = client.post(
        "/api/experience/cth/platform-collection/search",
        json={"operator": "agent", "platform": "douyin", "keyword": "广州太古汇"},
    )
    assert denied.status_code == 403
    assert denied.get_json()["code"] == "HUMAN_OPERATOR_REQUIRED"

    missing_confirmation = client.post(
        "/api/experience/cth/platform-collection/search",
        json={"operator": "human", "platform": "douyin", "keyword": "广州太古汇"},
    )
    assert missing_confirmation.status_code == 400
    assert missing_confirmation.get_json()["code"] == "READ_ONLY_CONFIRMATION_REQUIRED"

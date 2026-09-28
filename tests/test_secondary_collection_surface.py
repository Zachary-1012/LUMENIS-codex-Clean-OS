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

from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
from lumenis.system.collector.adapters import secondary_collection as surface


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
        "bilibili", "weibo", "douyin", "x", "kuaishou", "web_rss",
        "public_http", "web_atom", "sitemap", "zhihu", "instagram"
    ]
    assert result["manual_only"] is True
    assert result["read_only"] is True
    assert result["external_write"] is False
    assert result["product_will_not_publish"] is True
    assert result["primary_collection"]["parallel_collector_added"] is False
    assert "xiaohongshu_cn" in result["paused_platforms"]
    assert "weibo" not in result["paused_platforms"]
    assert "bilibili" not in result["out_of_scope_platforms"]
    assert "kuaishou" not in result["out_of_scope_platforms"]


def test_primary_xhs_status_is_a_separate_read_only_projection(monkeypatch):
    health_calls = []
    monkeypatch.setattr(
        surface,
        "_adapter_health",
        lambda platform: health_calls.append(platform) or {
            "status": "NOT_CONFIGURED", "ready": False, "can_attempt": False,
            "message": "not configured", "metadata": {},
        },
    )
    monkeypatch.setattr(surface, "_last_run", lambda _platform: None)
    monkeypatch.setattr(surface, "_xhs_primary_runtime_status", lambda: {
        "status": "READY", "heartbeat_at": "2026-09-15 09:00:00", "observed": True,
    })
    monkeypatch.setattr(surface, "_xhs_primary_last_run", lambda: {
        "state": "SUCCESS", "fetched": 4, "accepted": None,
        "started_at": "2026-09-15 08:55:00", "finished_at": "2026-09-15 09:00:00",
        "source": "collection_logs",
    })

    result = surface.get_collection_surface()
    primary = result["primary_collection"]

    assert health_calls == list(surface.SECONDARY_COLLECTION_PLATFORMS)
    assert primary["platform"] == "xiaohongshu"
    assert primary["region"] == "hk_international"
    assert primary["status"] == "READY"
    assert primary["last_run"]["fetched"] == 4
    assert primary["last_run"]["accepted"] is None
    assert primary["form_selectable"] is False
    assert primary["parallel_collector_added"] is False
    assert not any(secret in str(primary).lower() for secret in ("cookie", "token", "password"))


def test_primary_xhs_runtime_reader_does_not_import_orchestrator(monkeypatch):
    monkeypatch.delitem(sys.modules, "xhs_p0_orchestrator", raising=False)

    result = surface._xhs_primary_runtime_status()

    assert result == {"status": "UNVERIFIED", "heartbeat_at": None, "observed": False}
    assert "xhs_p0_orchestrator" not in sys.modules


def test_primary_xhs_runtime_reader_requires_a_fresh_heartbeat(monkeypatch):
    import time

    class FakeOrchestrator:
        def get_status(self):
            return {
                "session_ok": True,
                "heartbeat_last": time.time() - 61,
                "heartbeat_interval": 30,
                "resident_mode": "RESIDENT_ACTIVE",
                "user_paused": False,
            }

    monkeypatch.setitem(sys.modules, "xhs_p0_orchestrator", FakeOrchestrator())

    result = surface._xhs_primary_runtime_status()

    assert result["status"] == "UNVERIFIED"
    assert result["observed"] is True


def test_primary_xhs_runtime_reader_accepts_a_fresh_heartbeat(monkeypatch):
    import time

    class FakeOrchestrator:
        def get_status(self):
            return {
                "session_ok": True,
                "heartbeat_last": time.time(),
                "heartbeat_interval": 30,
                "resident_mode": "RESIDENT_ACTIVE",
                "user_paused": False,
            }

    monkeypatch.setitem(sys.modules, "xhs_p0_orchestrator", FakeOrchestrator())

    result = surface._xhs_primary_runtime_status()

    assert result["status"] == "READY"
    assert result["observed"] is True
    assert result["heartbeat_at"]


def test_surface_route_exposes_primary_status_projection(monkeypatch):
    from flask import Flask
    import experience_runtime

    payload = {
        "ok": True,
        "product": "LUMENIS",
        "domain": "CTH",
        "primary_collection": {
            "platform": "xiaohongshu",
            "status": "UNVERIFIED",
            "form_selectable": False,
            "parallel_collector_added": False,
        },
        "platforms": [],
    }
    monkeypatch.setattr(surface, "get_collection_surface", lambda: payload)
    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)

    response = app.test_client().get("/api/experience/cth/platform-collection")

    assert response.status_code == 200
    assert response.get_json()["primary_collection"] == payload["primary_collection"]


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


def test_weibo_is_in_scope_and_mainland_xhs_remains_paused():
    assert surface._validate_request("weibo", "广州太古汇", 5) == (
        "weibo", "广州太古汇", 5
    )
    with pytest.raises(ValueError, match="大陆小红书"):
        surface._validate_request("xiaohongshu_cn", "广州太古汇", 5)


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
    monkeypatch.setattr(surface, "_daily_action_count", lambda platform, at: 0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(surface, "_write_evidence", lambda *args, **kwargs: 1)
    monkeypatch.setattr(surface, "_mark_subject_and_sync", lambda *args, **kwargs: {
        "subject_matches": 1, "canonical_synced": 1, "subjects": [],
    })
    monkeypatch.setattr(
        "lumenis.system.collector.adapters.multi_platform_import.import_multi_platform_records",
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
    assert result["provenance"]["source"] == "platform:douyin"
    assert result["provenance"]["provider"] == "platform_adapter"


def test_native_web_rss_record_maps_existing_canonical_fields():
    record = surface._native_record(
        {
            "platform_content_id": "google-news:abc123",
            "title": "公开新闻标题",
            "content": "",
            "author_id": "媒体来源",
            "author_nickname": "媒体来源",
            "publish_datetime": "2026-09-15 10:00:00",
            "url": "https://news.example/article",
            "likes": None,
            "comments": None,
            "shares": None,
            "raw": {"source_name": "媒体来源", "provider": "google_news_rss"},
        },
        "web_rss",
        "广州太古汇",
        "2026-09-15 10:01:00",
    )

    assert record["content_id"] == "google-news:abc123"
    assert record["source_id"] == "媒体来源"
    assert record["published_at"] == "2026-09-15 10:00:00"
    assert record["like_count"] is None


def test_provider_exception_isolated_and_recorded(monkeypatch):
    class BrokenAdapter:
        def health_check(self):
            return CollectionResult(status=CollectionStatus.SUCCESS, platform="bilibili")

        def search(self, keyword, max_results=20):
            raise RuntimeError("private provider failure detail")

    run_log = {}
    evidence = {}
    monkeypatch.setattr(surface, "get_adapter", lambda platform: BrokenAdapter())
    monkeypatch.setattr(surface, "_daily_action_count", lambda platform, at: 0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: run_log.update(kwargs))
    monkeypatch.setattr(
        surface, "_write_evidence",
        lambda platform, keyword, result, **kwargs: evidence.update(result) or 7,
    )

    result = surface.collect_search("bilibili", "广州太古汇", max_results=1, operator="human")

    assert result["ok"] is False
    assert result["status"] == "PROVIDER_UNAVAILABLE"
    assert result["evidence_recorded"] is True
    assert "private provider failure detail" not in result["error"]
    assert run_log["error"].startswith("PROVIDER_UNAVAILABLE:")
    assert evidence["provenance"]["source"] == "platform:bilibili"


def test_evidence_failure_marker_is_not_reported_as_persisted(monkeypatch):
    from lumenis.shared.evidence import store as evidence_store

    monkeypatch.setattr(surface, "_ensure_evidence_schema", lambda: None)
    monkeypatch.setattr(evidence_store, "record_collection_evidence", lambda **kwargs: -1)

    assert surface._write_evidence(
        "bilibili",
        "广州太古汇",
        {"status": "SUCCESS", "provenance": {"provider": "fixture"}},
        started="2026-09-15 10:00:00",
    ) is None


def test_collection_fails_closed_when_evidence_is_not_persisted(monkeypatch):
    class FakeAdapter:
        def health_check(self):
            return CollectionResult(status=CollectionStatus.SUCCESS, platform="kuaishou")

        def search(self, keyword, max_results=20):
            return CollectionResult(
                status=CollectionStatus.NO_NEW_DATA,
                platform="kuaishou",
                items=[],
            )

    run_log = {}
    monkeypatch.setattr(surface, "get_adapter", lambda platform: FakeAdapter())
    monkeypatch.setattr(surface, "_daily_action_count", lambda platform, at: 0)
    monkeypatch.setattr(surface, "_write_evidence", lambda *args, **kwargs: None)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: run_log.update(kwargs))
    monkeypatch.setitem(surface._last_action, "kuaishou", 0.0)

    result = surface.collect_search("kuaishou", "广州太古汇", max_results=1, operator="human")

    assert result["ok"] is False
    assert result["status"] == "EVIDENCE_WRITE_FAILED"
    assert result["evidence_recorded"] is False
    assert run_log["error"].startswith("EVIDENCE_WRITE_FAILED:")


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


def test_douyin_requires_explicit_remote_browser_worker(monkeypatch):
    from lumenis.adapters.douyin import _configured_browser_worker_url

    monkeypatch.delenv("DOUYIN_CDP_URL", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        _configured_browser_worker_url()

    monkeypatch.setenv("DOUYIN_CDP_URL", "http://127.0.0.1:9222")
    with pytest.raises(RuntimeError, match="loopback"):
        _configured_browser_worker_url()

    monkeypatch.setenv("DOUYIN_CDP_URL", "http://localhost:9222")
    with pytest.raises(RuntimeError, match="remote browser worker"):
        _configured_browser_worker_url()


def test_requested_adapters_expose_uniform_capability_contract():
    from lumenis.system.collector.adapters import get_adapter, list_adapters

    required_platforms = {"xhs", "bilibili", "weibo", "douyin", "x", "kuaishou", "web_rss"}
    assert required_platforms.issubset(set(list_adapters()))
    required_capabilities = {
        "search", "detail", "comments", "author", "author_posts", "healthcheck",
    }
    for platform in required_platforms:
        adapter = get_adapter(platform)
        assert set(adapter.capability_map()) == required_capabilities

    assert get_adapter("kuaishou").search("广州太古汇").status == CollectionStatus.NOT_CONFIGURED
    rss = get_adapter("web_rss")
    assert rss.capability_map()["detail"] == "not_supported"
    assert rss.detail("news-1").status == CollectionStatus.NOT_SUPPORTED
    assert rss.comments("news-1").status == CollectionStatus.NOT_SUPPORTED
    assert rss.author_posts("publisher").status == CollectionStatus.NOT_SUPPORTED

"""CTH secondary collection surface tests.

These tests exercise the product boundary with local fakes only.  They must
never start a browser, call a platform, or use the production database.
"""
from __future__ import annotations

import os
import sys
from copy import deepcopy

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
from lumenis.system.collector.adapters import secondary_collection as surface


class _ServerActorStub:
    actor_id = "test-server-actor"
    principal_kind = "server"


@pytest.fixture
def approved_global_request():
    return {
        "actor": _ServerActorStub(),
        "scope": {
            "domain_id": "cth", "global_scope": True,
            "subject_id": None, "brand_focus_id": None,
        },
    }


def _stub_approved_global_guard(monkeypatch, request):
    def allow(actor, scope, platform, keyword, max_results):
        assert actor is request["actor"]
        assert scope == request["scope"]
        return dict(request["scope"]), None

    monkeypatch.setattr(surface, "_manual_collection_guard", allow)


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
        "public_http", "web_atom", "sitemap", "zhihu", "instagram",
        "wechat", "facebook", "xiaohongshu"
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


def test_collect_search_follows_read_only_import_and_evidence_chain(monkeypatch, approved_global_request):
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
    monkeypatch.setattr(surface, "_write_prelaunch_evidence", lambda *args, **kwargs: 1)
    monkeypatch.setattr(surface, "_sync_unassigned_collection", lambda note_ids, scope, evidence_id, **kwargs: len(note_ids))
    monkeypatch.setattr(surface, "_prelaunch_scope_conflict", lambda records, scope, **kwargs: False)
    from lumenis.shared.database import platform_content
    monkeypatch.setattr(platform_content, "platform_records_changed", lambda *args, **kwargs: True)
    def write_native(records, **kwargs):
        assert kwargs["connection"].in_transaction
        assert kwargs["scope"]["global_scope"] is True
        return len(records)
    monkeypatch.setattr(platform_content, "persist_unassigned_platform_records", write_native)
    _stub_approved_global_guard(monkeypatch, approved_global_request)
    monkeypatch.setattr(
        "lumenis.system.collector.adapters.multi_platform_import.import_multi_platform_records",
        lambda records, **kwargs: {"imported": 1, "updated": 0, "failed": 0,
                         "details": [{"status": "imported", "note_id": "777"}]},
    )

    result = surface.collect_search(
        "douyin", "广州太古汇", max_results=1, operator="human",
        actor=approved_global_request["actor"], scope=approved_global_request["scope"],
    )

    assert result["ok"] is True
    assert result["read_only"] is True
    assert result["external_write"] is False
    assert result["publish_authority"] == "human_manual_only"
    assert result["imported"] == 1
    assert result["canonical_synced"] == 1
    assert result["native_fields_synced"] == 1 and result["refresh_verified"] is True
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
    assert record.get("source_id") is None
    assert record["source_name"] == "媒体来源"
    assert record["published_at"] == "2026-09-15 10:00:00"
    assert record.get("like_count") is None
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record
    assert to_canonical_record(record, "web_rss")["author_id"] is None


def test_native_bilibili_search_record_bridges_source_publication_and_favorites():
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    item = {
        "platform_content_id": "BV1Q541167Qg",
        "title": "Bilibili search result",
        "content": "Source description",
        "author_id": "",
        "author_nickname": "Uploader",
        "publish_datetime": "2026-09-18T04:00:00+00:00",
        "url": "https://www.bilibili.com/video/BV1Q541167Qg",
        "likes": None,
        "comments": None,
        "collects": 123,
        "shares": None,
        "raw": {
            "engine": "bilibili_search_api",
            "bvid": "BV1Q541167Qg",
            "pubdate_ts": 1789704000,
            "video_review": 17,
        },
    }
    original = deepcopy(item)

    record = surface._native_record(
        item, "bilibili", "广州太古汇", "2026-09-18T04:01:00+00:00",
    )
    canonical = to_canonical_record(record, "bilibili")

    assert record["bvid"] == "BV1Q541167Qg"
    assert record["pubdate"] == "2026-09-18T04:00:00+00:00"
    assert record["pubdate_ts"] == 1789704000
    assert record["favorite"] == 123
    assert record.get("reply") is None
    assert canonical["published_at"] == "2026-09-18T04:00:00+00:00"
    assert canonical["collect_count"] == 123
    assert canonical["comment_count"] is None
    assert record["captured_at"] == "2026-09-18T04:01:00+00:00"
    assert item == original


def test_native_bilibili_detail_keeps_existing_native_values_and_fills_gaps():
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    item = {
        "platform_content_id": "BV1detail",
        "author_id": "87654321",
        "publish_datetime": "2026-09-18T04:00:00+00:00",
        "likes": 41,
        "comments": 12,
        "collects": 23,
        "shares": 7,
        "raw": {
            "bvid": "BV1detail",
            "mid": "87654321",
            "pubdate": 1789704000,
            "pubdate_ts": 1789704000,
            "like": 41,
            "reply": 12,
            "favorite": 23,
            "share": 7,
        },
    }
    original = deepcopy(item)

    record = surface._native_record(item, "bilibili", "query", "capture")
    canonical = to_canonical_record(record, "bilibili")

    assert record["bvid"] == "BV1detail"
    assert record["mid"] == "87654321"
    assert record["pubdate"] == 1789704000
    assert record["pubdate_ts"] == 1789704000
    assert (record["like"], record["reply"], record["favorite"], record["share"]) == (41, 12, 23, 7)
    assert (canonical["like_count"], canonical["comment_count"], canonical["collect_count"], canonical["share_count"]) == (41, 12, 23, 7)
    assert item == original


def test_native_bilibili_missing_source_values_stay_null_without_capture_fallback():
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    item = {
        "platform_content_id": "BV1unknown",
        "publish_datetime": "",
        "likes": None,
        "comments": None,
        "collects": None,
        "shares": None,
        "raw": {"bvid": "BV1unknown", "video_review": 99},
    }

    record = surface._native_record(item, "bilibili", "query", "2026-09-18T04:01:00+00:00")
    canonical = to_canonical_record(record, "bilibili")

    assert record["bvid"] == "BV1unknown"
    assert record.get("pubdate") is None
    assert record.get("reply") is None
    assert record.get("favorite") is None
    assert record["captured_at"] == "2026-09-18T04:01:00+00:00"
    assert canonical["published_at"] is None
    assert canonical["like_count"] is None
    assert canonical["comment_count"] is None
    assert canonical["collect_count"] is None
    assert canonical["share_count"] is None


def test_native_bilibili_source_identity_and_zero_metrics_win_over_projection():
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    item = {
        "platform_content_id": "BVprojected",
        "author_id": "87654321",
        "likes": 41,
        "comments": 12,
        "collects": 23,
        "shares": 7,
        "raw": {"bvid": "BVnative", "like": 0, "favorite": 0},
    }

    record = surface._native_record(item, "bilibili", "query", "capture")
    canonical = to_canonical_record(record, "bilibili")

    assert canonical["content_id"] == "BVnative"
    assert (record["like"], record["favorite"]) == (0, 0)
    assert (record["mid"], record["reply"], record["share"]) == ("87654321", 12, 7)


def test_native_weibo_post_identity_author_and_zero_metrics_are_distinct():
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    item = {
        "platform_content_id": "projection-post-id",
        "author_id": "projection-author-id",
        "author_nickname": "Projected author",
        "publish_datetime": "projection-publication",
        "likes": 99,
        "comments": 98,
        "shares": 97,
        "raw": {
            "engine": "weibo_mobile_search_api",
            "mid": "5071234567890123456",
            "idstr": "5071234567890123456",
            "user_id": "2468013579",
            "created_at": "native-publication",
            "attitudes_count": 0,
            "comments_count": 14,
            "reposts_count": 6,
        },
    }
    original = deepcopy(item)

    record = surface._native_record(item, "weibo", "query", "capture-time")
    canonical = to_canonical_record(record, "weibo")

    assert record["mid"] == "5071234567890123456"
    assert record["idstr"] == "5071234567890123456"
    assert record["user_id"] == "2468013579"
    assert canonical["content_id"] == "5071234567890123456"
    assert canonical["author_id"] == "2468013579"
    assert canonical["published_at"] == "native-publication"
    assert (canonical["like_count"], canonical["comment_count"], canonical["share_count"]) == (0, 14, 6)
    assert record["captured_at"] == "capture-time"
    assert item == original


def test_native_weibo_post_id_does_not_fill_unknown_author():
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    item = {
        "platform_content_id": "5071234567890123456",
        "author_id": "",
        "raw": {
            "engine": "weibo_mobile_search_api",
            "mid": "5071234567890123456",
            "idstr": "5071234567890123456",
        },
    }
    original = deepcopy(item)

    record = surface._native_record(item, "weibo", "query", "capture-time")
    canonical = to_canonical_record(record, "weibo")

    assert record["mid"] == "5071234567890123456"
    assert record["idstr"] == "5071234567890123456"
    assert record.get("user_id") is None
    assert canonical["author_id"] is None
    assert item == original


def test_provider_exception_isolated_and_recorded(monkeypatch, approved_global_request):
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
    _stub_approved_global_guard(monkeypatch, approved_global_request)
    monkeypatch.setattr(
        surface, "_write_prelaunch_evidence",
        lambda platform, keyword, result, **kwargs: evidence.update(result) or 7,
    )

    result = surface.collect_search(
        "bilibili", "广州太古汇", max_results=1, operator="human",
        actor=approved_global_request["actor"], scope=approved_global_request["scope"],
    )

    assert result["ok"] is False
    assert result["status"] == "PROVIDER_UNAVAILABLE"
    assert result["evidence_recorded"] is True
    assert "private provider failure detail" not in result["error"]
    assert run_log["error"].startswith("PROVIDER_UNAVAILABLE:")
    assert evidence["provenance"]["source"] == "platform:bilibili"


def test_evidence_failure_marker_is_not_reported_as_persisted(monkeypatch, approved_global_request):
    from lumenis.shared.evidence import store as evidence_store

    monkeypatch.setattr(surface, "_ensure_evidence_schema", lambda: None)
    monkeypatch.setattr(evidence_store, "record_evidence", lambda **kwargs: -1)

    assert surface._write_prelaunch_evidence(
        "bilibili",
        "广州太古汇",
        {"status": "SUCCESS", "provenance": {"provider": "fixture"}},
        started="2026-09-15 10:00:00",
        scope=approved_global_request["scope"],
        source_ids=[],
        manual=True,
    ) is None


def test_collection_fails_closed_when_evidence_is_not_persisted(monkeypatch, approved_global_request):
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
    _stub_approved_global_guard(monkeypatch, approved_global_request)
    monkeypatch.setattr(surface, "_write_prelaunch_evidence", lambda *args, **kwargs: None)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: run_log.update(kwargs))
    monkeypatch.setitem(surface._last_action, "kuaishou", 0.0)

    result = surface.collect_search(
        "kuaishou", "广州太古汇", max_results=1, operator="human",
        actor=approved_global_request["actor"], scope=approved_global_request["scope"],
    )

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


def test_product_business_route_forwards_query_checkpoint_and_rejects_it_for_single_source(monkeypatch):
    from flask import Flask
    import experience_runtime

    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)
    client = app.test_client()
    checkpoint = {"input_fingerprint": "a" * 64, "completed_query_keys": ["b" * 64]}
    captured = {}
    actor = object()
    scope = {"domain_id": "cth", "global_scope": True}
    monkeypatch.setattr(experience_runtime, "_content_project_scope",
                        lambda *_args, **_kwargs: (actor, scope))

    def collect_business_queries(requests, **kwargs):
        captured.update(requests=requests, **kwargs)
        return {"ok": True, "status": "PARTIAL", "checkpoint": checkpoint,
                "coverage_complete": False, "runs": []}

    monkeypatch.setattr(surface, "collect_business_queries", collect_business_queries)
    monkeypatch.setattr(surface, "collect_search",
                        lambda *_args, **_kwargs: pytest.fail("single-source path must not run"))

    resumed = client.post(
        "/api/experience/cth/platform-collection/search",
        json={"operator": "human", "confirm_read_only": True,
              "business_requests": [{"purpose": "test-only route envelope"}],
              "checkpoint": checkpoint, "max_queries": 4},
    )
    assert resumed.status_code == 200
    assert captured["checkpoint"] == checkpoint
    assert captured["max_queries"] == 4
    assert captured["actor"] is actor and captured["scopes"] == {"cth": scope}
    assert resumed.get_json()["coverage_complete"] is False

    wrong_route = client.post(
        "/api/experience/cth/platform-collection/search",
        json={"operator": "human", "confirm_read_only": True,
              "platform": "douyin", "keyword": "brand", "checkpoint": checkpoint},
    )
    assert wrong_route.status_code == 400
    assert wrong_route.get_json()["status"] == "invalid_request"


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

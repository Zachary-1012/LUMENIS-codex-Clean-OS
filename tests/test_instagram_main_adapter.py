# -*- coding: utf-8 -*-
"""Instagram 主链路适配器单元测试（全 mock，不启动浏览器、不访问网络）。"""
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lumenis.system.collector.adapters import get_adapter
from lumenis.system.collector.adapters.base import BasePlatformAdapter, CollectionStatus
from lumenis.system.collector.adapters.instagram import InstagramAdapter
from lumenis.adapters.base import AdapterResult, CollectedNote


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_note(**overrides) -> CollectedNote:
    defaults = dict(
        title="test post",
        content="caption text",
        url="https://www.instagram.com/p/ABC123/",
        author="testuser",
        author_id="",
        publish_date="2026-09-01T12:00:00Z",
        likes=100,
        comments=5,
        collects=0,
        shares=0,
        cover="",
        source_platform="instagram",
        raw_data={"shortcode": "ABC123", "media_type": "post", "needs_detail": False},
    )
    defaults.update(overrides)
    return CollectedNote(**defaults)


def _make_engine(result: AdapterResult) -> MagicMock:
    """Create a mock v4 engine that returns *result* for every method."""
    engine = MagicMock()
    engine.search.return_value = result
    engine.detail.return_value = result
    engine.comments.return_value = result
    engine.creator.return_value = result
    return engine


def _adapter_with_engine(result: AdapterResult) -> InstagramAdapter:
    return InstagramAdapter(engine=_make_engine(result))


# ---------------------------------------------------------------------------
# 1. Registry
# ---------------------------------------------------------------------------
def test_registry_can_get_instagram_adapter():
    adapter = get_adapter("instagram")
    assert adapter.platform == "instagram"
    assert isinstance(adapter, BasePlatformAdapter)
    assert adapter.enabled is False
    assert adapter.monitor_priority == "secondary"


# ---------------------------------------------------------------------------
# 2. normalize_item field mapping
# ---------------------------------------------------------------------------
def test_normalize_item_field_mapping():
    adapter = InstagramAdapter(engine=MagicMock())
    note = _make_note()
    item = adapter.normalize_item(note.__dict__)
    assert item["platform_content_id"] == "ABC123"
    assert item["content"] == "caption text"
    assert item["author_nickname"] == "testuser"
    assert item["publish_datetime"] == "2026-09-01T12:00:00Z"
    assert item["likes"] == 100
    assert item["url"] == "https://www.instagram.com/p/ABC123/"
    assert item["source_platform"] == "instagram"
    assert item["raw"]["media_type"] == "post"
    assert item["raw"]["needs_detail"] is False


def test_normalize_item_extracts_shortcode_from_url_when_raw_missing():
    adapter = InstagramAdapter(engine=MagicMock())
    note = _make_note(raw_data={})
    item = adapter.normalize_item(note.__dict__)
    assert item["platform_content_id"] == "ABC123"


def test_normalize_item_preserves_zero_and_maps_missing_or_invalid_counts_to_unknown():
    adapter = InstagramAdapter(engine=MagicMock())
    note = _make_note(
        likes=0,
        comments=None,
        collects="not-a-count",
        shares="",
    )

    item = adapter.normalize_item(note.__dict__)

    assert item["platform_content_id"] == "ABC123"
    assert item["likes"] == 0
    assert item["comments"] is None
    assert item["collects"] is None
    assert item["shares"] is None


# ---------------------------------------------------------------------------
# 3-8. Status mapping via search()
# ---------------------------------------------------------------------------
def test_status_mapping_success():
    result = AdapterResult(success=True, notes=[_make_note()], raw_count=1)
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.SUCCESS
    assert cr.new_count == 1
    assert cr.raw_count == 1


def test_status_mapping_no_new_data():
    result = AdapterResult(success=True, notes=[], raw_count=0)
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.NO_NEW_DATA
    assert cr.new_count == 0


def test_status_mapping_session_expired():
    result = AdapterResult(
        success=False,
        error="Instagram 登录态失效，请更新 Cookie 或在代理 Profile 重新登录",
    )
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.SESSION_EXPIRED


def test_status_mapping_need_verify():
    result = AdapterResult(
        success=False,
        error="Instagram 出现确认/人机验证，需人工通过后再采",
    )
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.NEED_VERIFY


def test_status_mapping_blocked():
    result = AdapterResult(
        success=False,
        error="Instagram 触发频控，按熔断退避不硬刚",
    )
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.BLOCKED


def test_status_mapping_collect_error_proxy():
    result = AdapterResult(
        success=False,
        error="Instagram 需经代理访问，未配置 GOOGLE_PROXY / OPENAI_PROXY",
    )
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.COLLECT_ERROR
    assert "代理" in cr.message


def test_status_mapping_collect_error_other():
    result = AdapterResult(success=False, error="Instagram 浏览器采集异常: timeout")
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.COLLECT_ERROR


# ---------------------------------------------------------------------------
# 9-10. health_check (local only, no network)
# ---------------------------------------------------------------------------
def test_health_check_no_cookie_no_proxy(monkeypatch):
    monkeypatch.setenv("GOOGLE_PROXY", "")
    monkeypatch.setenv("OPENAI_PROXY", "")
    adapter = InstagramAdapter(engine=MagicMock())
    # Point cookie path to a non-existent file
    monkeypatch.setattr(InstagramAdapter, "COOKIE_PATH", Path("/nonexistent/fake_ig_cookie.json"))
    hc = adapter.health_check()
    assert hc.status == CollectionStatus.COLLECT_ERROR
    assert "cookie" in hc.message.lower() or "Cookie" in hc.message
    assert "代理" in hc.message or "proxy" in hc.message.lower()
    assert hc.metadata["cookie_exists"] is False
    assert hc.metadata["proxy_configured"] is False


def test_health_check_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_PROXY", "http://proxy.example.com:8080")
    monkeypatch.setenv("OPENAI_PROXY", "")
    # Create a fake non-empty cookie file
    fake_cookie = tmp_path / "instagram.json"
    fake_cookie.write_text('[{"name":"sessionid","value":"test"}]', encoding="utf-8")
    adapter = InstagramAdapter(engine=MagicMock())
    monkeypatch.setattr(InstagramAdapter, "COOKIE_PATH", fake_cookie)
    hc = adapter.health_check()
    assert hc.status == CollectionStatus.SUCCESS
    assert "ready" in hc.message.lower()
    assert hc.metadata["cookie_exists"] is True
    assert hc.metadata["proxy_configured"] is True


def test_health_check_cookie_missing_only(monkeypatch):
    monkeypatch.setenv("GOOGLE_PROXY", "http://proxy:8080")
    monkeypatch.setenv("OPENAI_PROXY", "")
    adapter = InstagramAdapter(engine=MagicMock())
    monkeypatch.setattr(InstagramAdapter, "COOKIE_PATH", Path("/nonexistent/fake.json"))
    hc = adapter.health_check()
    # proxy configured but cookie missing -> SESSION_EXPIRED
    assert hc.status == CollectionStatus.SESSION_EXPIRED
    assert hc.metadata["cookie_exists"] is False
    assert hc.metadata["proxy_configured"] is True


# ---------------------------------------------------------------------------
# 11. detail delegates to engine
# ---------------------------------------------------------------------------
def test_detail_delegates_to_engine():
    note = _make_note(publish_date="2026-08-15T10:30:00Z")
    result = AdapterResult(success=True, notes=[note], raw_count=1)
    engine = MagicMock()
    engine.detail.return_value = result
    adapter = InstagramAdapter(engine=engine)
    cr = adapter.detail("ABC123")
    assert cr.status == CollectionStatus.SUCCESS
    assert len(cr.items) == 1
    assert cr.items[0]["publish_datetime"] == "2026-08-15T10:30:00Z"
    assert cr.metadata["shortcode"] == "ABC123"
    engine.detail.assert_called_once_with("ABC123", media_type="post")


def test_detail_passes_media_type():
    result = AdapterResult(success=True, notes=[_make_note()], raw_count=1)
    engine = MagicMock()
    engine.detail.return_value = result
    adapter = InstagramAdapter(engine=engine)
    adapter.detail("REEL123", media_type="reel")
    engine.detail.assert_called_once_with("REEL123", media_type="reel")


# ---------------------------------------------------------------------------
# 12. comments delegates to engine
# ---------------------------------------------------------------------------
def test_comments_delegates_to_engine():
    comments_data = [
        {"author": "user1", "content": "great post!", "publish_time": "2026-09-01T10:00:00Z", "likes": 2},
        {"author": "user2", "content": "love this", "publish_time": "2026-09-01T11:00:00Z", "likes": 0},
    ]
    note = CollectedNote(
        title="comments",
        content="2 comments",
        url="https://www.instagram.com/p/ABC123/",
        raw_data={"shortcode": "ABC123", "comments": comments_data},
    )
    result = AdapterResult(success=True, notes=[note], raw_count=2)
    engine = MagicMock()
    engine.comments.return_value = result
    adapter = InstagramAdapter(engine=engine)
    cr = adapter.comments("ABC123")
    assert cr.status == CollectionStatus.SUCCESS
    assert len(cr.comments) == 2
    assert cr.comments[0]["author"] == "user1"
    assert cr.comments[0]["content"] == "great post!"
    assert cr.new_count == 2
    engine.comments.assert_called_once_with("ABC123", max_comments=20)


def test_comments_no_data_maps_to_no_new_data():
    note = CollectedNote(
        title="comments",
        content="0 comments",
        url="https://www.instagram.com/p/ABC123/",
        raw_data={"shortcode": "ABC123", "comments": []},
    )
    result = AdapterResult(success=True, notes=[note], raw_count=0)
    adapter = _adapter_with_engine(result)
    cr = adapter.comments("ABC123")
    assert cr.status == CollectionStatus.NO_NEW_DATA
    assert len(cr.comments) == 0


# ---------------------------------------------------------------------------
# 13. creator delegates to engine
# ---------------------------------------------------------------------------
def test_creator_delegates_to_engine():
    note = CollectedNote(
        title="testcreator",
        content="bio text here",
        url="https://www.instagram.com/testcreator/",
        author="testcreator",
        raw_data={
            "username": "testcreator",
            "followers": 15000,
            "following": 300,
            "posts": 120,
            "verified": True,
            "creator_type": "instagram_user",
        },
    )
    result = AdapterResult(success=True, notes=[note], raw_count=1)
    engine = MagicMock()
    engine.creator.return_value = result
    adapter = InstagramAdapter(engine=engine)
    cr = adapter.creator("testcreator")
    assert cr.status == CollectionStatus.SUCCESS
    assert len(cr.items) == 1
    assert cr.items[0]["raw"]["followers"] == 15000
    assert cr.items[0]["raw"]["verified"] is True
    assert cr.items[0]["author_nickname"] == "testcreator"
    assert cr.metadata["username"] == "testcreator"
    engine.creator.assert_called_once_with("testcreator")


# ---------------------------------------------------------------------------
# Additional: engine lazy-load does not import at construction
# ---------------------------------------------------------------------------
def test_adapter_construction_does_not_load_engine():
    """Constructing with engine=None should not trigger v4 import."""
    import sys
    # We can't easily unimport v4, but we can verify _engine is None
    adapter = InstagramAdapter()
    assert adapter._engine is None
    assert adapter._engine_loaded is False


def test_search_exception_returns_collect_error():
    engine = MagicMock()
    engine.search.side_effect = RuntimeError("browser crashed")
    adapter = InstagramAdapter(engine=engine)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.COLLECT_ERROR
    assert "browser crashed" in cr.message

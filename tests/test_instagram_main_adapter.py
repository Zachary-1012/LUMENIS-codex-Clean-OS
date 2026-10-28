# -*- coding: utf-8 -*-
"""Instagram 主链路适配器单元测试（全 mock，不启动浏览器、不访问网络）。"""
import os
from pathlib import Path
from unittest.mock import MagicMock
from concurrent.futures import CancelledError

import pytest

from lumenis.system.collector.adapters import get_adapter
from lumenis.system.collector.adapters.base import BasePlatformAdapter, CollectionStatus
from lumenis.system.collector.adapters.instagram import InstagramAdapter
from lumenis.adapters.base import AdapterResult, CollectedNote
from lumenis.adapters.instagram import InstagramAdapter as V4InstagramAdapter


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
        raw_data={"shortcode": "ABC123", "media_type": "post", "needs_detail": False,
                  "native_identity": {"shortcode": "ABC123", "requested_shortcode": "ABC123",
                                      "status": "OBSERVED_MATCH"}},
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
    assert cr.status == CollectionStatus.COOLING_DOWN


def test_status_mapping_collect_error_proxy():
    result = AdapterResult(
        success=False,
        error="Instagram 需经代理访问，未配置 GOOGLE_PROXY / OPENAI_PROXY",
    )
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.NOT_CONFIGURED
    assert "代理" in cr.message


def test_status_mapping_collect_error_other():
    result = AdapterResult(success=False, error="Instagram 浏览器采集异常: timeout")
    adapter = _adapter_with_engine(result)
    cr = adapter.search("test")
    assert cr.status == CollectionStatus.PROVIDER_UNAVAILABLE


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
    assert hc.status == CollectionStatus.NOT_CONFIGURED
    assert hc.metadata["worker_binding_registered"] is False
    assert hc.metadata["login_and_collection_verified"] is False
    assert not adapter._engine.mock_calls


def test_health_check_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_PROXY", "http://proxy.example.com:8080")
    monkeypatch.setenv("OPENAI_PROXY", "")
    # Create a fake non-empty cookie file
    fake_cookie = tmp_path / "instagram.json"
    fake_cookie.write_text('[{"name":"sessionid","value":"test"}]', encoding="utf-8")
    adapter = InstagramAdapter(engine=MagicMock())
    monkeypatch.setattr(InstagramAdapter, "COOKIE_PATH", fake_cookie)
    hc = adapter.health_check()
    # A local file/proxy cannot make a worker, consent or platform session ready.
    assert hc.status == CollectionStatus.NOT_CONFIGURED
    assert hc.metadata["worker_binding_registered"] is False
    assert hc.metadata["login_and_collection_verified"] is False


def test_health_check_cookie_missing_only(monkeypatch):
    monkeypatch.setenv("GOOGLE_PROXY", "http://proxy:8080")
    monkeypatch.setenv("OPENAI_PROXY", "")
    adapter = InstagramAdapter(engine=MagicMock())
    monkeypatch.setattr(InstagramAdapter, "COOKIE_PATH", Path("/nonexistent/fake.json"))
    hc = adapter.health_check()
    assert hc.status == CollectionStatus.NOT_CONFIGURED
    assert hc.metadata["worker_binding_registered"] is False


def test_public_post_health_requires_real_document_read_without_worker():
    adapter = InstagramAdapter(engine=MagicMock())
    health = adapter.health_check(url="https://www.instagram.com/p/ABC123/")
    assert health.status == CollectionStatus.NEED_VERIFY
    assert health.metadata["provider"] == "public_native_post_document"
    assert health.metadata["requires_auth"] is False


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
    engine.comments.assert_called_once_with("ABC123", max_comments=20, cursor=None, include_replies=False)


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


@pytest.mark.parametrize("method,operation", [
    ("comments", "comments"),
    ("creator", "creator"),
])
def test_fix_105_original_instagram_adapter_redacts_exception_and_cause(method, operation, monkeypatch, caplog):
    engine = V4InstagramAdapter()

    def fail(*args, **kwargs):
        try:
            raise RuntimeError("cookie=CAUSE_SECRET page=PRIVATE_PAGE_TEXT")
        except RuntimeError as cause:
            raise ValueError("token=TOP_SECRET session=EXCEPTION_TEXT") from cause

    monkeypatch.setattr(engine, "_native_read", fail)
    with caplog.at_level("WARNING", logger="lumenis.adapters.instagram"):
        result = getattr(engine, method)("ABC123" if method == "comments" else "testcreator")

    assert result.success is False
    assert result.error == "INSTAGRAM_FAILURE:AUTH_REQUIRED"
    assert result.diagnostics["error_code"] == result.error
    assert result.diagnostics["stack"]
    assert "TOP_SECRET" not in result.error
    assert "CAUSE_SECRET" not in repr(result.diagnostics)
    assert "PRIVATE_PAGE_TEXT" not in caplog.text
    assert "TOP_SECRET" not in caplog.text
    assert "CAUSE_SECRET" not in caplog.text
    assert "ValueError" not in caplog.text


def test_fix_105_registered_comments_exception_is_redacted():
    engine = MagicMock()

    def fail(*args, **kwargs):
        try:
            raise RuntimeError("cookie=CAUSE_SECRET")
        except RuntimeError as cause:
            raise ValueError("token=TOP_SECRET page=PRIVATE_PAGE_TEXT") from cause

    engine.comments.side_effect = fail
    result = InstagramAdapter(engine=engine).comments("ABC123")
    assert result.status == CollectionStatus.COLLECT_ERROR
    assert result.message == "INSTAGRAM_FAILURE:UPSTREAM_FAILURE"
    assert result.metadata["failure_diagnostic"]["stack"]
    assert "TOP_SECRET" not in result.message
    assert "CAUSE_SECRET" not in repr(result.metadata)
    assert "PRIVATE_PAGE_TEXT" not in repr(result.metadata)


def test_fix_105_registered_creator_sanitizes_engine_error_text():
    engine = MagicMock()
    engine.creator.return_value = AdapterResult(
        success=False,
        error="token=TOP_SECRET payload=PRIVATE_PAGE_TEXT",
        diagnostics={"error_code": "INSTAGRAM_FAILURE:UPSTREAM_FAILURE",
                     "stack": [{"file": "secret/path.py", "line": 2, "function": "bad\nframe"}]},
    )
    result = InstagramAdapter(engine=engine).creator("testcreator")
    assert result.status == CollectionStatus.COLLECT_ERROR
    assert result.message == "INSTAGRAM_FAILURE:UPSTREAM_FAILURE"
    assert result.metadata["failure_diagnostic"] == {
        "error_code": "INSTAGRAM_FAILURE:UPSTREAM_FAILURE", "stack": [],
    }
    assert "TOP_SECRET" not in result.message
    assert "PRIVATE_PAGE_TEXT" not in repr(result.metadata)


@pytest.mark.parametrize(('error','expected'), [
    ('READONLY_WORKER_NOT_CONFIGURED', 'INSTAGRAM_FAILURE:NOT_CONFIGURED'),
    ('READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE', 'INSTAGRAM_FAILURE:PROVIDER_UNAVAILABLE'),
    ('network connection timeout', 'INSTAGRAM_FAILURE:NETWORK_UNAVAILABLE'),
])
@pytest.mark.parametrize('operation', ['comments', 'creator'])
def test_fix_105_worker_configuration_and_unavailable_codes_stay_distinct(
        monkeypatch, error, expected, operation):
    from lumenis.adapters.instagram import InstagramAdapter as OriginalInstagramAdapter

    def fail_before_browser(*_args, **_kwargs):
        raise RuntimeError(error)

    monkeypatch.setattr('lumenis.adapters.instagram.configured_readonly_worker_url', fail_before_browser)
    engine = OriginalInstagramAdapter()
    result = getattr(engine, operation)('ABC123' if operation == 'comments' else 'testcreator')
    assert result.success is False
    assert result.error == expected
    assert result.diagnostics['error_code'] == expected


@pytest.mark.parametrize('operation', ['comments', 'creator'])
def test_fix_105_registered_instagram_raised_failures_use_sanitized_status(operation):
    engine = MagicMock()
    getattr(engine, operation).side_effect = TimeoutError('timeout token=TOP_SECRET')
    result = getattr(InstagramAdapter(engine=engine), operation)(
        'ABC123' if operation == 'comments' else 'testcreator'
    )
    assert result.status == CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.message == 'INSTAGRAM_FAILURE:NETWORK_UNAVAILABLE'
    assert 'TOP_SECRET' not in repr(result)


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


def test_detail_exception_preserves_search_observation_and_honest_partial_state(caplog):
    engine = _make_engine(AdapterResult(success=True, notes=[_make_note(likes=0)], raw_count=1))
    engine.detail.side_effect = TimeoutError('do not log secret payload')
    result = InstagramAdapter(engine=engine).search('test')
    assert result.status == CollectionStatus.PROVIDER_UNAVAILABLE and not result.ok
    assert len(result.items) == result.raw_count == 1
    item = result.items[0]
    assert item['raw']['search_summary_observation']['text'] == 'caption text'
    assert item['raw']['search_summary_observation']['metrics']['likes'] == 0
    assert item['content'] == '' and item['likes'] is None
    assert item['raw']['detail_observation']['status'] == 'PROVIDER_UNAVAILABLE'
    assert result.metadata['search_status'] == 'SUCCESS'
    assert result.metadata['acquisition_state'] == 'PARTIAL'
    assert 'do not log secret payload' not in caplog.text


def _native_note(code, **kwargs):
    return _make_note(url=f'https://www.instagram.com/p/{code}/', raw_data={
        'shortcode': code, 'native_identity': {'shortcode': code,
        'requested_shortcode': code, 'status': 'OBSERVED_MATCH'}}, **kwargs)


@pytest.mark.parametrize('failure', [TimeoutError('synthetic timeout'), CancelledError()])
def test_mixed_detail_failure_keeps_completed_body_and_stops_remaining_requests(failure):
    notes = [_native_note(code) for code in ('ONE', 'TWO', 'THREE')]
    engine = _make_engine(AdapterResult(success=True, notes=notes, raw_count=3))
    engine.detail.side_effect = [AdapterResult(success=True, notes=[_native_note('ONE', likes=0, comments=None)]), failure]
    result = InstagramAdapter(engine=engine).search('test')
    assert not result.ok and len(result.items) == 3
    assert engine.detail.call_count == 2
    first, second, third = result.items
    assert first['content'] == 'caption text' and first['likes'] == 0 and first['comments'] is None
    assert first['raw']['detail_observation']['status'] == 'SUCCESS'
    assert second['raw']['search_summary_observation']['text'] == 'caption text'
    assert third['raw']['detail_observation']['status'] == 'PENDING'
    assert result.metadata['detail']['succeeded'] == 1
    assert result.metadata['detail']['failed'] == result.metadata['detail']['pending'] == 1
    assert result.metadata['acquisition_state'] == 'PARTIAL'


def test_missing_detail_result_is_not_complete_success():
    engine = _make_engine(AdapterResult(success=True, notes=[_make_note()], raw_count=1))
    engine.detail.return_value = AdapterResult(success=True, notes=[], raw_count=0)
    result = InstagramAdapter(engine=engine).search('test')
    assert result.status == CollectionStatus.COLLECT_ERROR and not result.ok
    assert len(result.items) == 1
    assert result.items[0]['raw']['detail_observation']['status'] == 'DETAIL_NOT_RETURNED'


def test_async_cancellation_is_not_swallowed_as_provider_failure():
    import asyncio
    engine = _make_engine(AdapterResult(success=True, notes=[_make_note()], raw_count=1))
    engine.detail.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        InstagramAdapter(engine=engine).search('test')


def test_unverified_detail_identity_stays_partial_without_promoting_body():
    engine = _make_engine(AdapterResult(success=True, notes=[_make_note()], raw_count=1))
    engine.detail.return_value = AdapterResult(success=True, notes=[_make_note(raw_data={'shortcode': 'ABC123'})])
    result = InstagramAdapter(engine=engine).search('test')
    assert not result.ok and result.metadata['acquisition_state'] == 'PARTIAL'
    assert result.items[0]['content'] == ''
    assert result.items[0]['raw']['detail_observation']['status'] == 'IDENTITY_MISMATCH'


def test_missing_native_id_keeps_preview_without_detail_call_or_success():
    engine = _make_engine(AdapterResult(success=True, notes=[_make_note(url='', raw_data={})], raw_count=1))
    result = InstagramAdapter(engine=engine).search('test')
    engine.detail.assert_not_called()
    assert not result.ok and len(result.items) == 1
    assert result.items[0]['raw']['search_summary_observation']['text'] == 'caption text'
    assert result.items[0]['raw']['detail_observation']['status'] == 'NOT_ATTEMPTED_NO_NATIVE_ID'

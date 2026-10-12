"""Injected-backend unit regressions; never open a browser or collect live data."""
from types import SimpleNamespace

import pytest

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.douyin import DouyinAdapter
from lumenis.system.collector.adapters.facebook import FacebookAdapter


@pytest.mark.parametrize("reason", [
    "SEARCH_CARDS_NOT_OBSERVED", "SEARCH_CARDS_WITHOUT_POST_OBSERVATIONS",
])
def test_facebook_retains_exact_safe_search_failure(reason):
    error = f"PROVIDER_UNAVAILABLE: {reason}"
    observation = FacebookAdapter._safe_failure_observation(error)
    assert observation == {"state": "SEARCH_FAILED", "reason": reason}
    response = SimpleNamespace(success=False, notes=[], error=error, raw_count=0, duration_seconds=0)
    result = FacebookAdapter(backend=SimpleNamespace(search=lambda *args, **kwargs: response)).search("原始任务词")
    assert result.status == CollectionStatus.COLLECT_ERROR
    assert result.metadata["detail"]["search_failure"] == observation
    assert result.metadata["detail"]["body_completeness"] == "NOT_OBSERVED"


def test_facebook_does_not_copy_unknown_failure_text():
    observation = FacebookAdapter._safe_failure_observation("PROVIDER_UNAVAILABLE: private-session-value")
    assert observation == {"state": "PROVIDER_UNAVAILABLE", "reason": None}


@pytest.mark.parametrize("error", ["PROVIDER_UNAVAILABLE: TIMEOUT", "PROVIDER_UNAVAILABLE: WORKER_DISCONNECTED"])
def test_facebook_actual_provider_failure_keeps_provider_state(error):
    response = SimpleNamespace(success=False, notes=[], error=error, raw_count=0, duration_seconds=0)
    result = FacebookAdapter(backend=SimpleNamespace(search=lambda *args, **kwargs: response)).search("原始任务词")
    assert result.status == CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.metadata["detail"]["body_completeness"] == "NOT_OBSERVED"


def test_facebook_verified_success_empty_remains_no_results():
    response = SimpleNamespace(success=True, notes=[], error="", raw_count=0, duration_seconds=0)
    result = FacebookAdapter(backend=SimpleNamespace(search=lambda *args, **kwargs: response)).search("原始任务词")
    assert result.status == CollectionStatus.NO_NEW_DATA
    assert result.metadata["detail"]["body_completeness"] == "NO_RESULTS"


@pytest.mark.parametrize(("error", "reason"), [
    ("DOUYIN_CAPTCHA_REQUIRED: 安全验证", "VERIFICATION_REQUIRED"),
    ("抖音登录态失效", "SESSION_UNAVAILABLE"),
    ("DOUYIN_RATE_LIMITED: 访问频繁", "RATE_LIMITED"),
    ("DOUYIN_NETWORK_UNAVAILABLE", "PROVIDER_UNAVAILABLE"),
    ("抖音搜索未返回可验证的结构化结果，不能确认为无新内容", "SEARCH_FAILED"),
])
def test_douyin_failed_search_is_unobserved_and_keeps_recovery_reason(error, reason):
    response = SimpleNamespace(success=False, notes=[], error=error, raw_count=0, duration_seconds=0)
    detail_calls = []
    backend = SimpleNamespace(
        search=lambda *args, **kwargs: response,
        detail=lambda **kwargs: detail_calls.append(kwargs),
    )
    adapter = DouyinAdapter(backend=backend)
    expected_status = adapter._v4_status_to_main(False, [], error)
    result = adapter.search("原始任务词")
    assert result.status == expected_status
    assert result.status != CollectionStatus.NO_NEW_DATA
    assert result.metadata["detail"]["body_completeness"] == "NOT_OBSERVED"
    assert result.metadata["detail"]["search_state"] == expected_status.value
    assert result.metadata["detail"]["search_failure_state"] == reason
    assert result.metadata["error_type"] == reason
    assert detail_calls == []


def test_douyin_verified_success_empty_remains_no_results():
    response = SimpleNamespace(success=True, notes=[], error="", raw_count=0, duration_seconds=0)
    adapter = DouyinAdapter(backend=SimpleNamespace(search=lambda *args, **kwargs: response))
    result = adapter.search("原始任务词")
    assert result.status == CollectionStatus.NO_NEW_DATA
    assert result.metadata["detail"]["body_completeness"] == "NO_RESULTS"
    assert result.metadata["detail"]["search_failure_state"] is None
    assert "error_type" not in result.metadata

# -*- coding: utf-8 -*-
"""
Collector Guard 集成层单元测试（旁路模式，不启动真实采集）
"""
import sys, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import collector_guard_integration as cgi


class TestCollectorGuardIntegration:

    def setup_method(self):
        cgi.reset()

    def teardown_method(self):
        cgi.reset()

    def test_init_guards_creates_all_platforms(self):
        cgi.init_guards()
        status = cgi.get_all_status()
        assert "xhs" in status
        assert "douyin" in status
        assert "weibo" in status
        assert "bilibili" in status
        assert "instagram" in status
        assert "zhihu" in status

    def test_init_guards_idempotent(self):
        cgi.init_guards()
        g1 = cgi.get_guard("xhs")
        cgi.init_guards()  # 重复调用不重建
        g2 = cgi.get_guard("xhs")
        assert g1 is g2

    def test_get_guard_returns_guard(self):
        guard = cgi.get_guard("xhs")
        assert guard is not None
        assert guard.platform == "xhs"
        assert hasattr(guard, "run")
        assert hasattr(guard, "status")

    def test_get_guard_unknown_platform_returns_none(self):
        assert cgi.get_guard("nonexistent") is None

    def test_get_all_status_contains_metrics(self):
        status = cgi.get_all_status()
        for platform, st in status.items():
            assert "enabled" in st
            assert "limiter" in st
            assert "metrics" in st

    def test_is_enabled_returns_bool(self):
        assert isinstance(cgi.is_enabled(), bool)

    def test_guard_run_passthrough_when_disabled(self):
        """guard disabled 时直通，仅异常兜底。"""
        from collector_guard import CollectorGuard
        guard = CollectorGuard("test", enabled=False)
        result = guard.run(lambda: {"notes": [{"note_id": "1"}]}, "keyword")
        assert result.ok is True
        assert len(result.notes) == 1

    def test_guard_run_catches_exception(self):
        """guard 捕获采集异常，不向上拖垮系统。"""
        from collector_guard import CollectorGuard
        guard = CollectorGuard("test", enabled=False)
        result = guard.run(lambda: (_ for _ in ()).throw(RuntimeError("boom")), "keyword")
        assert result.ok is False
        assert "boom" in result.detail

    def test_status_api_importable(self):
        """app.py 中的 API 路由可导入（不实际启动 Flask）。"""
        # 验证集成层可被 app.py 的路由函数调用
        from collector_guard_integration import get_all_status, is_enabled
        status = get_all_status()
        assert isinstance(status, dict)
        assert isinstance(is_enabled(), bool)

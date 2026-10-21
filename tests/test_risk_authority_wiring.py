# -*- coding: utf-8 -*-
"""P1-4 风险权威归属锁定测试（不重复 test_risk_engine 已覆盖的评分器内部行为）。

运行时事实（2026-09-02 审计）：
- 现役采集风险/熔断 = CollectorGuard（state 七态 + analyzer + AdaptiveRateLimiter），采集链默认启用；
- collector_guard/risk_engine.py 的 RiskEngine(0-100 连续分) 已实现、已被 test_risk_engine 覆盖，
  但【未被 CollectorGuard 实例化、未接管现役熔断】，是备用增强件；
- 根 risk_engine.py 是历史命名兼容层，只做转发。
本测试把上述归属钉死，防止未来误改 RiskEngine 就以为影响了生产熔断，或反向把现役状态机替换掉。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.system.collector.guard import CollectorGuard, AdaptiveRateLimiter  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_active_guard_uses_state_machine_not_scoring_engine():
    g = CollectorGuard(platform="xhs", enabled=True)
    # 现役四件套齐备
    assert isinstance(g.limiter, AdaptiveRateLimiter)
    assert g.analyzer is not None and g.metrics is not None and g.checkpoint is not None
    # 关键：现役 Guard 不持有/不实例化连续分 RiskEngine
    assert not hasattr(g, "risk_engine")
    # guard.py 源码层也不导入 risk_engine（两套机制独立，避免误耦合）
    guard_src = open(os.path.join(ROOT, "lumenis", "system", "collector", "guard", "guard.py"), encoding="utf-8").read()
    assert "risk_engine" not in guard_src and "RiskEngine" not in guard_src


def test_compat_root_risk_engine_is_pure_forward(monkeypatch):
    import risk_engine as compat
    import subject_rules

    # Explicit legacy focus; missing scope must still reject.
    from subject_context import brand_scope
    with brand_scope("guangzhou_taikoo_hui", product_id="CTH"):
        clause_a, vals_a = compat._subject_sql_and_values("n")
        clause_b, vals_b = subject_rules.subject_sql_and_values("n")
    assert clause_a == clause_b and vals_a == vals_b

    # build_daily_report 必须转发 daily_report.generate_daily_digest（不自己算）
    sentinel = {"ok": "forwarded"}
    monkeypatch.setattr(compat.daily_report, "generate_daily_digest", lambda d=None: sentinel)
    assert compat.build_daily_report("2026-09-01") is sentinel


def test_scoring_engine_module_independent_from_active_state_machine():
    # 备用评分器模块可独立导入，且不反向依赖现役 guard
    re_src = open(os.path.join(ROOT, "lumenis", "system", "collector", "guard", "risk_engine.py"), encoding="utf-8").read()
    assert "from .guard" not in re_src and "import guard" not in re_src
    from lumenis.system.collector.guard.risk_engine import RiskEngine
    r = RiskEngine()
    snap = r.snapshot()
    assert "risk_score" in snap and "should_stop_request" in snap


def test_legacy_subject_forward_rejects_absent_context(monkeypatch):
    import pytest
    import risk_engine as compat
    import subject_context
    monkeypatch.setattr(subject_context, 'get_thread_context', lambda: None)
    with pytest.raises(ValueError, match='LEGACY_SUBJECT_SCOPE_REQUIRED'):
        compat._subject_sql_and_values('n')

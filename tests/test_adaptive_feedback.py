# -*- coding: utf-8 -*-
"""adaptive_engine 采集结果回写闭环 + 动态冻结时长测试（纯逻辑、不触网、不连浏览器）。"""
import os
import sys
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _fresh_bridge(monkeypatch):
    """每次重新 import bridge，避免全局单例污染；旁路真实网络/浏览器。"""
    import xhs_cookie_bridge as xcb
    importlib.reload(xcb)
    return xcb


def test_adaptive_cool_minutes_maps_strategy(monkeypatch):
    """冷却时长随策略递增：normal60 < cautious90 < conservative180 < suspended360。"""
    xcb = _fresh_bridge(monkeypatch)
    import adaptive_engine as ae
    cases = {'normal': 60, 'cautious': 90, 'conservative': 180, 'suspended': 360}
    for strat, expected in cases.items():
        monkeypatch.setattr(ae.adaptive_engine, 'get_current_strategy', lambda s=strat: s)
        assert xcb._adaptive_cool_minutes() == expected, strat


def test_adaptive_cool_minutes_fail_open(monkeypatch):
    """adaptive_engine 异常时回退 60 分钟，绝不因新组件卡住熔断。"""
    xcb = _fresh_bridge(monkeypatch)
    import adaptive_engine as ae

    def _boom():
        raise RuntimeError('engine down')
    monkeypatch.setattr(ae.adaptive_engine, 'get_current_strategy', _boom)
    assert xcb._adaptive_cool_minutes() == 60


def test_report_result_drives_strategy_escalation(monkeypatch):
    """连续失败（风控错误）应驱动策略从 normal 升级，成功后可回落。"""
    import adaptive_engine as ae
    importlib.reload(ae)
    eng = ae.adaptive_engine
    eng.reset_to_normal()
    assert eng.get_current_strategy() == 'normal'
    # 连续多次失败 + 风控关键词，风险分应累积升级
    for _ in range(6):
        eng.report_collection_result(False, 0, duration=12.0, error='验证码 captcha 风控')
    strat_after_fail = eng.get_current_strategy()
    assert strat_after_fail in ('cautious', 'conservative', 'suspended'), strat_after_fail
    # 冷却时长映射与升级后策略一致（不会比 normal 更短）
    xcb = _fresh_bridge(monkeypatch)
    monkeypatch.setattr(ae.adaptive_engine, 'get_current_strategy', lambda: strat_after_fail)
    assert xcb._adaptive_cool_minutes() >= 90


def test_report_result_success_keeps_normal(monkeypatch):
    """连续成功且无风控应保持 normal。"""
    import adaptive_engine as ae
    importlib.reload(ae)
    eng = ae.adaptive_engine
    eng.reset_to_normal()
    for _ in range(6):
        eng.report_collection_result(True, notes_count=15, duration=10.0, error=None)
    assert eng.get_current_strategy() == 'normal'

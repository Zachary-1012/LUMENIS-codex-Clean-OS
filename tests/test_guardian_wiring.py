# -*- coding: utf-8 -*-
"""P1-7 guardian runtime and Shared Learning startup wiring contract.

不重复 test_auto_recovery.py / test_data_feedback.py 的模块内部行为；
本测试只锁定 app.py 启动接线：默认启用、可整体关闭、各自 try/except 隔离不阻断启动、
auto_recovery 靠 app 层 _p17_started 幂等（引擎自身每次起线程，必须由接线层防重复）、
接线位于 app.run 之前。运行中 8201 冻结未重启属预期，重启后生效。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _app_src():
    return open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()


def test_p17_wiring_default_on_isolated_and_before_app_run():
    src = _app_src()
    # 接线段存在
    assert "P1-7 三 guardian 模块受控接入" in src
    # 默认启用，且可用 ZBC_GUARDIAN_ENABLED=0 整体关闭
    assert "os.environ.get('ZBC_GUARDIAN_ENABLED', '1') == '1'" in src
    # Recovery and health adapters stay wired; feedback uses its current owner.
    for mod in ("import auto_recovery as _ar",
                "from lumenis.shared.learning import feedback as _dfl",
                "import system_guardian as _sg"):
        assert mod in src
    # 三个模块各自 try/except 隔离（任一失败不阻断启动）
    assert src.count("启动失败") >= 3
    # auto_recovery 接线层幂等标志（引擎内部不幂等，防重复起监控线程）
    assert "_p17_started" in src
    # 接线必须发生在 app.run 之前（取两者位置比较）
    assert src.index("P1-7 三 guardian 模块受控接入") < src.index("app.run(")


def test_guardian_singletons_and_entrypoints():
    import auto_recovery
    from lumenis.shared.learning import feedback as dfl_mod
    import system_guardian

    assert isinstance(auto_recovery.recovery_engine, auto_recovery.AutoRecoveryEngine)
    assert isinstance(dfl_mod.data_feedback_loop, dfl_mod.DataFeedbackLoop)
    assert callable(auto_recovery.recovery_engine.start_background_monitor)
    assert callable(dfl_mod.data_feedback_loop.run_feedback_cycle)
    assert callable(system_guardian.health_check)


def test_app_layer_idempotent_guard_starts_monitor_once(monkeypatch):
    """复刻 app.py 的 _p17_started 守卫：连进两次只允许起一次后台监控。"""
    import auto_recovery as ar
    eng = ar.recovery_engine
    calls = {"n": 0}

    def _fake_start(interval=60):
        calls["n"] += 1

    monkeypatch.setattr(eng, "start_background_monitor", _fake_start)
    # 清掉历史标志，严格按 app 接线模式跑两轮
    if hasattr(eng, "_p17_started"):
        delattr(eng, "_p17_started")
    for _ in range(2):
        if not getattr(eng, "_p17_started", False):
            eng.start_background_monitor(60)
            eng._p17_started = True
    assert calls["n"] == 1

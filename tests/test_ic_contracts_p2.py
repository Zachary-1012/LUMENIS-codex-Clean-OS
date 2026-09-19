# -*- coding: utf-8 -*-
"""序境-Core · IC-035/044/048 Contract 测试。

覆盖：
- IC-035：当前安全边界保留五层控制模型，不把文档存在当作实现证明
- IC-044：耸动/合成内容风险信号接入 alert_engine（向后兼容 + 危机期收紧 + 独立扫描）
- IC-048：可视化质量门检查清单（check() 结果结构化 + 必填项判定）

强制 DB：module 级 autouse fixture 设置 ZBC_DB_PATH=临时库 + init_alert_tables 建全 schema。
"""
import os
import sqlite3
import sys
import tempfile

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
if BASE not in sys.path:
    sys.path.insert(0, BASE)


def _conn():
    """用 alert_engine._conn() 拿连接（设置 row_factory=Row）。"""
    import alert_engine
    return alert_engine._conn()

_TMPDB = os.path.join(tempfile.gettempdir(), "zbc_test_ic035_044_048.db")


@pytest.fixture(autouse=True, scope="module")
def _db():
    """模块级：强制临时库 + 建全 schema，防污染。"""
    if os.path.exists(_TMPDB):
        os.remove(_TMPDB)
    os.environ["ZBC_DB_PATH"] = _TMPDB
    import database
    database.init_db()
    import alert_engine
    alert_engine.init_alert_tables()
    yield
    os.environ.pop("ZBC_DB_PATH", None)


# ============ IC-035 · 当前安全边界 ============
class TestIC035:
    def test_current_boundary_covers_five_layers(self):
        path = os.path.join(BASE, "00-GOVERNANCE", "SECURITY-BOUNDARY-CURRENT.md")
        assert os.path.exists(path), "当前安全边界必须存在"
        with open(path, encoding="utf-8") as source:
            text = source.read()
        for layer in ["输入护栏", "身份权限", "执行沙箱", "输出护栏", "可观测审计"]:
            assert layer in text, f"当前安全边界缺少[{layer}]"
        assert "does not claim" in text, "文档不得冒充实现验证证据"


# ============ IC-044 · 耸动/合成内容风险信号 ============
class TestIC044:
    def test_backward_compat(self):
        """不传 synthetic_signals / crisis_mode 时行为与 IC-020 一致（无新增告警）。"""
        import alert_engine
        r = alert_engine.evaluate_alerts(notes=[], conn=_conn())
        assert r["enabled"] is True
        assert isinstance(r["alerts"], list)
        assert r["alerts"] == []

    def test_synthetic_block_creates_high_alert(self):
        """耸动/合成内容 BLOCK 信号 → high 告警。"""
        import alert_engine
        c = _conn()
        r = alert_engine.evaluate_alerts(
            notes=[], synthetic_signals=[
                {"id": "S1", "type": "ai_generated", "evidence": "AI 生成标记"},
                {"id": "S2", "type": "synthetic", "evidence": "深度合成特征"},
            ], conn=c)
        types = [a["type"] for a in r["alerts"]]
        assert "synthetic_content" in types, f"应生成耸动/合成告警，got {types}"
        assert any(a["severity"] == "high" for a in r["alerts"])
        c.close()

    def test_suspicious_signal_medium(self):
        """疑似信号（old_republish/emotion_excitation）→ medium。"""
        import alert_engine
        c = _conn()
        r = alert_engine.evaluate_alerts(
            notes=[], synthetic_signals=[
                {"id": "S3", "type": "old_republish", "evidence": "旧素材重发"},
            ], conn=c)
        assert any(a["severity"] == "medium" for a in r["alerts"])
        c.close()

    def test_synthetic_risk_scan_categories(self):
        """synthetic_risk_scan 分类正确（blocked/suspicious/clean）。"""
        import alert_engine
        r = alert_engine.synthetic_risk_scan([
            {"id": "a", "type": "ai_generated"},
            {"id": "b", "type": "emotion_excitation"},
            {"id": "c", "type": "normal_post"},
        ])
        assert [x["id"] for x in r["blocked"]] == ["a"]
        assert [x["id"] for x in r["suspicious"]] == ["b"]
        assert [x["id"] for x in r["clean"]] == ["c"]

    def test_crisis_mode_tightens_threshold(self):
        """危机期收紧：risk_index 达收紧阈值（< 常规 high 阈值）触发 high。"""
        import alert_engine
        c = _conn()
        # 常规 high=70，收紧系数 0.8 → 收紧阈值 56；risk_index=60 常规不触发，危机期触发
        r = alert_engine.evaluate_alerts(notes=[], risk_index=60.0, crisis_mode=True, conn=c)
        assert any(a["severity"] == "high" for a in r["alerts"]), f"危机期应触发收紧告警，got {r['alerts']}"
        c.close()

    def test_crisis_not_false_positive(self):
        """非危机期：risk_index=60 不触发 high（常规阈值 70）。"""
        import alert_engine
        c = _conn()
        r = alert_engine.evaluate_alerts(notes=[], risk_index=60.0, crisis_mode=False, conn=c)
        assert not any(a["severity"] == "high" for a in r["alerts"]), f"非危机期不应触发收紧，got {r['alerts']}"
        c.close()


# ============ IC-048 · 可视化质量门 ============
class TestIC048:
    def test_check_pass(self):
        """全部必填满足 → PASS。"""
        import importlib
        from scripts import visualization_quality_gate as vq
        importlib.reload(vq)
        r = vq.check(vis_id="VIS-TEST-01", question="负面占比趋势？",
                     canonical_source="MET-RISK-01", data_source_note="canonical_metrics")
        assert r["result"] == "PASS"
        assert r["required_pass"] == r["required_total"]

    def test_check_fail_missing_question(self):
        """缺待回答问题 → FAIL。"""
        from scripts import visualization_quality_gate as vq
        r = vq.check(vis_id="VIS-TEST-02", question="",
                     canonical_source="MET-RISK-01", data_source_note="x")
        assert r["result"] == "FAIL"
        assert "VISQ-01" in r["failed_required"]

    def test_check_fail_no_canonical(self):
        """缺 Canonical 来源 → FAIL（VISQ-07 必填）。"""
        from scripts import visualization_quality_gate as vq
        r = vq.check(vis_id="VIS-TEST-03", question="趋势？",
                     canonical_source="", data_source_note="x")
        assert r["result"] == "FAIL"
        assert "VISQ-07" in r["failed_required"]

    def test_optional_fail_not_block(self):
        """仅建议项失败不阻塞 PASS。"""
        from scripts import visualization_quality_gate as vq
        r = vq.check(vis_id="VIS-TEST-04", question="趋势？",
                     canonical_source="MET-RISK-01", data_source_note="x",
                     mobile_ok=False, motion_ok=False)
        assert r["result"] == "PASS"
        assert set(r["failed_optional"]) == {"VISQ-09", "VISQ-10"}

    def test_checklist_md_has_10_items(self):
        """质量门清单含全部 10 项检查。"""
        from scripts import visualization_quality_gate as vq
        md = vq.checklist_md()
        assert "VISQ-10" in md
        assert md.count("| VISQ-") == 10

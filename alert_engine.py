# -*- coding: utf-8 -*-
"""
序境-Core · IC-020 舆情危机告警引擎（P1 落地）
================================================
契约依据：序境/01-PRODUCT/PRODUCTION_CANDIDATE_CONTRACTS_20260904.md §一（IC-020）
目标：舆情危机告警阈值可配置 + 告警状态机（DETECTED→NOTIFIED→ESCALATED→RESOLVED），
      不伪造"已告警"状态，全程可审计。

红线遵守：
- 只消费 canonical_metrics（MET-RISK-01/03 已固定口径），不重复计算业务指标
- 不修改 calculate_risk_index / assess_risk 现有逻辑（防数字真相漂移）
- 阈值默认值静态落地并登记 Evidence；调优必须基于标注样本（本期不做）
- 独立开关 ALERT_ENGINE_ENABLED，异常可整体禁用回退到无告警基线

表结构（增量，独立新表，不碰既有表）：
- alert_configs     告警阈值配置（可配，K-V）
- alert_records     告警记录（状态机留痕）
"""
import json
import math
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from lumenis.shared.database import get_repository, main_db_path

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = main_db_path()

# ============== 告警状态机（IC-020 Contract §1.4） ==============
# 状态转移表：只允许如下转移
STATE_TRANSITIONS = {
    "DETECTED": {"NOTIFIED", "ESCALATED", "RESOLVED", "REJECTED"},   # 检测到→通知/升级/解决/人工否决
    "NOTIFIED": {"ESCALATED", "RESOLVED", "REJECTED"},               # 已通知→升级/解决/否决
    "ESCALATED": {"RESOLVED", "REJECTED"},                            # 已升级→解决/否决
    "RESOLVED": set(),                                                # 终态
    "REJECTED": set(),                                                # 终态（人工判定无需处置）
}
VALID_STATES = set(STATE_TRANSITIONS)

# ============== 默认阈值（静态配置，登记 Evidence；调优须基于标注样本） ==============
DEFAULT_ALERT_CONFIG = {
    "enabled": True,            # 总开关
    "risk_index_high": 70.0,    # 风险指数≥70 → high 告警（对齐 _generate_trend_alerts 既有口径）
    "risk_index_med": 50.0,     # 风险指数≥50 → medium
    "neg_ratio_high": 0.40,     # 负面占比≥40% → high（对齐既有 neg_pct>40）
    "neg_ratio_med": 0.25,      # 负面占比≥25% → medium
    "high_risk_count_high": 3,  # 高风险事件≥3 → high（对齐既有 risk>=3）
    "high_risk_count_med": 1,   # 高风险事件≥1 → medium
    "brand_health_high": 60.0,  # 品牌健康<60 → high（对齐既有 health<60）
    "brand_health_med": 75.0,   # 品牌健康<75 → medium
    "mention_surge_pct": None,  # 无经验证业务默认值；仅显式人工配置的旧启发式可用
    "sentiment_drop_pt": 20.0,  # 情绪得分骤降≥20pt
    "cooldown_hours": 6,        # 同类告警冷却时间（防刷屏）
    "crisis_threshold_factor": 0.8,  # IC-044 危机期阈值收紧系数（<1 表示收紧；对既有阈值×系数）
}


def _conn() -> sqlite3.Connection:
    """Canonical Shared Database repository connection."""
    return get_repository().connect(timeout=30)


def init_alert_tables(conn: Optional[sqlite3.Connection] = None) -> None:
    """增量建表（幂等）。"""
    own = conn is None
    c = conn or _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS alert_configs (
            key TEXT PRIMARY KEY,
            value REAL DEFAULT 0,
            value_text TEXT DEFAULT '',
            source TEXT DEFAULT 'DEFAULT',
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS alert_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_key TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            metric_key TEXT DEFAULT '',
            metric_value TEXT DEFAULT '',
            message TEXT DEFAULT '',
            state TEXT DEFAULT 'DETECTED',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            audit_log TEXT DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_alert_records_state ON alert_records(state);
        CREATE INDEX IF NOT EXISTS idx_alert_records_created ON alert_records(created_at);
        """)
        c.commit()
        _seed_default_config(c)
    finally:
        if own:
            c.close()


def _seed_default_config(conn: sqlite3.Connection) -> None:
    """默认阈值落库（仅当 key 不存在时写入，不覆盖用户配置）。"""
    cur = conn.execute("SELECT COUNT(*) AS n FROM alert_configs")
    if cur.fetchone()["n"] > 0:
        return
    for k, v in DEFAULT_ALERT_CONFIG.items():
        if isinstance(v, bool):
            conn.execute("INSERT OR IGNORE INTO alert_configs(key, value, value_text, source) VALUES(?,?,?,?)",
                         (k, 1 if v else 0, str(v), "DEFAULT-IC020"))
        elif isinstance(v, (int, float)):
            conn.execute("INSERT OR IGNORE INTO alert_configs(key, value, value_text, source) VALUES(?,?,?,?)",
                         (k, float(v), str(v), "DEFAULT-IC020"))
    conn.commit()


def _cfg_bool(conn: sqlite3.Connection, key: str, default: bool = True) -> bool:
    r = conn.execute("SELECT value FROM alert_configs WHERE key=?", (key,)).fetchone()
    if r is None:
        return default
    return bool(r["value"])


def _cfg_num(conn: sqlite3.Connection, key: str, default: float) -> float:
    r = conn.execute("SELECT value FROM alert_configs WHERE key=?", (key,)).fetchone()
    if r is None:
        return default
    try:
        return float(r["value"])
    except Exception:
        return default



def _mention_surge_rule(conn):
    """Legacy explicit operator threshold, never a model or default business rule."""
    row = conn.execute("SELECT value, source, updated_at FROM alert_configs WHERE key=?",
                       ("mention_surge_pct",)).fetchone()
    result = {"method": "legacy_heuristic", "state": "CONFIGURATION_REQUIRED",
              "threshold_pct": None, "source": None, "updated_at": None,
              "business_validation": "NOT_VERIFIED",
              "scope_binding": "UNVERIFIED_LEGACY_INPUT", "window": None}
    if row is None:
        return result
    result.update(source=row["source"], updated_at=row["updated_at"])
    # Historical DEFAULT-IC020=200 rows remain untouched but are not approval.
    if not isinstance(row["source"], str) or not row["source"].strip() or row["source"].startswith("DEFAULT"):
        return result
    try:
        value = float(row["value"])
    except (TypeError, ValueError, OverflowError):
        return result
    if not math.isfinite(value) or value <= 0:
        return result
    result.update(state="CONFIGURED_LEGACY_HEURISTIC", threshold_pct=value)
    return result


def read_cth_temporal_alerts(connection, *, start_date, end_date, authorize):
    """Existing Alert Owner consumes an authorized native-time read, without writes.

    Statistical readiness is not an approved business alert policy. Until an
    existing scoped rule/approval owner supplies that policy, expose the missing
    configuration and never invent a severity, cooldown, notification or receipt.
    No caller-supplied series, snapshot or claimed PASS is accepted here.
    """
    from trend_api import read_cth_temporal_metrics
    result = read_cth_temporal_metrics(connection, start_date=start_date,
                                       end_date=end_date, authorize=authorize)
    if authorize() != result["binding"]:
        raise PermissionError("CTH alert read scope changed after analysis")
    trend = result.get("statistics", {}).get("trend", {
        "state": "UNAVAILABLE", "reason": result.get("code", "SOURCE_ANALYSIS_UNAVAILABLE")})
    result["alert_evaluation"] = {
        "state": "CONFIGURATION_REQUIRED", "reason": "APPROVED_SCOPED_BUSINESS_RULE_REQUIRED",
        "alerts": [], "write_state": "NOT_PERFORMED", "notification_state": "NOT_PERFORMED",
        "method": trend.get("method"), "model_state": trend["state"],
        "model_reason": trend.get("reason"),
        "monitoring_state": trend.get("monitoring", {}).get("state", "NOT_READY"),
        "business_validation": "NOT_VERIFIED",
        "context": {"binding": result["binding"], "window": result["window"],
                    "source": result["source"], "snapshot_sha256": result["snapshot_sha256"],
                    "recipe": result["recipe"]},
        "rule": None, "threshold": None,
        "cooldown": {"state": "NOT_APPLICABLE", "reason": "NO_COMMITTED_MODEL_ALERT"},
        "limitations": ["Retrospective change points are not future alerts.",
                        "Control-chart defaults are not calibrated business thresholds.",
                        "Read authorization does not authorize alert writes or notifications."],
    }
    return result


def is_enabled(conn: Optional[sqlite3.Connection] = None) -> bool:
    if conn is None:
        init_alert_tables()
    own = conn is None
    c = conn or _conn()
    try:
        return _cfg_bool(c, "enabled", True)
    finally:
        if own:
            c.close()


def get_config(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """返回当前生效配置（含默认值兜底，懒初始化）。"""
    if conn is None:
        init_alert_tables()
    own = conn is None
    c = conn or _conn()
    try:
        cfg = dict(DEFAULT_ALERT_CONFIG)
        for r in c.execute("SELECT key, value, value_text FROM alert_configs"):
            if r["key"] == "enabled":
                cfg["enabled"] = bool(r["value"])
            elif r["key"] != "mention_surge_pct":
                cfg[r["key"]] = r["value"]
        cfg["mention_surge_pct"] = _mention_surge_rule(c)["threshold_pct"]
        return cfg
    finally:
        if own:
            c.close()


def set_config(updates: Dict[str, Any], source: str = "MANUAL") -> Dict[str, Any]:
    """更新阈值配置（仅允许存在于 DEFAULT 的 key，防注入任意 key）。"""
    c = _conn()
    try:
        for k, v in updates.items():
            if k not in DEFAULT_ALERT_CONFIG:
                continue
            if isinstance(v, bool):
                c.execute("INSERT INTO alert_configs(key, value, value_text, source, updated_at) VALUES(?,?,?,?,datetime('now','localtime')) "
                          "ON CONFLICT(key) DO UPDATE SET value=excluded.value, value_text=excluded.value_text, source=excluded.source, updated_at=excluded.updated_at",
                          (k, 1 if v else 0, str(v), source))
            elif isinstance(v, (int, float)):
                c.execute("INSERT INTO alert_configs(key, value, value_text, source, updated_at) VALUES(?,?,?,?,datetime('now','localtime')) "
                          "ON CONFLICT(key) DO UPDATE SET value=excluded.value, value_text=excluded.value_text, source=excluded.source, updated_at=excluded.updated_at",
                          (k, float(v), str(v), source))
        c.commit()
        return get_config(c)
    finally:
        c.close()


def transition_state(alert_id: int, new_state: str, operator: str = "system",
                     note: str = "", conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """HCG 状态机转移：合法转移才允许，全程留痕。"""
    if new_state not in VALID_STATES:
        raise ValueError(f"非法告警状态: {new_state}")
    own = conn is None
    c = conn or _conn()
    try:
        row = c.execute("SELECT * FROM alert_records WHERE id=?", (alert_id,)).fetchone()
        if row is None:
            raise LookupError(f"告警记录不存在: {alert_id}")
        cur_state = row["state"]
        if new_state not in STATE_TRANSITIONS.get(cur_state, set()):
            raise ValueError(f"非法状态转移 {cur_state} -> {new_state}（状态机锁定）")
        audit = json.loads(row["audit_log"] or "[]")
        audit.append({
            "from": cur_state, "to": new_state, "operator": operator,
            "note": note, "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        c.execute("UPDATE alert_records SET state=?, updated_at=datetime('now','localtime'), audit_log=? WHERE id=?",
                  (new_state, json.dumps(audit, ensure_ascii=False), alert_id))
        c.commit()
        return dict(c.execute("SELECT * FROM alert_records WHERE id=?", (alert_id,)).fetchone())
    finally:
        if own:
            c.close()


def _record_alert(c: sqlite3.Connection, alert_key: str, alert_type: str, severity: str,
                  metric_key: str, metric_value: str, message: str) -> Optional[int]:
    """写入告警记录（含冷却检查）。返回告警 id；冷却期内返回 None。"""
    cooldown_h = _cfg_num(c, "cooldown_hours", 6)
    row = c.execute(
        "SELECT id, created_at FROM alert_records WHERE alert_key=? AND state IN ('DETECTED','NOTIFIED','ESCALATED') "
        "ORDER BY created_at DESC LIMIT 1", (alert_key,)).fetchone()
    if row is not None:
        try:
            created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() - created < timedelta(hours=cooldown_h):
                return None  # 冷却期内不重复告警
        except Exception:
            pass
    cur = c.execute(
        "INSERT INTO alert_records(alert_key, alert_type, severity, metric_key, metric_value, message, state) "
        "VALUES(?,?,?,?,?,?,'DETECTED')",
        (alert_key, alert_type, severity, metric_key, metric_value, message))
    c.commit()
    return cur.lastrowid


def evaluate_alerts(notes: List[Dict[str, Any]], risk_index: Optional[float] = None,
                    brand_health: Optional[float] = None,
                    event_high_count: Optional[int] = None,
                    mention_baseline: Optional[float] = None,
                    synthetic_signals: Optional[list] = None,
                    crisis_mode: bool = False,
                    conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    核心评估：消费 canonical_metrics（cm.sentiment_count / cm.risk_count）+ 已算好的 risk_index。
    生成告警记录（状态 DETECTED），返回本次评估摘要。
    禁止在此重新计算业务指标——输入必须来自调用方（daily_report / canonical）。
    IC-044（增量）：synthetic_signals 耸动/合成内容风险信号；crisis_mode 危机期阈值收紧（对既有阈值×系数）。
    两者均为可选参数，不传则行为与 IC-020 完全一致（向后兼容）。
    """
    own = conn is None
    c = conn or _conn()
    try:
        if not _cfg_bool(c, "enabled", True):
            return {"enabled": False, "alerts": [], "message": "告警引擎已关闭（ALERT_ENGINE_ENABLED=false）"}

        import canonical_metrics as cm
        sent = cm.sentiment_count(notes)
        risk = cm.risk_count(notes)
        total = len(notes)
        # MET-NEG-RATIO：分母为 known(pos+neu+neg)，不含 unknown；分母为 0 返回 None（不可算），
        # 严禁用 or 0.0 把 UNKNOWN 伪装成 0（Phase 6 审计修复）。
        neg_ratio = cm.neg_ratio(sent)
        high_count = risk.get("high", 0)
        critical_count = risk.get("critical", 0)  # 方案甲：critical 独立桶，不并入 high
        med_count = risk.get("medium", 0)

        # 阈值
        ri_h = _cfg_num(c, "risk_index_high", 70.0)
        ri_m = _cfg_num(c, "risk_index_med", 50.0)
        nr_h = _cfg_num(c, "neg_ratio_high", 0.40)
        nr_m = _cfg_num(c, "neg_ratio_med", 0.25)
        hrc_h = _cfg_num(c, "high_risk_count_high", 3)
        hrc_m = _cfg_num(c, "high_risk_count_med", 1)
        bh_h = _cfg_num(c, "brand_health_high", 60.0)
        bh_m = _cfg_num(c, "brand_health_med", 75.0)
        surge_rule = _mention_surge_rule(c)
        surge = surge_rule["threshold_pct"]

        alerts = []
        if risk_index is not None:
            if risk_index >= ri_h:
                aid = _record_alert(c, "risk_index", "risk_index", "high", "risk_index",
                                    f"{risk_index}", f"风险指数 {risk_index} 达危急阈值（≥{ri_h}），建议立即人工介入")
                if aid: alerts.append({"id": aid, "type": "risk_index", "severity": "high", "metric": f"risk_index={risk_index}"})
            elif risk_index >= ri_m:
                aid = _record_alert(c, "risk_index", "risk_index", "medium", "risk_index",
                                    f"{risk_index}", f"风险指数 {risk_index} 达偏高阈值（≥{ri_m}），建议加强监控")
                if aid: alerts.append({"id": aid, "type": "risk_index", "severity": "medium", "metric": f"risk_index={risk_index}"})

        # neg_ratio 为 None 表示分母为 0（无已知情感数据），不可算→跳过负面占比告警，
        # 绝不把 UNKNOWN 当 0 触发或不触发告警（Phase 6 审计修复）。
        if neg_ratio is not None:
            if neg_ratio >= nr_h:
                aid = _record_alert(c, "neg_ratio", "negative_surge", "high", "negative_pct",
                                    f"{neg_ratio:.2%}", f"负面占比 {neg_ratio:.2%} 超警戒线（≥{nr_h:.0%}），需立即关注来源")
                if aid: alerts.append({"id": aid, "type": "negative_surge", "severity": "high", "metric": f"negative_pct={neg_ratio:.2%}"})
            elif neg_ratio >= nr_m:
                aid = _record_alert(c, "neg_ratio", "negative_elevated", "medium", "negative_pct",
                                    f"{neg_ratio:.2%}", f"负面占比 {neg_ratio:.2%} 处偏高区间（≥{nr_m:.0%}），建议跟踪演化")
                if aid: alerts.append({"id": aid, "type": "negative_elevated", "severity": "medium", "metric": f"negative_pct={neg_ratio:.2%}"})

        if event_high_count is not None:
            if event_high_count >= hrc_h:
                aid = _record_alert(c, "high_risk_cluster", "high_risk_cluster", "high", "high_risk_count",
                                    str(event_high_count), f"高风险事件 {event_high_count} 起达集群阈值（≥{hrc_h}），建议启动应急")
                if aid: alerts.append({"id": aid, "type": "high_risk_cluster", "severity": "high", "metric": f"high_risk_count={event_high_count}"})
            elif event_high_count >= hrc_m:
                aid = _record_alert(c, "high_risk_present", "high_risk_present", "medium", "high_risk_count",
                                    str(event_high_count), f"高风险事件 {event_high_count} 起，需持续跟踪处置")
                if aid: alerts.append({"id": aid, "type": "high_risk_present", "severity": "medium", "metric": f"high_risk_count={event_high_count}"})

        if brand_health is not None:
            if brand_health < bh_h:
                aid = _record_alert(c, "brand_health", "brand_health_critical", "high", "brand_health",
                                    f"{brand_health}", f"品牌健康分 {brand_health} 低于警戒线（<{bh_h}），声誉压力较大")
                if aid: alerts.append({"id": aid, "type": "brand_health_critical", "severity": "high", "metric": f"brand_health={brand_health}"})
            elif brand_health < bh_m:
                aid = _record_alert(c, "brand_health", "brand_health_declining", "medium", "brand_health",
                                    f"{brand_health}", f"品牌健康分 {brand_health} 处下行区间（<{bh_m}），建议关注修复")
                if aid: alerts.append({"id": aid, "type": "brand_health_declining", "severity": "medium", "metric": f"brand_health={brand_health}"})

        if surge is not None and type(mention_baseline) in (int, float) and math.isfinite(mention_baseline) and total > 0 and mention_baseline > 0:
            surge_ratio = (total - mention_baseline) / mention_baseline * 100
            if surge_ratio >= surge:
                aid = _record_alert(c, "mention_surge", "mention_surge", "high", "mention_surge_pct",
                                    f"{surge_ratio:.1f}", f"[旧人工阈值启发式，非趋势模型] 提及量环比变化 {surge_ratio:.1f}%（≥{surge}%），需人工核验")
                if aid: alerts.append({"id": aid, "type": "mention_surge", "severity": "high", "metric": f"mention_surge_pct={surge_ratio:.1f}"})

        # IC-044 耸动/合成内容风险信号（危机期联动；代理信号，明确标注，不编造平台原生能力）
        if synthetic_signals:
            _syn = synthetic_risk_scan(synthetic_signals)
            if _syn["blocked"]:
                for sig in _syn["blocked"]:
                    _key = f"synthetic_blk_{sig.get('id', '') or sig.get('type', 'x')}"
                    aid = _record_alert(c, _key, "synthetic_content_risk", "high", "synthetic_signal",
                                        sig.get("id", ""), f"耸动/合成内容风险：{sig.get('reason', '')}（建议官方源核验+分级响应）")
                    if aid: alerts.append({"id": aid, "type": "synthetic_content", "severity": "high",
                                           "metric": f"synthetic_signal={sig.get('id', '')}"})
            if _syn["suspicious"]:
                for sig in _syn["suspicious"]:
                    _key = f"synthetic_sus_{sig.get('id', '') or sig.get('type', 'x')}"
                    aid = _record_alert(c, _key, "synthetic_content_suspicious", "medium", "synthetic_signal",
                                        sig.get("id", ""), f"耸动/合成内容疑似：{sig.get('reason', '')}（建议关注）")
                    if aid: alerts.append({"id": aid, "type": "synthetic_content", "severity": "medium",
                                           "metric": f"synthetic_signal={sig.get('id', '')}"})

        # IC-044 危机期阈值收紧：已触发任何 high 告警 或 显式 crisis_mode → 后续评估阈值×收紧系数
        crisis_factor = _cfg_num(c, "crisis_threshold_factor", 0.8)
        if crisis_mode or any(a["severity"] == "high" for a in alerts):
            # 危机期收紧：已达收紧 high 阈值则强制升级 high（用独立类型避免与常规告警冷却互斥）
            if risk_index is not None and risk_index >= ri_h * crisis_factor:
                aid = _record_alert(c, "risk_index_crisis", "risk_index_crisis", "high", "risk_index",
                                    f"{risk_index}", f"[危机期收紧] 风险指数 {risk_index} 达收紧阈值（≥{ri_h*crisis_factor:.1f}），原常规阈值{ri_h:.0f}")
                if aid: alerts.append({"id": aid, "type": "risk_index_crisis", "severity": "high", "metric": f"risk_index={risk_index}"})
            if risk_index is not None and risk_index >= ri_m * crisis_factor and risk_index < ri_h * crisis_factor:
                aid = _record_alert(c, "risk_index_crisis_med", "risk_index_crisis_med", "medium", "risk_index",
                                    f"{risk_index}", f"[危机期收紧] 风险指数 {risk_index} 达收紧中阈值（≥{ri_m*crisis_factor:.1f}）")
                if aid: alerts.append({"id": aid, "type": "risk_index_crisis", "severity": "medium", "metric": f"risk_index={risk_index}"})
            if neg_ratio is not None and neg_ratio >= nr_h * crisis_factor:
                aid = _record_alert(c, "negative_crisis", "negative_crisis", "high", "negative_pct",
                                    f"{neg_ratio:.2%}", f"[危机期收紧] 负面占比 {neg_ratio:.2%} 达收紧阈值（≥{nr_h*crisis_factor:.0%}），原常规阈值{nr_h:.0%}")
                if aid: alerts.append({"id": aid, "type": "negative_surge", "severity": "high", "metric": f"negative_pct={neg_ratio:.2%}"})

        return {"enabled": True, "alerts": alerts, "mention_surge_rule": surge_rule,
                "message": f"评估完成，触发 {len(alerts)} 条新告警"}
    finally:
        if own:
            c.close()


def list_records(state: str = "", limit: int = 50, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    if conn is None:
        init_alert_tables()
    own = conn is None
    c = conn or _conn()
    try:
        if state:
            rows = c.execute("SELECT * FROM alert_records WHERE state=? ORDER BY created_at DESC LIMIT ?", (state, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM alert_records ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="序境 IC-020 舆情危机告警引擎")
    ap.add_argument("--init", action="store_true", help="初始化告警配置表")
    ap.add_argument("--config", action="store_true", help="查看当前配置")
    ap.add_argument("--records", action="store_true", help="查看告警记录")
    ap.add_argument("--state", default="", help="按状态过滤记录")
    a = ap.parse_args()
    if a.init or (not a.config and not a.records):
        init_alert_tables()
        print("告警表已初始化（幂等）")
    if a.config:
        print(json.dumps(get_config(), ensure_ascii=False, indent=2))
    if a.records:
        print(json.dumps(list_records(a.state), ensure_ascii=False, indent=2))


# ===== IC-044 · 耸动/合成内容风险信号扫描（代理信号，与 IC-020 告警联动）=====
# 依据：CONTRACT_IC035_044_048_20260904.md §二（Cycle HH）。
# 原则：信号为代理/标记，不编造平台原生能力；处置走官方源核验+分级响应；
#       与 IC-020 共用告警状态机，不新建第二条告警链。


def synthetic_risk_scan(signals: list, config: Optional[dict] = None) -> dict:
    """扫描耸动/合成内容风险信号。

    signals：每条 {id, type, evidence} 结构（type 建议：ai_generated/synthetic/old_republish/
             emotion_excitation/conflict_fact；调用方从内容分析/采集证据传入）。
    config：可选 {block_types:[...], suspicious_types:[...]} 覆盖默认分类。

    返回：{blocked:[...], suspicious:[...], clean:[...], message}
    """
    cfg = config or {}
    block_types = set(cfg.get("block_types") or ["ai_generated", "synthetic"])
    suspicious_types = set(cfg.get("suspicious_types") or ["old_republish", "emotion_excitation", "conflict_fact"])
    blocked, suspicious, clean = [], [], []
    for sig in signals or []:
        if not isinstance(sig, dict):
            continue
        st = (sig.get("type") or "unknown").lower()
        entry = {
            "id": sig.get("id", ""),
            "type": st,
            "evidence": sig.get("evidence", ""),
            "reason": sig.get("reason", f"耸动/合成信号类型[{st}]，建议官方源核验"),
        }
        if st in block_types:
            blocked.append(entry)
        elif st in suspicious_types:
            suspicious.append(entry)
        else:
            clean.append(entry)
    return {
        "blocked": blocked,
        "suspicious": suspicious,
        "clean": clean,
        "message": f"扫描 {len(signals or [])} 条信号：BLOCK {len(blocked)} / SUSPICIOUS {len(suspicious)} / CLEAN {len(clean)}",
    }

# -*- coding: utf-8 -*-
"""
Signal Detector — 主动式信号检测器
====================================
扫描系统状态上下文，基于纯规则生成 Signal。不依赖外部 AI API。

context 可选字段（.get() 安全访问）：
  system_metrics / risk_state / task_progress / data_quality /
  trend_data / performance / better_path

检测维度：ANOMALY / TREND_CHANGE / TASK_BLOCKED / RISK_ESCALATION /
          DATA_MISSING / BETTER_PATH / PERFORMANCE_DEGRADE
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ── 枚举与数据结构 ────────────────────────────────────────────

class SignalType(str, Enum):
    ANOMALY = "anomaly"
    TREND_CHANGE = "trend_change"
    TASK_BLOCKED = "task_blocked"
    RISK_ESCALATION = "risk_escalation"
    DATA_MISSING = "data_missing"
    BETTER_PATH = "better_path"
    PERFORMANCE_DEGRADE = "performance_degrade"


class SignalSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


_SEVERITY_ORDER: Dict[str, int] = {"info": 0, "warning": 1, "critical": 2}


@dataclass
class Signal:
    """主动检测信号，携带证据引用与上下文快照，可解释可审计。"""
    signal_id: str = field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:12]}")
    signal_type: str = ""
    severity: str = SignalSeverity.INFO.value
    source: str = ""
    title: str = ""
    description: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def severity_rank(self) -> int:
        return _SEVERITY_ORDER.get(self.severity, 0)


# ── 默认阈值 ──────────────────────────────────────────────────

_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "cpu_pct_critical": 90.0, "cpu_pct_warning": 75.0,
    "memory_pct_critical": 90.0, "memory_pct_warning": 75.0,
    "error_rate_critical": 0.10, "error_rate_warning": 0.03,
    "latency_ms_critical": 5000.0, "latency_ms_warning": 2000.0,
    "task_stuck_seconds_critical": 600, "task_stuck_seconds_warning": 180,
    "task_retry_critical": 5, "task_retry_warning": 3,
    "risk_escalation_count_critical": 3, "risk_escalation_count_warning": 1,
    "data_null_rate_critical": 0.50, "data_null_rate_warning": 0.20,
    "data_capture_gap_seconds_critical": 3600, "data_capture_gap_seconds_warning": 1800,
    "trend_change_pct_critical": 50.0, "trend_change_pct_warning": 20.0,
    "perf_degrade_latency_ratio_critical": 2.0,
    "perf_degrade_latency_ratio_warning": 1.5,
}


def _merge_thresholds(context: Dict[str, Any]) -> Dict[str, Any]:
    t = dict(_DEFAULT_THRESHOLDS)
    custom = context.get("thresholds")
    if isinstance(custom, dict):
        t.update(custom)
    return t


def _f(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _i(v: Any, d: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return d


# ── SignalDetector ────────────────────────────────────────────

class SignalDetector:
    """信号检测器：扫描系统状态，基于规则生成信号列表。"""

    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        self._custom_thresholds = thresholds or {}

    def detect_signals(self, context: Optional[Dict[str, Any]] = None) -> List[Signal]:
        """主入口：扫描上下文，返回按严重度降序排列的 Signal 列表。"""
        context = context or {}
        th = _merge_thresholds(context)
        if self._custom_thresholds:
            th.update(self._custom_thresholds)

        signals: List[Signal] = []
        signals.extend(self._detect_anomaly(context, th))
        signals.extend(self._detect_risk_escalation(context, th))
        signals.extend(self._detect_task_blocked(context, th))
        signals.extend(self._detect_data_missing(context, th))
        signals.extend(self._detect_trend_change(context, th))
        signals.extend(self._detect_performance_degrade(context, th))
        signals.extend(self._detect_better_path(context, th))
        signals.sort(key=lambda s: s.severity_rank, reverse=True)
        return signals

    # ── 子检测器 ──────────────────────────────────────────────

    def _detect_anomaly(self, ctx: Dict, th: Dict) -> List[Signal]:
        """检测系统指标异常：CPU / 内存 / 错误率 / 延迟。"""
        m = ctx.get("system_metrics")
        if not isinstance(m, dict):
            return []
        sigs: List[Signal] = []
        # (metric_key, label, unit, threshold_key_prefix, fmt)
        checks = [
            ("cpu_pct", "CPU 使用率", "%", "cpu_pct", "{:.1f}"),
            ("memory_pct", "内存使用率", "%", "memory_pct", "{:.1f}"),
            ("error_rate", "错误率", "", "error_rate", "{:.1%}"),
            ("latency_ms", "响应延迟", "ms", "latency_ms", "{:.0f}"),
        ]
        for key, label, unit, prefix, fmt in checks:
            val = _f(m.get(key))
            if val <= 0:
                continue
            crit = th[f"{prefix}_critical"]
            warn = th[f"{prefix}_warning"]
            if val >= crit:
                sev = SignalSeverity.CRITICAL
                word = "异常"
            elif val >= warn:
                sev = SignalSeverity.WARNING
                word = "偏高"
            else:
                continue
            val_str = fmt.format(val)
            sigs.append(self._sig(
                SignalType.ANOMALY, sev,
                source=f"system_metrics.{key}",
                title=f"{label}{word}：{val_str}{unit}",
                description=f"{label} {val_str}{unit} 超过{sev.value}阈值 "
                            f"{fmt.format(crit)}{unit}。",
                evidence_refs=[f"system_metrics.{key}={val}"],
                snapshot={key: val, "threshold": crit},
            ))
        return sigs

    def _detect_risk_escalation(self, ctx: Dict, th: Dict) -> List[Signal]:
        """检测风险升级：等级上升 / 升级次数激增 / 活跃告警偏多。"""
        r = ctx.get("risk_state")
        if not isinstance(r, dict):
            return []
        sigs: List[Signal] = []
        cur = str(r.get("current_level", "")).lower()
        prev = str(r.get("previous_level", "")).lower()
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if cur and prev and cur in order and prev in order:
            if order[cur] > order[prev]:
                sev = (SignalSeverity.CRITICAL
                       if cur == "critical" or order[cur] - order[prev] >= 2
                       else SignalSeverity.WARNING)
                sigs.append(self._sig(
                    SignalType.RISK_ESCALATION, sev,
                    source="risk_state.level",
                    title=f"风险等级升级：{prev} → {cur}",
                    description=f"系统风险等级从 {prev} 升级至 {cur}。",
                    evidence_refs=[f"current={cur}", f"previous={prev}"],
                    snapshot={"current_level": cur, "previous_level": prev},
                ))
        esc = _i(r.get("escalation_count"))
        if esc >= th["risk_escalation_count_critical"]:
            sigs.append(self._sig(
                SignalType.RISK_ESCALATION, SignalSeverity.CRITICAL,
                source="risk_state.escalation_count",
                title=f"风险升级次数激增：{esc} 次",
                description=f"近期风险升级累计 {esc} 次。",
                evidence_refs=[f"escalation_count={esc}"],
                snapshot={"escalation_count": esc},
            ))
        elif esc >= th["risk_escalation_count_warning"]:
            sigs.append(self._sig(
                SignalType.RISK_ESCALATION, SignalSeverity.WARNING,
                source="risk_state.escalation_count",
                title=f"风险升级次数偏多：{esc} 次",
                description=f"近期风险升级累计 {esc} 次。",
                evidence_refs=[f"escalation_count={esc}"],
                snapshot={"escalation_count": esc},
            ))
        alerts = _i(r.get("active_alerts"))
        if alerts >= 5:
            sigs.append(self._sig(
                SignalType.RISK_ESCALATION, SignalSeverity.WARNING,
                source="risk_state.active_alerts",
                title=f"活跃告警数偏多：{alerts} 条",
                description=f"当前活跃告警 {alerts} 条。",
                evidence_refs=[f"active_alerts={alerts}"],
                snapshot={"active_alerts": alerts},
            ))
        return sigs

    def _detect_task_blocked(self, ctx: Dict, th: Dict) -> List[Signal]:
        """检测任务阻塞：卡住超时 / 重试过多。"""
        t = ctx.get("task_progress")
        if not isinstance(t, dict):
            return []
        sigs: List[Signal] = []
        tid = str(t.get("task_id", "unknown"))
        status = str(t.get("status", "")).lower()
        stuck = _i(t.get("stuck_seconds"))
        if stuck > 0 and status not in ("completed", "failed", "cancelled"):
            if stuck >= th["task_stuck_seconds_critical"]:
                sigs.append(self._sig(
                    SignalType.TASK_BLOCKED, SignalSeverity.CRITICAL,
                    source=f"task_progress.{tid}",
                    title=f"任务阻塞超时：{tid}（{stuck}s）",
                    description=f"任务 {tid} 已卡住 {stuck} 秒，状态：{status or 'unknown'}。",
                    evidence_refs=[f"task_id={tid}", f"stuck_seconds={stuck}"],
                    snapshot={"task_id": tid, "stuck_seconds": stuck, "status": status},
                ))
            elif stuck >= th["task_stuck_seconds_warning"]:
                sigs.append(self._sig(
                    SignalType.TASK_BLOCKED, SignalSeverity.WARNING,
                    source=f"task_progress.{tid}",
                    title=f"任务可能阻塞：{tid}（{stuck}s）",
                    description=f"任务 {tid} 已持续 {stuck} 秒无进展。",
                    evidence_refs=[f"task_id={tid}", f"stuck_seconds={stuck}"],
                    snapshot={"task_id": tid, "stuck_seconds": stuck},
                ))
        retries = _i(t.get("retry_count"))
        if retries >= th["task_retry_critical"]:
            sigs.append(self._sig(
                SignalType.TASK_BLOCKED, SignalSeverity.CRITICAL,
                source=f"task_progress.{tid}.retry",
                title=f"任务重试过多：{tid}（{retries} 次）",
                description=f"任务 {tid} 已重试 {retries} 次，建议人工介入。",
                evidence_refs=[f"retry_count={retries}"],
                snapshot={"task_id": tid, "retry_count": retries},
            ))
        elif retries >= th["task_retry_warning"]:
            sigs.append(self._sig(
                SignalType.TASK_BLOCKED, SignalSeverity.WARNING,
                source=f"task_progress.{tid}.retry",
                title=f"任务重试偏多：{tid}（{retries} 次）",
                description=f"任务 {tid} 已重试 {retries} 次。",
                evidence_refs=[f"retry_count={retries}"],
                snapshot={"task_id": tid, "retry_count": retries},
            ))
        return sigs

    def _detect_data_missing(self, ctx: Dict, th: Dict) -> List[Signal]:
        """检测数据缺失：关键表空 / 字段空率高 / 采集断流。"""
        d = ctx.get("data_quality")
        if not isinstance(d, dict):
            return []
        sigs: List[Signal] = []
        missing = d.get("missing_tables")
        if isinstance(missing, list) and missing:
            sev = (SignalSeverity.CRITICAL if len(missing) >= 2
                   else SignalSeverity.WARNING)
            sigs.append(self._sig(
                SignalType.DATA_MISSING, sev,
                source="data_quality.missing_tables",
                title=f"关键数据表缺失：{', '.join(missing[:5])}",
                description=f"检测到 {len(missing)} 张关键表无数据：{', '.join(missing[:5])}。",
                evidence_refs=[f"missing_tables={missing}"],
                snapshot={"missing_tables": missing},
            ))
        null_rate = _f(d.get("null_rate"))
        if null_rate > 0:
            if null_rate >= th["data_null_rate_critical"]:
                sev, word = SignalSeverity.CRITICAL, "过高"
            elif null_rate >= th["data_null_rate_warning"]:
                sev, word = SignalSeverity.WARNING, "偏高"
            else:
                sev, word = None, ""
            if sev:
                sigs.append(self._sig(
                    SignalType.DATA_MISSING, sev,
                    source="data_quality.null_rate",
                    title=f"关键字段空率{word}：{null_rate:.1%}",
                    description=f"关键字段空值率 {null_rate:.1%}。",
                    evidence_refs=[f"null_rate={null_rate}"],
                    snapshot={"null_rate": null_rate},
                ))
        gap = _i(d.get("capture_gap_seconds"))
        if gap > 0:
            if gap >= th["data_capture_gap_seconds_critical"]:
                sigs.append(self._sig(
                    SignalType.DATA_MISSING, SignalSeverity.CRITICAL,
                    source="data_quality.capture_gap",
                    title=f"采集断流：已 {gap} 秒无新数据",
                    description=f"距上次成功采集已 {gap} 秒，需检查采集链路与 Auth。",
                    evidence_refs=[f"capture_gap_seconds={gap}"],
                    snapshot={"capture_gap_seconds": gap},
                ))
            elif gap >= th["data_capture_gap_seconds_warning"]:
                sigs.append(self._sig(
                    SignalType.DATA_MISSING, SignalSeverity.WARNING,
                    source="data_quality.capture_gap",
                    title=f"采集间隔偏长：{gap} 秒",
                    description=f"距上次成功采集已 {gap} 秒。",
                    evidence_refs=[f"capture_gap_seconds={gap}"],
                    snapshot={"capture_gap_seconds": gap},
                ))
        return sigs

    def _detect_trend_change(self, ctx: Dict, th: Dict) -> List[Signal]:
        """检测趋势显著变化。"""
        t = ctx.get("trend_data")
        if not isinstance(t, dict):
            return []
        metric = str(t.get("metric", "unknown"))
        change = _f(t.get("change_pct"))
        direction = str(t.get("direction", "")).lower()
        if abs(change) >= th["trend_change_pct_critical"]:
            sev, word = SignalSeverity.CRITICAL, "剧烈变化"
        elif abs(change) >= th["trend_change_pct_warning"]:
            sev, word = SignalSeverity.WARNING, "明显变化"
        else:
            return []
        return [self._sig(
            SignalType.TREND_CHANGE, sev,
            source=f"trend_data.{metric}",
            title=f"趋势{word}：{metric} {change:+.1f}%",
            description=f"指标 {metric} 变化率 {change:+.1f}%（方向：{direction or 'unknown'}）。",
            evidence_refs=[f"metric={metric}", f"change_pct={change}"],
            snapshot={"metric": metric, "change_pct": change, "direction": direction},
        )]

    def _detect_performance_degrade(self, ctx: Dict, th: Dict) -> List[Signal]:
        """检测性能退化：当前延迟相对基线倍数。"""
        p = ctx.get("performance")
        if not isinstance(p, dict):
            return []
        cur = _f(p.get("current_latency_ms"))
        base = _f(p.get("baseline_latency_ms"))
        if cur <= 0 or base <= 0:
            return []
        ratio = cur / base
        if ratio >= th["perf_degrade_latency_ratio_critical"]:
            sev, word = SignalSeverity.CRITICAL, "严重退化"
        elif ratio >= th["perf_degrade_latency_ratio_warning"]:
            sev, word = SignalSeverity.WARNING, "退化"
        else:
            return []
        return [self._sig(
            SignalType.PERFORMANCE_DEGRADE, sev,
            source="performance.latency",
            title=f"性能{word}：延迟为基线的 {ratio:.1f} 倍",
            description=f"当前 {cur:.0f}ms，基线 {base:.0f}ms，退化 {ratio:.1f}x。",
            evidence_refs=[f"current={cur}", f"baseline={base}"],
            snapshot={"ratio": ratio, "current": cur, "baseline": base},
        )]

    def _detect_better_path(self, ctx: Dict, th: Dict) -> List[Signal]:
        """检测更优路径：仅在 context 显式提供 better_path 时触发。"""
        bp = ctx.get("better_path")
        if not isinstance(bp, dict):
            return []
        evidence = bp.get("evidence_refs")
        return [self._sig(
            SignalType.BETTER_PATH, SignalSeverity.INFO,
            source=str(bp.get("source", "better_path")),
            title=str(bp.get("title", "检测到更优执行路径")),
            description=str(bp.get("description", "系统检测到可能更优的执行路径。")),
            evidence_refs=evidence if isinstance(evidence, list) else [],
            snapshot={"better_path": bp},
        )]

    # ── 内部工具 ──────────────────────────────────────────────

    @staticmethod
    def _sig(
        signal_type: SignalType, severity: SignalSeverity,
        source: str, title: str, description: str,
        evidence_refs: Optional[List[str]] = None,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        return Signal(
            signal_type=signal_type.value, severity=severity.value,
            source=source, title=title, description=description,
            evidence_refs=evidence_refs or [],
            context_snapshot=snapshot or {},
        )


# ── 模块级便捷函数 ────────────────────────────────────────────

_default_detector: Optional[SignalDetector] = None


def _get_default_detector() -> SignalDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = SignalDetector()
    return _default_detector


def detect_signals(context: Optional[Dict[str, Any]] = None) -> List[Signal]:
    """模块级便捷函数：使用默认检测器扫描上下文。"""
    return _get_default_detector().detect_signals(context)

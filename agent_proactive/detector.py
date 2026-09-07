# -*- coding: utf-8 -*-
"""
Signal Detector — 主动式信号检测器
====================================
扫描系统状态上下文，基于纯规则生成 Signal。
不依赖任何外部 AI API，所有检测逻辑可解释、可追踪。

context 可选字段（用 .get() 安全访问）：
  - system_metrics   : {cpu_pct, memory_pct, disk_pct, error_rate, latency_ms, ...}
  - risk_state       : {current_level, previous_level, active_alerts, escalation_count, ...}
  - task_progress    : {task_id, status, stuck_seconds, retry_count, progress_pct, ...}
  - data_quality     : {missing_tables, missing_fields, null_rate, last_capture_at, ...}
  - trend_data       : {metric, current, baseline, change_pct, direction, window, ...}
  - ai_status        : {provider, status, circuit_state, fallback_count, ...}
  - collection_state : {platform, status, consecutive_failures, ...}

检测维度：
  - ANOMALY            : 系统指标异常（CPU/内存/错误率/延迟超阈值）
  - TREND_CHANGE       : 趋势显著变化（变化率超阈值且方向明确）
  - TASK_BLOCKED       : 任务阻塞（卡住超时 / 重试过多 / 进度停滞）
  - RISK_ESCALATION    : 风险升级（等级上升 / 活跃告警数激增）
  - DATA_MISSING       : 数据缺失（关键表空 / 字段空率高 / 采集断流）
  - BETTER_PATH        : 更优路径（检测到可优化的执行路径）
  - PERFORMANCE_DEGRADE: 性能退化（延迟上升 / 吞吐下降）
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────────────────────
# 枚举与数据结构
# ──────────────────────────────────────────────────────────────

class SignalType(str, Enum):
    """信号类型枚举。"""
    ANOMALY = "anomaly"
    TREND_CHANGE = "trend_change"
    TASK_BLOCKED = "task_blocked"
    RISK_ESCALATION = "risk_escalation"
    DATA_MISSING = "data_missing"
    BETTER_PATH = "better_path"
    PERFORMANCE_DEGRADE = "performance_degrade"


class SignalSeverity(str, Enum):
    """信号严重度枚举。"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# 严重度排序权重（用于排序）
_SEVERITY_ORDER: Dict[str, int] = {
    SignalSeverity.INFO.value: 0,
    SignalSeverity.WARNING.value: 1,
    SignalSeverity.CRITICAL.value: 2,
}


@dataclass
class Signal:
    """主动检测信号。

    每个信号携带可追溯的证据引用与上下文快照，确保可解释、可审计。
    """
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


# ──────────────────────────────────────────────────────────────
# 检测阈值（可通过 context 中的 thresholds 覆盖）
# ──────────────────────────────────────────────────────────────

_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "cpu_pct_critical": 90.0,
    "cpu_pct_warning": 75.0,
    "memory_pct_critical": 90.0,
    "memory_pct_warning": 75.0,
    "error_rate_critical": 0.10,       # 10%
    "error_rate_warning": 0.03,        # 3%
    "latency_ms_critical": 5000.0,
    "latency_ms_warning": 2000.0,
    "task_stuck_seconds_critical": 600,
    "task_stuck_seconds_warning": 180,
    "task_retry_critical": 5,
    "task_retry_warning": 3,
    "risk_escalation_count_critical": 3,
    "risk_escalation_count_warning": 1,
    "data_null_rate_critical": 0.50,
    "data_null_rate_warning": 0.20,
    "data_capture_gap_seconds_critical": 3600,
    "data_capture_gap_seconds_warning": 1800,
    "trend_change_pct_critical": 50.0,
    "trend_change_pct_warning": 20.0,
    "perf_degrade_latency_ratio_critical": 2.0,
    "perf_degrade_latency_ratio_warning": 1.5,
}


def _merge_thresholds(context: Dict[str, Any]) -> Dict[str, Any]:
    """合并默认阈值与 context 中自定义阈值。"""
    thresholds = dict(_DEFAULT_THRESHOLDS)
    custom = context.get("thresholds")
    if isinstance(custom, dict):
        thresholds.update(custom)
    return thresholds


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """安全转换为 int。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ──────────────────────────────────────────────────────────────
# SignalDetector 主类
# ──────────────────────────────────────────────────────────────

class SignalDetector:
    """信号检测器：扫描系统状态上下文，基于规则生成信号列表。

    用法：
        detector = SignalDetector()
        signals = detector.detect_signals({
            "system_metrics": {"cpu_pct": 95, "error_rate": 0.12},
            "risk_state": {"current_level": "high", "previous_level": "low"},
        })
    """

    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        """
        Args:
            thresholds: 自定义检测阈值（覆盖默认值），None 则使用默认
        """
        self._custom_thresholds = thresholds or {}

    def detect_signals(self, context: Optional[Dict[str, Any]] = None) -> List[Signal]:
        """主入口：扫描系统状态，生成信号列表。

        Args:
            context: 系统状态上下文字典，所有字段均可选

        Returns:
            按严重度降序排列的 Signal 列表（CRITICAL > WARNING > INFO）
        """
        context = context or {}
        thresholds = _merge_thresholds(context)
        if self._custom_thresholds:
            thresholds.update(self._custom_thresholds)

        signals: List[Signal] = []

        # 依次执行各子检测器
        signals.extend(self._detect_anomaly(context, thresholds))
        signals.extend(self._detect_risk_escalation(context, thresholds))
        signals.extend(self._detect_task_blocked(context, thresholds))
        signals.extend(self._detect_data_missing(context, thresholds))
        signals.extend(self._detect_trend_change(context, thresholds))
        signals.extend(self._detect_performance_degrade(context, thresholds))
        signals.extend(self._detect_better_path(context, thresholds))

        # 按严重度降序排列
        signals.sort(key=lambda s: s.severity_rank, reverse=True)
        return signals

    # ── 子检测器 ──────────────────────────────────────────────

    def _detect_anomaly(
        self, context: Dict[str, Any], thresholds: Dict[str, Any]
    ) -> List[Signal]:
        """检测系统指标异常：CPU / 内存 / 错误率 / 延迟。"""
        signals: List[Signal] = []
        metrics = context.get("system_metrics")
        if not isinstance(metrics, dict):
            return signals

        cpu = _safe_float(metrics.get("cpu_pct"))
        if cpu > 0:
            if cpu >= thresholds["cpu_pct_critical"]:
                signals.append(self._make_signal(
                    SignalType.ANOMALY, SignalSeverity.CRITICAL,
                    source="system_metrics.cpu",
                    title=f"CPU 使用率异常：{cpu:.1f}%",
                    description=f"CPU 使用率 {cpu:.1f}% 超过临界阈值 "
                                f"{thresholds['cpu_pct_critical']}%，可能影响采集与分析主链路。",
                    evidence_refs=[f"system_metrics.cpu_pct={cpu}"],
                    snapshot={"cpu_pct": cpu, "threshold": thresholds["cpu_pct_critical"]},
                ))
            elif cpu >= thresholds["cpu_pct_warning"]:
                signals.append(self._make_signal(
                    SignalType.ANOMALY, SignalSeverity.WARNING,
                    source="system_metrics.cpu",
                    title=f"CPU 使用率偏高：{cpu:.1f}%",
                    description=f"CPU 使用率 {cpu:.1f}% 超过警告阈值 "
                                f"{thresholds['cpu_pct_warning']}%。",
                    evidence_refs=[f"system_metrics.cpu_pct={cpu}"],
                    snapshot={"cpu_pct": cpu, "threshold": thresholds["cpu_pct_warning"]},
                ))

        mem = _safe_float(metrics.get("memory_pct"))
        if mem > 0:
            if mem >= thresholds["memory_pct_critical"]:
                signals.append(self._make_signal(
                    SignalType.ANOMALY, SignalSeverity.CRITICAL,
                    source="system_metrics.memory",
                    title=f"内存使用率异常：{mem:.1f}%",
                    description=f"内存使用率 {mem:.1f}% 超过临界阈值 "
                                f"{thresholds['memory_pct_critical']}%，存在 OOM 风险。",
                    evidence_refs=[f"system_metrics.memory_pct={mem}"],
                    snapshot={"memory_pct": mem, "threshold": thresholds["memory_pct_critical"]},
                ))
            elif mem >= thresholds["memory_pct_warning"]:
                signals.append(self._make_signal(
                    SignalType.ANOMALY, SignalSeverity.WARNING,
                    source="system_metrics.memory",
                    title=f"内存使用率偏高：{mem:.1f}%",
                    description=f"内存使用率 {mem:.1f}% 超过警告阈值 "
                                f"{thresholds['memory_pct_warning']}%。",
                    evidence_refs=[f"system_metrics.memory_pct={mem}"],
                    snapshot={"memory_pct": mem, "threshold": thresholds["memory_pct_warning"]},
                ))

        err_rate = _safe_float(metrics.get("error_rate"))
        if err_rate > 0:
            if err_rate >= thresholds["error_rate_critical"]:
                signals.append(self._make_signal(
                    SignalType.ANOMALY, SignalSeverity.CRITICAL,
                    source="system_metrics.error_rate",
                    title=f"错误率异常：{err_rate:.1%}",
                    description=f"系统错误率 {err_rate:.1%} 超过临界阈值 "
                                f"{thresholds['error_rate_critical']:.1%}，主链路可能受损。",
                    evidence_refs=[f"system_metrics.error_rate={err_rate}"],
                    snapshot={"error_rate": err_rate, "threshold": thresholds["error_rate_critical"]},
                ))
            elif err_rate >= thresholds["error_rate_warning"]:
                signals.append(self._make_signal(
                    SignalType.ANOMALY, SignalSeverity.WARNING,
                    source="system_metrics.error_rate",
                    title=f"错误率偏高：{err_rate:.1%}",
                    description=f"系统错误率 {err_rate:.1%} 超过警告阈值 "
                                f"{thresholds['error_rate_warning']:.1%}。",
                    evidence_refs=[f"system_metrics.error_rate={err_rate}"],
                    snapshot={"error_rate": err_rate, "threshold": thresholds["error_rate_warning"]},
                ))

        latency = _safe_float(metrics.get("latency_ms"))
        if latency > 0:
            if latency >= thresholds["latency_ms_critical"]:
                signals.append(self._make_signal(
                    SignalType.ANOMALY, SignalSeverity.CRITICAL,
                    source="system_metrics.latency",
                    title=f"响应延迟异常：{latency:.0f}ms",
                    description=f"平均响应延迟 {latency:.0f}ms 超过临界阈值 "
                                f"{thresholds['latency_ms_critical']:.0f}ms。",
                    evidence_refs=[f"system_metrics.latency_ms={latency}"],
                    snapshot={"latency_ms": latency, "threshold": thresholds["latency_ms_critical"]},
                ))
            elif latency >= thresholds["latency_ms_warning"]:
                signals.append(self._make_signal(
                    SignalType.ANOMALY, SignalSeverity.WARNING,
                    source="system_metrics.latency",
                    title=f"响应延迟偏高：{latency:.0f}ms",
                    description=f"平均响应延迟 {latency:.0f}ms 超过警告阈值 "
                                f"{thresholds['latency_ms_warning']:.0f}ms。",
                    evidence_refs=[f"system_metrics.latency_ms={latency}"],
                    snapshot={"latency_ms": latency, "threshold": thresholds["latency_ms_warning"]},
                ))

        return signals

    def _detect_risk_escalation(
        self, context: Dict[str, Any], thresholds: Dict[str, Any]
    ) -> List[Signal]:
        """检测风险升级：风险等级上升 / 活跃告警数激增。"""
        signals: List[Signal] = []
        risk = context.get("risk_state")
        if not isinstance(risk, dict):
            return signals

        current = str(risk.get("current_level", "")).lower()
        previous = str(risk.get("previous_level", "")).lower()
        level_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

        if current and previous and current in level_order and previous in level_order:
            if level_order[current] > level_order[previous]:
                severity = (
                    SignalSeverity.CRITICAL
                    if current == "critical" or level_order[current] - level_order[previous] >= 2
                    else SignalSeverity.WARNING
                )
                signals.append(self._make_signal(
                    SignalType.RISK_ESCALATION, severity,
                    source="risk_state.level",
                    title=f"风险等级升级：{previous} → {current}",
                    description=f"系统风险等级从 {previous} 升级至 {current}，"
                                f"需关注舆情或系统稳定性变化。",
                    evidence_refs=[
                        f"risk_state.current_level={current}",
                        f"risk_state.previous_level={previous}",
                    ],
                    snapshot={"current_level": current, "previous_level": previous},
                ))

        esc_count = _safe_int(risk.get("escalation_count"))
        if esc_count >= thresholds["risk_escalation_count_critical"]:
            signals.append(self._make_signal(
                SignalType.RISK_ESCALATION, SignalSeverity.CRITICAL,
                source="risk_state.escalation_count",
                title=f"风险升级次数激增：{esc_count} 次",
                description=f"近期风险升级累计 {esc_count} 次，超过临界阈值 "
                            f"{thresholds['risk_escalation_count_critical']} 次。",
                evidence_refs=[f"risk_state.escalation_count={esc_count}"],
                snapshot={"escalation_count": esc_count},
            ))
        elif esc_count >= thresholds["risk_escalation_count_warning"]:
            signals.append(self._make_signal(
                SignalType.RISK_ESCALATION, SignalSeverity.WARNING,
                source="risk_state.escalation_count",
                title=f"风险升级次数偏多：{esc_count} 次",
                description=f"近期风险升级累计 {esc_count} 次，超过警告阈值 "
                            f"{thresholds['risk_escalation_count_warning']} 次。",
                evidence_refs=[f"risk_state.escalation_count={esc_count}"],
                snapshot={"escalation_count": esc_count},
            ))

        active_alerts = _safe_int(risk.get("active_alerts"))
        if active_alerts >= 5:
            signals.append(self._make_signal(
                SignalType.RISK_ESCALATION, SignalSeverity.WARNING,
                source="risk_state.active_alerts",
                title=f"活跃告警数偏多：{active_alerts} 条",
                description=f"当前活跃告警 {active_alerts} 条，建议逐一确认处理状态。",
                evidence_refs=[f"risk_state.active_alerts={active_alerts}"],
                snapshot={"active_alerts": active_alerts},
            ))

        return signals

    def _detect_task_blocked(
        self, context: Dict[str, Any], thresholds: Dict[str, Any]
    ) -> List[Signal]:
        """检测任务阻塞：卡住超时 / 重试过多 / 进度停滞。"""
        signals: List[Signal] = []
        task = context.get("task_progress")
        if not isinstance(task, dict):
            return signals

        task_id = str(task.get("task_id", "unknown"))
        status = str(task.get("status", "")).lower()

        # 卡住超时
        stuck = _safe_int(task.get("stuck_seconds"))
        if stuck > 0 and status not in ("completed", "failed", "cancelled"):
            if stuck >= thresholds["task_stuck_seconds_critical"]:
                signals.append(self._make_signal(
                    SignalType.TASK_BLOCKED, SignalSeverity.CRITICAL,
                    source=f"task_progress.{task_id}",
                    title=f"任务阻塞超时：{task_id}（{stuck}s）",
                    description=f"任务 {task_id} 已卡住 {stuck} 秒，超过临界阈值 "
                                f"{thresholds['task_stuck_seconds_critical']} 秒，"
                                f"当前状态：{status or 'unknown'}。",
                    evidence_refs=[f"task_progress.task_id={task_id}", f"stuck_seconds={stuck}"],
                    snapshot={"task_id": task_id, "stuck_seconds": stuck, "status": status},
                ))
            elif stuck >= thresholds["task_stuck_seconds_warning"]:
                signals.append(self._make_signal(
                    SignalType.TASK_BLOCKED, SignalSeverity.WARNING,
                    source=f"task_progress.{task_id}",
                    title=f"任务可能阻塞：{task_id}（{stuck}s）",
                    description=f"任务 {task_id} 已持续 {stuck} 秒无进展，超过警告阈值 "
                                f"{thresholds['task_stuck_seconds_warning']} 秒。",
                    evidence_refs=[f"task_progress.task_id={task_id}", f"stuck_seconds={stuck}"],
                    snapshot={"task_id": task_id, "stuck_seconds": stuck, "status": status},
                ))

        # 重试过多
        retries = _safe_int(task.get("retry_count"))
        if retries >= thresholds["task_retry_critical"]:
            signals.append(self._make_signal(
                SignalType.TASK_BLOCKED, SignalSeverity.CRITICAL,
                source=f"task_progress.{task_id}.retry",
                title=f"任务重试过多：{task_id}（{retries} 次）",
                description=f"任务 {task_id} 已重试 {retries} 次，超过临界阈值 "
                            f"{thresholds['task_retry_critical']} 次，建议人工介入。",
                evidence_refs=[f"task_progress.retry_count={retries}"],
                snapshot={"task_id": task_id, "retry_count": retries},
            ))
        elif retries >= thresholds["task_retry_warning"]:
            signals.append(self._make_signal(
                SignalType.TASK_BLOCKED, SignalSeverity.WARNING,
                source=f"task_progress.{task_id}.retry",
                title=f"任务重试偏多：{task_id}（{retries} 次）",
                description=f"任务 {task_id} 已重试 {retries} 次，超过警告阈值 "
                            f"{thresholds['task_retry_warning']} 次。",
                evidence_refs=[f"task_progress.retry_count={retries}"],
                snapshot={"task_id": task_id, "retry_count": retries},
            ))

        return signals

    def _detect_data_missing(
        self, context: Dict[str, Any], thresholds: Dict[str, Any]
    ) -> List[Signal]:
        """检测数据缺失：关键表空 / 字段空率高 / 采集断流。"""
        signals: List[Signal] = []
        dq = context.get("data_quality")
        if not isinstance(dq, dict):
            return signals

        # 关键表缺失
        missing_tables = dq.get("missing_tables")
        if isinstance(missing_tables, list) and missing_tables:
            severity = (
                SignalSeverity.CRITICAL if len(missing_tables) >= 2
                else SignalSeverity.WARNING
            )
            signals.append(self._make_signal(
                SignalType.DATA_MISSING, severity,
                source="data_quality.missing_tables",
                title=f"关键数据表缺失：{', '.join(missing_tables[:5])}",
                description=f"检测到 {len(missing_tables)} 张关键表无数据或不存在："
                            f"{', '.join(missing_tables[:5])}，可能影响统计与报告。",
                evidence_refs=[f"data_quality.missing_tables={missing_tables}"],
                snapshot={"missing_tables": missing_tables},
            ))

        # 字段空率
        null_rate = _safe_float(dq.get("null_rate"))
        if null_rate > 0:
            if null_rate >= thresholds["data_null_rate_critical"]:
                signals.append(self._make_signal(
                    SignalType.DATA_MISSING, SignalSeverity.CRITICAL,
                    source="data_quality.null_rate",
                    title=f"关键字段空率过高：{null_rate:.1%}",
                    description=f"关键字段空值率 {null_rate:.1%} 超过临界阈值 "
                                f"{thresholds['data_null_rate_critical']:.1%}，数据质量严重受损。",
                    evidence_refs=[f"data_quality.null_rate={null_rate}"],
                    snapshot={"null_rate": null_rate, "threshold": thresholds["data_null_rate_critical"]},
                ))
            elif null_rate >= thresholds["data_null_rate_warning"]:
                signals.append(self._make_signal(
                    SignalType.DATA_MISSING, SignalSeverity.WARNING,
                    source="data_quality.null_rate",
                    title=f"字段空率偏高：{null_rate:.1%}",
                    description=f"关键字段空值率 {null_rate:.1%} 超过警告阈值 "
                                f"{thresholds['data_null_rate_warning']:.1%}。",
                    evidence_refs=[f"data_quality.null_rate={null_rate}"],
                    snapshot={"null_rate": null_rate, "threshold": thresholds["data_null_rate_warning"]},
                ))

        # 采集断流（距上次采集时间间隔）
        gap = _safe_int(dq.get("capture_gap_seconds"))
        if gap > 0:
            if gap >= thresholds["data_capture_gap_seconds_critical"]:
                signals.append(self._make_signal(
                    SignalType.DATA_MISSING, SignalSeverity.CRITICAL,
                    source="data_quality.capture_gap",
                    title=f"采集断流：已 {gap} 秒无新数据",
                    description=f"距上次成功采集已 {gap} 秒，超过临界阈值 "
                                f"{thresholds['data_capture_gap_seconds_critical']} 秒，"
                                f"需检查采集链路与 Auth 状态。",
                    evidence_refs=[f"data_quality.capture_gap_seconds={gap}"],
                    snapshot={"capture_gap_seconds": gap},
                ))
            elif gap >= thresholds["data_capture_gap_seconds_warning"]:
                signals.append(self._make_signal(
                    SignalType.DATA_MISSING, SignalSeverity.WARNING,
                    source="data_quality.capture_gap",
                    title=f"采集间隔偏长：{gap} 秒",
                    description=f"距上次成功采集已 {gap} 秒，超过警告阈值 "
                                f"{thresholds['data_capture_gap_seconds_warning']} 秒。",
                    evidence_refs=[f"data_quality.capture_gap_seconds={gap}"],
                    snapshot={"capture_gap_seconds": gap},
                ))

        return signals

    def _detect_trend_change(
        self, context: Dict[str, Any], thresholds: Dict[str, Any]
    ) -> List[Signal]:
        """检测趋势显著变化：变化率超阈值且方向明确。"""
        signals: List[Signal] = []
        trend = context.get("trend_data")
        if not isinstance(trend, dict):
            return signals

        metric = str(trend.get("metric", "unknown"))
        change_pct = _safe_float(trend.get("change_pct"))
        direction = str(trend.get("direction", "")).lower()

        if abs(change_pct) >= thresholds["trend_change_pct_critical"]:
            signals.append(self._make_signal(
                SignalType.TREND_CHANGE, SignalSeverity.CRITICAL,
                source=f"trend_data.{metric}",
                title=f"趋势剧烈变化：{metric} {change_pct:+.1f}%",
                description=f"指标 {metric} 变化率 {change_pct:+.1f}%（方向：{direction or 'unknown'}），"
                            f"超过临界阈值 ±{thresholds['trend_change_pct_critical']}%。",
                evidence_refs=[
                    f"trend_data.metric={metric}",
                    f"trend_data.change_pct={change_pct}",
                ],
                snapshot={"metric": metric, "change_pct": change_pct, "direction": direction},
            ))
        elif abs(change_pct) >= thresholds["trend_change_pct_warning"]:
            signals.append(self._make_signal(
                SignalType.TREND_CHANGE, SignalSeverity.WARNING,
                source=f"trend_data.{metric}",
                title=f"趋势明显变化：{metric} {change_pct:+.1f}%",
                description=f"指标 {metric} 变化率 {change_pct:+.1f}%（方向：{direction or 'unknown'}），"
                            f"超过警告阈值 ±{thresholds['trend_change_pct_warning']}%。",
                evidence_refs=[
                    f"trend_data.metric={metric}",
                    f"trend_data.change_pct={change_pct}",
                ],
                snapshot={"metric": metric, "change_pct": change_pct, "direction": direction},
            ))

        return signals

    def _detect_performance_degrade(
        self, context: Dict[str, Any], thresholds: Dict[str, Any]
    ) -> List[Signal]:
        """检测性能退化：当前延迟相对基线的倍数。"""
        signals: List[Signal] = []
        perf = context.get("performance")
        if not isinstance(perf, dict):
            return signals

        current_latency = _safe_float(perf.get("current_latency_ms"))
        baseline_latency = _safe_float(perf.get("baseline_latency_ms"))
        if current_latency > 0 and baseline_latency > 0:
            ratio = current_latency / baseline_latency
            if ratio >= thresholds["perf_degrade_latency_ratio_critical"]:
                signals.append(self._make_signal(
                    SignalType.PERFORMANCE_DEGRADE, SignalSeverity.CRITICAL,
                    source="performance.latency",
                    title=f"性能严重退化：延迟为基线的 {ratio:.1f} 倍",
                    description=f"当前延迟 {current_latency:.0f}ms，基线 {baseline_latency:.0f}ms，"
                                f"退化倍数 {ratio:.1f}x 超过临界阈值 "
                                f"{thresholds['perf_degrade_latency_ratio_critical']}x。",
                    evidence_refs=[
                        f"performance.current_latency_ms={current_latency}",
                        f"performance.baseline_latency_ms={baseline_latency}",
                    ],
                    snapshot={"ratio": ratio, "current": current_latency, "baseline": baseline_latency},
                ))
            elif ratio >= thresholds["perf_degrade_latency_ratio_warning"]:
                signals.append(self._make_signal(
                    SignalType.PERFORMANCE_DEGRADE, SignalSeverity.WARNING,
                    source="performance.latency",
                    title=f"性能退化：延迟为基线的 {ratio:.1f} 倍",
                    description=f"当前延迟 {current_latency:.0f}ms，基线 {baseline_latency:.0f}ms，"
                                f"退化倍数 {ratio:.1f}x 超过警告阈值 "
                                f"{thresholds['perf_degrade_latency_ratio_warning']}x。",
                    evidence_refs=[
                        f"performance.current_latency_ms={current_latency}",
                        f"performance.baseline_latency_ms={baseline_latency}",
                    ],
                    snapshot={"ratio": ratio, "current": current_latency, "baseline": baseline_latency},
                ))

        return signals

    def _detect_better_path(
        self, context: Dict[str, Any], thresholds: Dict[str, Any]
    ) -> List[Signal]:
        """检测更优路径：当上下文显式标记了可优化路径时生成 INFO 信号。

        此检测器不做猜测，仅在 context 中存在明确的 better_path 建议时触发，
        避免误报。调用方可在 context["better_path"] 中放入：
        {"title": ..., "description": ..., "evidence_refs": [...]}
        """
        signals: List[Signal] = []
        bp = context.get("better_path")
        if not isinstance(bp, dict):
            return signals

        title = str(bp.get("title", "检测到更优执行路径"))
        description = str(bp.get("description", "系统检测到一条可能更优的执行路径，建议评估。"))
        evidence = bp.get("evidence_refs")
        if not isinstance(evidence, list):
            evidence = []

        signals.append(self._make_signal(
            SignalType.BETTER_PATH, SignalSeverity.INFO,
            source=str(bp.get("source", "better_path")),
            title=title,
            description=description,
            evidence_refs=evidence,
            snapshot={"better_path": bp},
        ))
        return signals

    # ── 内部工具 ──────────────────────────────────────────────

    @staticmethod
    def _make_signal(
        signal_type: SignalType,
        severity: SignalSeverity,
        source: str,
        title: str,
        description: str,
        evidence_refs: Optional[List[str]] = None,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        """构造 Signal 实例。"""
        return Signal(
            signal_type=signal_type.value,
            severity=severity.value,
            source=source,
            title=title,
            description=description,
            evidence_refs=evidence_refs or [],
            context_snapshot=snapshot or {},
        )


# ──────────────────────────────────────────────────────────────
# 模块级便捷函数
# ──────────────────────────────────────────────────────────────

_default_detector: Optional[SignalDetector] = None


def _get_default_detector() -> SignalDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = SignalDetector()
    return _default_detector


def detect_signals(context: Optional[Dict[str, Any]] = None) -> List[Signal]:
    """模块级便捷函数：使用默认检测器扫描上下文并返回信号列表。

    Args:
        context: 系统状态上下文字典

    Returns:
        按严重度降序排列的 Signal 列表
    """
    return _get_default_detector().detect_signals(context)

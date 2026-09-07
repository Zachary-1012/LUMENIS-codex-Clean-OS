# -*- coding: utf-8 -*-
"""
Observation Layer — 观察/感知层（ZBC MISSING 项补齐）
=====================================================
感知当前环境：DB 状态、API 可用性、工具可用性、前一步执行结果。
输出结构化 observation（state dict）供 Replanning 使用。

数据源：
  - DB 查询：notes/comments/events/daily_reports 等表的行数、最新时间
  - API 健康检查：ai_channel.channel_health()、provider 状态
  - collection_logs：采集状态
  - metric_snapshots：指标快照
  - 前一步执行结果：step output / error / duration

设计原则：
  - 只读感知，不修改任何系统状态
  - 结构化输出，可序列化
  - 可注入自定义 observer 扩展感知维度
  - 失败时返回降级 observation（不静默成空）

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - observation 作为 Agent._observe() 的输出，包含 environment_state / tool_state / step_result
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Observation:
    """结构化观察结果。"""
    observation_id: str = field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: str = ""
    step: int = 0

    # 环境状态
    db_status: str = "unknown"           # ok / degraded / unavailable
    db_stats: Dict[str, Any] = field(default_factory=dict)

    # AI/API 状态
    ai_status: str = "unknown"           # ok / degraded / unavailable
    ai_provider: str = ""
    ai_circuit_state: str = "unknown"

    # 工具状态
    tool_status: Dict[str, str] = field(default_factory=dict)  # tool_name -> available/unavailable

    # 采集状态
    collection_status: str = "unknown"   # running / idle / error / unknown
    collection_stats: Dict[str, Any] = field(default_factory=dict)

    # 前一步执行结果
    previous_step_result: Optional[Dict[str, Any]] = None
    previous_step_error: Optional[str] = None
    previous_step_duration_ms: float = 0.0

    # 环境变化标记（与上一次 observation 对比）
    environment_changed: bool = False
    changed_fields: List[str] = field(default_factory=list)

    # 自定义扩展
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class BaseObserver:
    """观察者基类。子类实现 observe() 方法。"""

    name: str = "base"

    def observe(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行观察，返回该维度的观察结果 dict。"""
        raise NotImplementedError


class DBStatusObserver(BaseObserver):
    """DB 状态观察者。只读查询，不修改数据。"""

    name = "db_status"

    def __init__(self, db_path: Optional[str] = None, query_func: Optional[Callable] = None):
        """
        Args:
            db_path: SQLite 数据库路径（None 则使用默认 data/monitor.db）
            query_func: 自定义查询函数 callback() -> Dict，用于测试注入
        """
        self._db_path = db_path
        self._query_func = query_func

    def observe(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._query_func:
            return self._query_func()

        result = {"status": "unknown", "tables": {}, "error": None}
        try:
            import sqlite3
            import os
            db_path = self._db_path or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "monitor.db"
            )
            if not os.path.exists(db_path):
                result["status"] = "unavailable"
                result["error"] = f"db file not found: {db_path}"
                return result

            conn = sqlite3.connect(db_path, timeout=5)
            try:
                # 只读查询关键表行数
                tables = ["notes", "comments", "events", "daily_reports",
                          "collection_logs", "ai_task", "ai_task_step"]
                stats = {}
                for tbl in tables:
                    try:
                        row = conn.execute(
                            f"SELECT COUNT(*) FROM {tbl}"
                        ).fetchone()
                        stats[tbl] = row[0] if row else 0
                    except Exception:
                        stats[tbl] = -1  # 表不存在

                # 最新采集时间
                try:
                    row = conn.execute(
                        "SELECT MAX(captured_at) FROM collection_logs"
                    ).fetchone()
                    stats["last_collection_at"] = row[0] if row and row[0] else None
                except Exception:
                    stats["last_collection_at"] = None

                result["status"] = "ok"
                result["tables"] = stats
            finally:
                conn.close()
        except Exception as e:
            result["status"] = "unavailable"
            result["error"] = str(e)[:200]

        return result


class AIStatusObserver(BaseObserver):
    """AI/API 健康观察者。复用 ai_channel 的健康检查。"""

    name = "ai_status"

    def __init__(self, health_func: Optional[Callable] = None):
        """
        Args:
            health_func: 自定义健康检查函数 callback() -> Dict，用于测试注入
        """
        self._health_func = health_func

    def observe(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._health_func:
            return self._health_func()

        result = {"status": "unknown", "provider": "", "circuit_state": "unknown", "error": None}
        try:
            from ai_channel import channel_health, get_provider_status_v1
            try:
                health = channel_health()
                result["status"] = health.get("status", "unknown")
                result["provider"] = health.get("provider", "")
            except Exception:
                pass

            try:
                providers = get_provider_status_v1()
                zhipu = providers.get("zhipu", {})
                result["circuit_state"] = zhipu.get("circuit_breaker", "unknown")
                result["provider_status"] = zhipu.get("status", "unknown")
            except Exception:
                pass
        except Exception as e:
            result["status"] = "unavailable"
            result["error"] = str(e)[:200]

        return result


class ToolStatusObserver(BaseObserver):
    """工具可用性观察者。检查已注册的 skill/function 是否可用。"""

    name = "tool_status"

    def __init__(self, tool_registry_func: Optional[Callable] = None):
        """
        Args:
            tool_registry_func: 自定义工具注册表查询 callback() -> Dict[tool_name, available]
        """
        self._tool_registry_func = tool_registry_func

    def observe(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._tool_registry_func:
            return self._tool_registry_func()

        result = {"tools": {}}
        try:
            from skill_registry import get_skill_registry
            reg = get_skill_registry()
            stats = reg.stats()
            result["tools"]["skill_registry_total"] = stats.get("total", 0)
            result["tools"]["skill_registry_enabled"] = stats.get("enabled", 0)
        except Exception as e:
            result["tools"]["skill_registry_error"] = str(e)[:100]

        return result


class CollectionStatusObserver(BaseObserver):
    """采集状态观察者。"""

    name = "collection_status"

    def __init__(self, collection_func: Optional[Callable] = None):
        self._collection_func = collection_func

    def observe(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._collection_func:
            return self._collection_func()

        result = {"status": "unknown", "stats": {}, "error": None}
        try:
            import sqlite3
            import os
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "monitor.db"
            )
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path, timeout=5)
                try:
                    # 最近采集日志
                    row = conn.execute(
                        "SELECT status, COUNT(*) FROM collection_logs "
                        "GROUP BY status ORDER BY COUNT(*) DESC"
                    ).fetchall()
                    result["stats"]["by_status"] = {r[0]: r[1] for r in row} if row else {}

                    # 最近1小时采集数
                    row = conn.execute(
                        "SELECT COUNT(*) FROM collection_logs "
                        "WHERE captured_at >= datetime('now', '-1 hour')"
                    ).fetchone()
                    result["stats"]["last_hour_count"] = row[0] if row else 0

                    result["status"] = "ok"
                finally:
                    conn.close()
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)[:200]

        return result


class ObservationLayer:
    """观察层：聚合多个观察者，输出结构化 Observation。

    用法：
        layer = ObservationLayer(agent_id="agent_001")
        layer.register_observer(DBStatusObserver())
        obs = layer.observe(step=1, previous_result={"output": "..."})
    """

    def __init__(
        self,
        agent_id: str = "",
        observers: Optional[List[BaseObserver]] = None,
        auto_register_default: bool = True,
    ):
        self.agent_id = agent_id
        self._observers: Dict[str, BaseObserver] = {}
        self._last_observation: Optional[Observation] = None

        if observers:
            for ob in observers:
                self.register_observer(ob)

        if auto_register_default and not observers:
            self._register_default_observers()

    def _register_default_observers(self) -> None:
        """注册默认观察者（DB / AI / Tool / Collection）。"""
        self.register_observer(DBStatusObserver())
        self.register_observer(AIStatusObserver())
        self.register_observer(ToolStatusObserver())
        self.register_observer(CollectionStatusObserver())

    def register_observer(self, observer: BaseObserver) -> None:
        """注册观察者。"""
        self._observers[observer.name] = observer

    def unregister_observer(self, name: str) -> None:
        """注销观察者。"""
        self._observers.pop(name, None)

    def observe(
        self,
        step: int = 0,
        previous_result: Optional[Dict[str, Any]] = None,
        previous_error: Optional[str] = None,
        previous_duration_ms: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        """执行全量观察，返回结构化 Observation。

        Args:
            step: 当前步骤号
            previous_result: 前一步执行结果
            previous_error: 前一步错误
            previous_duration_ms: 前一步耗时
            context: 附加上下文

        Returns:
            Observation 结构化观察结果
        """
        obs = Observation(
            agent_id=self.agent_id,
            step=step,
            previous_step_result=previous_result,
            previous_step_error=previous_error,
            previous_step_duration_ms=previous_duration_ms,
        )

        # 执行各观察者
        for name, observer in self._observers.items():
            try:
                result = observer.observe(context)
                self._apply_observer_result(obs, name, result)
            except Exception as e:
                obs.extra[f"{name}_error"] = str(e)[:200]

        # 与上一次对比，检测环境变化
        if self._last_observation:
            changed = []
            if obs.db_status != self._last_observation.db_status:
                changed.append("db_status")
            if obs.ai_status != self._last_observation.ai_status:
                changed.append("ai_status")
            if obs.collection_status != self._last_observation.collection_status:
                changed.append("collection_status")
            if obs.ai_circuit_state != self._last_observation.ai_circuit_state:
                changed.append("ai_circuit_state")
            obs.environment_changed = len(changed) > 0
            obs.changed_fields = changed

        self._last_observation = obs
        return obs

    @staticmethod
    def _apply_observer_result(obs: Observation, name: str, result: Dict[str, Any]) -> None:
        """将观察者结果应用到 Observation 对象。"""
        if name == "db_status":
            obs.db_status = result.get("status", "unknown")
            obs.db_stats = result.get("tables", {})
        elif name == "ai_status":
            obs.ai_status = result.get("status", "unknown")
            obs.ai_provider = result.get("provider", "")
            obs.ai_circuit_state = result.get("circuit_state", "unknown")
        elif name == "tool_status":
            obs.tool_status = result.get("tools", {})
        elif name == "collection_status":
            obs.collection_status = result.get("status", "unknown")
            obs.collection_stats = result.get("stats", {})
        else:
            obs.extra[name] = result

    def get_last_observation(self) -> Optional[Observation]:
        """获取上一次观察结果。"""
        return self._last_observation

    def reset(self) -> None:
        """重置观察历史。"""
        self._last_observation = None

# -*- coding: utf-8 -*-
"""
Environment Registry — 执行环境注册
====================================
管理 Agent 可执行的计算环境，支持 local / remote / hybrid 三种类型。

设计原则：
  - 环境注册与发现解耦，不绑定具体运行时
  - 每个环境声明其 capabilities，供调度器选择
  - 环境状态可查询（online / offline / busy / maintenance）
  - 不修改任何现有源码
"""
from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionEnvironment:
    """执行环境描述。"""
    env_id: str
    env_type: str = "local"               # local / remote / hybrid
    capabilities: Dict[str, Any] = field(default_factory=dict)
    status: str = "offline"               # online / offline / busy / maintenance
    endpoint: str = ""
    registered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(asdict(self))

    @property
    def is_available(self) -> bool:
        """是否可用（online 且非 busy/maintenance）。"""
        return self.status == "online"

    def has_capability(self, capability: str) -> bool:
        """检查是否具备指定能力。"""
        return capability in self.capabilities


class EnvironmentRegistry:
    """执行环境注册表。

    用法：
        registry = EnvironmentRegistry()
        env = ExecutionEnvironment(
            env_id="local_cpu",
            env_type="local",
            capabilities={"python": "3.11", "gpu": False},
            status="online",
        )
        registry.register(env)
        found = registry.get("local_cpu")
        all_envs = registry.list()
    """

    def __init__(self):
        self._envs: Dict[str, ExecutionEnvironment] = {}
        self._lock = threading.RLock()

    def register(self, env: ExecutionEnvironment) -> str:
        """注册环境，返回 env_id。"""
        with self._lock:
            self._envs[env.env_id] = copy.deepcopy(env)
        return env.env_id

    def unregister(self, env_id: str) -> bool:
        """注销环境，返回是否成功。"""
        with self._lock:
            return self._envs.pop(env_id, None) is not None

    def get(self, env_id: str) -> Optional[ExecutionEnvironment]:
        """获取环境，不存在返回 None。"""
        with self._lock:
            env = self._envs.get(env_id)
            return copy.deepcopy(env) if env else None

    def list(
        self,
        env_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ExecutionEnvironment]:
        """列出环境，可按类型/状态过滤。"""
        with self._lock:
            envs = list(self._envs.values())
        if env_type:
            envs = [e for e in envs if e.env_type == env_type]
        if status:
            envs = [e for e in envs if e.status == status]
        return [copy.deepcopy(e) for e in envs]

    def update_status(self, env_id: str, status: str) -> bool:
        """更新环境状态。"""
        with self._lock:
            env = self._envs.get(env_id)
            if env is None:
                return False
            env.status = status
            env.last_heartbeat = datetime.now(timezone.utc).isoformat()
            return True

    def heartbeat(self, env_id: str) -> bool:
        """环境心跳（更新 last_heartbeat，状态设为 online）。"""
        return self.update_status(env_id, "online")

    def find_available(
        self,
        required_capabilities: Optional[List[str]] = None,
        env_type: Optional[str] = None,
    ) -> List[ExecutionEnvironment]:
        """查找可用环境（online 且具备所需能力）。"""
        candidates = self.list(env_type=env_type, status="online")
        if required_capabilities:
            candidates = [
                e for e in candidates
                if all(e.has_capability(cap) for cap in required_capabilities)
            ]
        return candidates

    def clear(self) -> None:
        """清除所有环境（测试用）。"""
        with self._lock:
            self._envs.clear()

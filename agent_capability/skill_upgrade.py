# -*- coding: utf-8 -*-
"""Skill 升级为 Capability — Adapter 层增强。

现有 Skill → Capability 的映射：
  - 增加输入输出 schema、风险等级、权限要求、使用统计
  - 不修改现有 skills_registry 表结构，通过 adapter 层增强
  - Capability Registry：内存注册表，启动时从 skills_registry 加载

与 OSAI capability_registry.py + canonical_skill_registry.py 通过 Contract 对齐。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import get_db_connection
from .router import ToolDefinition, ToolParam, ToolRiskLevel, ToolPermissionLevel

logger = logging.getLogger(__name__)


class CapabilityStatus(str, Enum):
    REGISTERED = "registered"
    ENABLED = "enabled"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


@dataclass
class CapabilityMetadata:
    """Capability 增强元数据（在 SkillMetadata 基础上扩展）。"""
    capability_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    source_skill_id: str = ""               # 来源 Skill ID
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    permission_level: ToolPermissionLevel = ToolPermissionLevel.READ
    requires_approval: bool = False
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_duration_ms: float = 0.0
    status: CapabilityStatus = CapabilityStatus.REGISTERED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    config: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.usage_count
        return (self.success_count / total) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        d["permission_level"] = self.permission_level.value
        d["status"] = self.status.value
        d["success_rate"] = self.success_rate
        return d

    def to_tool_definition(self) -> ToolDefinition:
        """转换为 ToolDefinition（供 CapabilityRouter 使用）。"""
        params = []
        if isinstance(self.input_schema, dict):
            for pname, pdef in self.input_schema.get("properties", {}).items():
                params.append(ToolParam(
                    name=pname,
                    type=pdef.get("type", "string"),
                    required=pname in self.input_schema.get("required", []),
                    description=pdef.get("description", ""),
                    default=pdef.get("default"),
                ))
        return ToolDefinition(
            tool_id=self.capability_id,
            name=self.name,
            description=self.description,
            category=self.category,
            keywords=self.tags,
            params=params,
            permission_level=self.permission_level,
            risk_level=self.risk_level,
            requires_approval=self.requires_approval,
            enabled=self.status == CapabilityStatus.ENABLED,
            version=self.version,
            input_schema=self.input_schema or None,
            output_schema=self.output_schema or None,
        )


class CapabilityRegistry:
    """Capability 内存注册表。

    启动时从 skills_registry 表加载现有 Skill，通过 Adapter 增强为 Capability。
    不修改 skills_registry 表结构，所有增强数据保存在内存中。
    """

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False):
        self.db_path = db_path
        self.enabled = enabled
        self._capabilities: Dict[str, CapabilityMetadata] = {}
        self._loaded_from_db = False

    # ── 从 skills_registry 加载 ──────────────────────────────────

    def load_from_skills_registry(self) -> int:
        """从 skills_registry 表加载现有 Skill，升级为 Capability。

        Returns:
            加载的 Capability 数量
        """
        if not self.enabled or not self.db_path:
            return 0
        if self._loaded_from_db:
            return len(self._capabilities)

        try:
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute(
                    "SELECT skill_id, name, description, product, domain, status, config_json, version "
                    "FROM skills_registry"
                ).fetchall()
                for row in rows:
                    cap = self._upgrade_skill_to_capability(dict(row))
                    if cap:
                        self._capabilities[cap.capability_id] = cap
                self._loaded_from_db = True
                return len(self._capabilities)
            finally:
                conn.close()
        except Exception as e:
            logger.error("CapabilityRegistry.load_from_skills_registry failed: %s", e)
            return 0

    def _upgrade_skill_to_capability(self, skill_row: Dict[str, Any]) -> Optional[CapabilityMetadata]:
        """将 skills_registry 行升级为 CapabilityMetadata。"""
        skill_id = skill_row.get("skill_id", "")
        if not skill_id:
            return None

        # 解析 config_json
        config = {}
        try:
            if skill_row.get("config_json"):
                config = json.loads(skill_row["config_json"])
        except Exception:
            pass

        # 根据 Skill 类型推断风险等级和权限
        risk, perm, approval = self._infer_security_level(skill_id, config)

        return CapabilityMetadata(
            capability_id=f"cap.{skill_id}",
            name=skill_row.get("name", skill_id),
            description=skill_row.get("description", ""),
            version=skill_row.get("version", "1.0.0"),
            source_skill_id=skill_id,
            input_schema=config.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=config.get("output_schema", {"type": "object"}),
            risk_level=risk,
            permission_level=perm,
            requires_approval=approval,
            category=config.get("category", self._infer_category(skill_id)),
            tags=config.get("tags", [skill_id]),
            status=(CapabilityStatus.ENABLED
                    if skill_row.get("status") == "enabled"
                    else CapabilityStatus.DISABLED),
            config=config,
        )

    @staticmethod
    def _infer_security_level(skill_id: str, config: Dict[str, Any]
                              ) -> tuple[ToolRiskLevel, ToolPermissionLevel, bool]:
        """根据 Skill ID 和配置推断安全等级。"""
        sid = skill_id.lower()
        # 采集类 → HIGH + WRITE + 审批
        if any(k in sid for k in ("collect", "crawl", "browser")):
            return ToolRiskLevel.HIGH, ToolPermissionLevel.WRITE, True
        # 报告/分析类 → MEDIUM + ANALYZE
        if any(k in sid for k in ("report", "analyze", "generator", "brand")):
            return ToolRiskLevel.MEDIUM, ToolPermissionLevel.ANALYZE, False
        # 风险/告警类 → MEDIUM + READ
        if any(k in sid for k in ("risk", "alert", "kos")):
            return ToolRiskLevel.MEDIUM, ToolPermissionLevel.READ, False
        # 默认 → LOW + READ
        return ToolRiskLevel.LOW, ToolPermissionLevel.READ, False

    @staticmethod
    def _infer_category(skill_id: str) -> str:
        sid = skill_id.lower()
        if any(k in sid for k in ("collect", "crawl", "browser")):
            return "collection"
        if any(k in sid for k in ("report", "generator")):
            return "reports"
        if any(k in sid for k in ("analyze", "brand")):
            return "analysis"
        if any(k in sid for k in ("risk", "alert")):
            return "risk"
        if "kos" in sid:
            return "kos"
        return "general"

    # ── Capability 管理 ──────────────────────────────────────────

    def register_capability(self, cap: CapabilityMetadata) -> bool:
        """注册一个 Capability。"""
        if not self.enabled:
            return False
        self._capabilities[cap.capability_id] = cap
        return True

    def get_capability(self, capability_id: str) -> Optional[CapabilityMetadata]:
        return self._capabilities.get(capability_id)

    def list_capabilities(self, status: Optional[CapabilityStatus] = None,
                          category: Optional[str] = None) -> List[CapabilityMetadata]:
        caps = list(self._capabilities.values())
        if status:
            caps = [c for c in caps if c.status == status]
        if category:
            caps = [c for c in caps if c.category == category]
        return sorted(caps, key=lambda c: c.capability_id)

    def update_usage_stats(self, capability_id: str, success: bool,
                           duration_ms: float = 0.0) -> bool:
        """更新 Capability 使用统计。"""
        cap = self._capabilities.get(capability_id)
        if not cap:
            return False
        cap.usage_count += 1
        if success:
            cap.success_count += 1
        else:
            cap.failure_count += 1
        # 滑动平均耗时
        if cap.avg_duration_ms == 0:
            cap.avg_duration_ms = duration_ms
        else:
            cap.avg_duration_ms = cap.avg_duration_ms * 0.9 + duration_ms * 0.1
        return True

    # ── 导出为 Tool 定义 ─────────────────────────────────────────

    def to_tool_definitions(self) -> List[ToolDefinition]:
        """将所有已启用的 Capability 导出为 ToolDefinition（供 CapabilityRouter 注册）。"""
        return [
            cap.to_tool_definition()
            for cap in self._capabilities.values()
            if cap.status == CapabilityStatus.ENABLED
        ]

    def register_to_router(self, router) -> int:
        """将所有已启用的 Capability 注册到 CapabilityRouter。

        Returns:
            注册的 Tool 数量
        """
        if not self.enabled:
            return 0
        count = 0
        for cap in self._capabilities.values():
            if cap.status == CapabilityStatus.ENABLED:
                tool = cap.to_tool_definition()
                router.register_tool(tool)
                count += 1
        return count

    # ── 统计 ─────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        total = len(self._capabilities)
        enabled = sum(1 for c in self._capabilities.values()
                      if c.status == CapabilityStatus.ENABLED)
        by_category: Dict[str, int] = {}
        for c in self._capabilities.values():
            by_category[c.category] = by_category.get(c.category, 0) + 1
        return {
            "enabled": self.enabled,
            "total_capabilities": total,
            "enabled_capabilities": enabled,
            "loaded_from_db": self._loaded_from_db,
            "by_category": by_category,
        }

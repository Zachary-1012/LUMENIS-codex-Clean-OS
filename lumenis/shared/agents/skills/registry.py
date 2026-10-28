# -*- coding: utf-8 -*-
"""ZBC Phase 13 - Skill Registry & Metadata Model.

Skill boundary specification: every Skill must have complete metadata,
risk level, execution policy, and evidence contract.
Skills may not bypass permissions, write production data, execute
high-risk shell, modify system critical config, or bypass audit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionPolicy(str, Enum):
    READ_ONLY = "READ_ONLY"
    AUDIT_ONLY = "AUDIT_ONLY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    AUTO_EXECUTE = "AUTO_EXECUTE"


class EvaluationStatus(str, Enum):
    PLANNED = "PLANNED"
    PARTIAL = "PARTIAL"
    EVALUATED = "EVALUATED"
    DEPRECATED = "DEPRECATED"


SKILL_PROHIBITIONS: List[str] = [
    "bypass_permission_gate",
    "write_production_data",
    "execute_high_risk_shell",
    "modify_system_critical_config",
    "bypass_audit_trail",
    "escalate_privilege",
    "access_credentials_plaintext",
    "modify_subject_rules",
]

_HIGH_RISK_SHELL_PATTERNS = [
    r"\brm\s+-rf\b", r"\bsudo\b", r"\bformat\b", r"\bmkfs\b",
    r"\bdd\s+if=", r"\bchmod\s+777\b", r"\bchown\s+-R\s+root\b",
    r":\(\)\s*\{", r"\bwget\b.*\|\s*bash", r"\bcurl\b.*\|\s*sh",
]
_COMPILED_SHELL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _HIGH_RISK_SHELL_PATTERNS]


@dataclass
class SkillMetadata:
    skill_id: str
    version: str
    owner: str
    permission_level: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_level: RiskLevel
    execution_policy: ExecutionPolicy
    evidence_contract: str
    evaluation_status: EvaluationStatus
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    prohibited_actions: List[str] = field(default_factory=lambda: list(SKILL_PROHIBITIONS))
    product: str = "SYSTEM"
    domain: str = "system"
    cross_domain_allowed: List[str] = field(default_factory=list)
    category: str = "系统"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        d["execution_policy"] = self.execution_policy.value
        d["evaluation_status"] = self.evaluation_status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillMetadata":
        kw = dict(data)
        for enum_field, enum_cls in (
            ("risk_level", RiskLevel),
            ("execution_policy", ExecutionPolicy),
            ("evaluation_status", EvaluationStatus),
        ):
            v = kw.get(enum_field)
            if isinstance(v, str):
                kw[enum_field] = enum_cls(v)
        return cls(**kw)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: Dict[str, SkillMetadata] = {}
        self._validation_errors: List[str] = []

    def validate(self, meta: SkillMetadata) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        required_str = {
            "skill_id": meta.skill_id,
            "version": meta.version,
            "owner": meta.owner,
            "permission_level": meta.permission_level,
            "evidence_contract": meta.evidence_contract,
        }
        for fname, val in required_str.items():
            if not val or not isinstance(val, str) or not val.strip():
                errors.append(f"{fname} is required and must be non-empty string")

        if meta.skill_id and not re.match(r"^[a-z][a-z0-9_.]{2,63}$", meta.skill_id):
            errors.append(f"skill_id '{meta.skill_id}' invalid format")

        if meta.version and not re.match(r"^\d+\.\d+\.\d+", meta.version):
            warnings.append(f"version '{meta.version}' not semver-like")

        for schema_name in ("input_schema", "output_schema"):
            schema = getattr(meta, schema_name)
            if not isinstance(schema, dict):
                errors.append(f"{schema_name} must be a dict")
            elif not schema:
                errors.append(f"{schema_name} must not be empty")

        if meta.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            if meta.execution_policy == ExecutionPolicy.AUTO_EXECUTE:
                errors.append(
                    f"Skill '{meta.skill_id}': risk={meta.risk_level.value} "
                    f"cannot use AUTO_EXECUTE; must be APPROVAL_REQUIRED or stricter"
                )
        if meta.risk_level == RiskLevel.CRITICAL:
            if meta.execution_policy not in (
                ExecutionPolicy.APPROVAL_REQUIRED,
                ExecutionPolicy.AUDIT_ONLY,
            ):
                errors.append(
                    f"Skill '{meta.skill_id}': CRITICAL risk requires "
                    f"APPROVAL_REQUIRED or AUDIT_ONLY, got {meta.execution_policy.value}"
                )

        core_prohibitions = {
            "bypass_permission_gate", "write_production_data",
            "execute_high_risk_shell", "bypass_audit_trail",
        }
        missing = core_prohibitions - set(meta.prohibited_actions)
        if missing:
            errors.append(f"prohibited_actions missing core items: {sorted(missing)}")

        text_to_scan = " ".join([
            meta.description or "",
            meta.evidence_contract or "",
            str(meta.input_schema),
        ])
        for pat in _COMPILED_SHELL_PATTERNS:
            if pat.search(text_to_scan):
                errors.append(
                    f"Skill '{meta.skill_id}': metadata contains high-risk shell "
                    f"pattern '{pat.pattern}'"
                )

        known_levels = {
            "READ", "AUDIT", "ANALYZE", "RESEARCH", "PLAN",
            "PATCH_PREVIEW", "TEST", "VERIFY",
            "HUMAN_APPROVAL", "COMMIT", "PUSH",
        }
        if meta.permission_level and meta.permission_level not in known_levels:
            warnings.append(f"permission_level '{meta.permission_level}' not in known levels")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def register(self, meta: SkillMetadata, *, force: bool = False) -> Dict[str, Any]:
        result = self.validate(meta)
        if not result["valid"] and not force:
            self._validation_errors.extend(result["errors"])
            return {
                "registered": False,
                "skill_id": meta.skill_id,
                "errors": result["errors"],
                "warnings": result["warnings"],
            }
        self._skills[meta.skill_id] = meta
        return {
            "registered": True,
            "skill_id": meta.skill_id,
            "errors": [],
            "warnings": result["warnings"],
        }

    def get(self, skill_id: str) -> Optional[SkillMetadata]:
        return self._skills.get(skill_id)

    def has(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def list_all(self) -> List[SkillMetadata]:
        return list(self._skills.values())

    def list_by_risk(self, risk: RiskLevel) -> List[SkillMetadata]:
        return [s for s in self._skills.values() if s.risk_level == risk]

    def list_by_policy(self, policy: ExecutionPolicy) -> List[SkillMetadata]:
        return [s for s in self._skills.values() if s.execution_policy == policy]

    def list_requiring_approval(self) -> List[SkillMetadata]:
        return [
            s for s in self._skills.values()
            if s.execution_policy == ExecutionPolicy.APPROVAL_REQUIRED
            or s.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        ]

    def can_auto_execute(self, skill_id: str) -> Dict[str, Any]:
        meta = self._skills.get(skill_id)
        if meta is None:
            return {"allowed": False, "reason": f"skill '{skill_id}' not registered",
                    "policy": None, "risk": None}
        if meta.execution_policy != ExecutionPolicy.AUTO_EXECUTE:
            return {
                "allowed": False,
                "reason": f"execution_policy={meta.execution_policy.value}, requires approval/audit",
                "policy": meta.execution_policy.value,
                "risk": meta.risk_level.value,
            }
        if meta.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return {
                "allowed": False,
                "reason": f"risk={meta.risk_level.value} cannot auto-execute",
                "policy": meta.execution_policy.value,
                "risk": meta.risk_level.value,
            }
        return {"allowed": True, "reason": "OK",
                "policy": meta.execution_policy.value, "risk": meta.risk_level.value}

    def stats(self) -> Dict[str, Any]:
        by_risk = {r.value: 0 for r in RiskLevel}
        by_policy = {p.value: 0 for p in ExecutionPolicy}
        for s in self._skills.values():
            by_risk[s.risk_level.value] += 1
            by_policy[s.execution_policy.value] += 1
        return {
            "total": len(self._skills),
            "by_risk": by_risk,
            "by_policy": by_policy,
            "requiring_approval": len(self.list_requiring_approval()),
            "validation_errors_pending": len(self._validation_errors),
        }


_global_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
        _register_builtin_skills(_global_registry)
    return _global_registry


def _register_builtin_skills(reg: SkillRegistry) -> None:
    builtins = [
        SkillMetadata(
            skill_id="zbc.subject_authority_read",
            version="1.0.0",
            owner="core-team",
            permission_level="READ",
            input_schema={"type": "object", "properties": {}, "required": []},
            output_schema={"type": "object", "properties": {"subject_words_count": {"type": "integer"}}},
            risk_level=RiskLevel.LOW,
            execution_policy=ExecutionPolicy.READ_ONLY,
            evidence_contract="returns word counts and subject_hit presence, not contents; audit logged",
            evaluation_status=EvaluationStatus.EVALUATED,
            description="read-only subject authority status (counts only)",
            tags=["subject", "readonly", "authority"],
            product="SYSTEM", domain="system", category="开发者工具",
        ),
        SkillMetadata(
            skill_id="zbc.skill_registry_snapshot",
            version="1.0.0",
            owner="core-team",
            permission_level="READ",
            input_schema={"type": "object", "properties": {}, "required": []},
            output_schema={"type": "object", "properties": {"total": {"type": "integer"}}},
            risk_level=RiskLevel.LOW,
            execution_policy=ExecutionPolicy.READ_ONLY,
            evidence_contract="returns SkillRegistry.stats(), in-memory read only",
            evaluation_status=EvaluationStatus.EVALUATED,
            description="read-only skill registry stats snapshot",
            tags=["registry", "readonly"],
            product="SYSTEM", domain="system", category="开发者工具", cross_domain_allowed=["CTH", "BMP"],
        ),
        SkillMetadata(
            skill_id="zbc.agent_boundary_audit",
            version="1.0.0",
            owner="core-team",
            permission_level="AUDIT",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            output_schema={"type": "object", "properties": {"identity": {"type": "object"}}},
            risk_level=RiskLevel.LOW,
            execution_policy=ExecutionPolicy.READ_ONLY,
            evidence_contract="returns AgentIdentity snapshot and permission scope",
            evaluation_status=EvaluationStatus.EVALUATED,
            description="read-only agent boundary and permission audit",
            tags=["agent", "audit", "boundary"],
            product="SYSTEM", domain="system", category="开发者工具", cross_domain_allowed=["CTH", "BMP"],
        ),
    ]
    # The six user-specified creation/research tools are one shared capability
    # surface.  They are registered from the canonical catalog so the AI
    # surface, CTH and BMP consume the same IDs/permissions/evidence contract.
    # A missing optional adapter must not make the core registry unavailable.
    try:
        from lumenis_shared_skills import SHARED_SKILL_CATALOG
        for item in SHARED_SKILL_CATALOG:
            builtins.append(SkillMetadata.from_dict(item["metadata"]))
    except Exception:
        pass
    for b in builtins:
        reg.register(b)


if __name__ == "__main__":
    import json
    reg = get_skill_registry()
    print("=== SkillRegistry self-check ===")
    print(json.dumps(reg.stats(), ensure_ascii=False, indent=2))
    for s in reg.list_all():
        v = reg.validate(s)
        print(f"  {s.skill_id}: valid={v['valid']}, risk={s.risk_level.value}")
    print("self-check done")

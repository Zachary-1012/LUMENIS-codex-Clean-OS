# -*- coding: utf-8 -*-
"""ZBC/LUMENIS P1 — Skill Execution Chain (适配接入，不重写 skill_registry)。
执行链：Task → Permission → Agent → Skill → Tool → Action Firewall
       → Effect Fence → Execute → Evidence → Evaluation → Trace
"""
from __future__ import annotations
import json, traceback, uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class SkillState(str, Enum):
    REGISTERED = "registered"; ENABLED = "enabled"; RUNNING = "running"
    COMPLETED = "completed"; FAILED = "failed"; DISABLED = "disabled"

class ActionType(str, Enum):
    READ = "READ"; ANALYZE = "ANALYZE"; SUGGEST = "SUGGEST"
    EXPORT = "EXPORT"; WRITE = "WRITE"; COMMIT = "COMMIT"; PUSH = "PUSH"

class ExecutionStatus(str, Enum):
    PENDING = "pending"; RUNNING = "running"; COMPLETED = "completed"
    FAILED = "failed"; BLOCKED = "blocked"; REJECTED = "rejected"

_ACTION_POLICY = {
    ActionType.READ: "ALLOW", ActionType.ANALYZE: "ALLOW", ActionType.SUGGEST: "ALLOW",
    ActionType.EXPORT: "CONDITIONAL", ActionType.WRITE: "RESTRICTED",
    ActionType.COMMIT: "DENY", ActionType.PUSH: "DENY",
}

_VALID_TRANSITIONS = {
    SkillState.REGISTERED: {SkillState.ENABLED, SkillState.DISABLED},
    SkillState.ENABLED: {SkillState.RUNNING, SkillState.DISABLED},
    SkillState.RUNNING: {SkillState.COMPLETED, SkillState.FAILED, SkillState.DISABLED},
    SkillState.COMPLETED: {SkillState.ENABLED, SkillState.DISABLED},
    SkillState.FAILED: {SkillState.ENABLED, SkillState.DISABLED},
    SkillState.DISABLED: {SkillState.ENABLED},
}


@dataclass
class SkillExecutionContext:
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    skill_id: str = ""
    user_id: Optional[int] = None
    domain: str = "SYSTEM"
    product: str = "SYSTEM"
    task: str = ""
    input_payload: Dict[str, Any] = field(default_factory=dict)
    action_type: ActionType = ActionType.ANALYZE
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    permission_result: Optional[Dict[str, Any]] = None
    firewall_result: Optional[Dict[str, Any]] = None
    effect_fence_result: Optional[Dict[str, Any]] = None
    execute_result: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    error: Optional[str] = None
    def to_dict(self):
        d = asdict(self); d["action_type"] = self.action_type.value; d["status"] = self.status.value
        return d

@dataclass
class SkillRuntimeInfo:
    skill_id: str; name: str = ""; description: str = ""
    product: str = "SYSTEM"; domain: str = "global"; version: str = "1.0.0"
    state: SkillState = SkillState.REGISTERED
    enabled: bool = False
    config: Dict[str, Any] = field(default_factory=dict)
    cross_domain_allowed: List[str] = field(default_factory=list)
    source: str = "builtin"
    def to_dict(self):
        d = asdict(self); d["state"] = self.state.value; return d


def check_permission(ctx, user_role="user", skill_info=None):
    if skill_info and not skill_info.enabled:
        return {"allowed": False, "reason": f"skill '{ctx.skill_id}' is disabled", "code": "SKILL_DISABLED"}
    if skill_info and skill_info.product != "SHARED":
        caller = ctx.product.upper(); sk = skill_info.product.upper()
        if caller != sk and caller != "SYSTEM":
            if caller not in [a.upper() for a in skill_info.cross_domain_allowed]:
                return {"allowed": False, "reason": f"cross-domain denied: caller={caller}, skill={sk}",
                        "code": "CROSS_DOMAIN_DENIED"}
    if user_role not in ("owner", "admin"):
        if ctx.action_type in (ActionType.WRITE, ActionType.COMMIT, ActionType.PUSH):
            return {"allowed": False, "reason": f"role '{user_role}' cannot execute {ctx.action_type.value}",
                    "code": "INSUFFICIENT_ROLE"}
    return {"allowed": True, "reason": "OK", "code": "PERMISSION_GRANTED"}


def _check_sensitive_data(payload):
    sensitive = {"password", "token", "api_key", "secret", "cookie", "session", "private_key", "credential", "phone", "id_card"}
    text = json.dumps(payload, ensure_ascii=False).lower()
    return any(k in text for k in sensitive)


def action_firewall(ctx, extra_policy=None):
    """Action Firewall：P1 基础策略 + P2 深度校验链。"""
    policy = dict(_ACTION_POLICY)
    if extra_policy: policy.update(extra_policy)
    decision = policy.get(ctx.action_type, "DENY")

    # P2 深度校验链（可选接入）
    p2_result = None
    try:
        from p2_action_firewall import validate_action as p2_validate, ActionRequest, AgentAction
        try: p2_action = AgentAction(ctx.action_type.value)
        except ValueError: p2_action = AgentAction.ANALYZE
        p2_req = ActionRequest(
            identity=f"skill_executor:{ctx.execution_id}",
            intent=ctx.task or f"execute skill {ctx.skill_id}",
            tool=f"skill:{ctx.skill_id}", parameters=ctx.input_payload,
            target=ctx.input_payload.get("target", "staging"), scope=ctx.domain,
            action=p2_action, user_role="owner")
        p2_result = p2_validate(p2_req)
    except Exception:
        p2_result = None

    if p2_result is not None and not p2_result.allowed:
        return {"allowed": False, "action": ctx.action_type.value, "decision": p2_result.decision,
                "reason": p2_result.reason, "code": "P2_FIREWALL_DENY",
                "p2_checks": p2_result.checks, "requires_approval": p2_result.requires_approval}

    if decision == "ALLOW":
        return {"allowed": True, "action": ctx.action_type.value, "decision": "ALLOW",
                "reason": "action type permitted", "p2_passed": p2_result is not None}
    elif decision == "CONDITIONAL":
        if _check_sensitive_data(ctx.input_payload):
            return {"allowed": False, "action": ctx.action_type.value, "decision": "DENY",
                    "reason": "export contains sensitive data", "code": "EXPORT_SENSITIVE"}
        return {"allowed": True, "action": ctx.action_type.value, "decision": "CONDITIONAL_PASS",
                "reason": "export without sensitive data"}
    elif decision == "RESTRICTED":
        return {"allowed": True, "action": ctx.action_type.value, "decision": "RESTRICTED",
                "reason": "write allowed only through Effect Fence", "requires_effect_fence": True,
                "p2_passed": p2_result is not None}
    else:
        return {"allowed": False, "action": ctx.action_type.value, "decision": "DENY",
                "reason": f"action type {ctx.action_type.value} is denied by default", "code": "ACTION_DENIED"}


def effect_fence(ctx):
    writes = ctx.action_type in (ActionType.WRITE, ActionType.COMMIT, ActionType.PUSH)
    return {"fenced": True, "writes_production": writes, "staging_required": writes,
            "auto_admit": False,
            "validation_status": "pending_validation" if writes else "read_only_pass",
            "reason": "results staged; production admission requires Evidence -> Evaluation -> manual validation"
            if writes else "read-only action, no production side effect"}


def execute_skill(ctx, handler=None):
    if handler is not None:
        try:
            return {"success": True, "result": handler(ctx), "source": "custom_handler"}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()[-500:], "source": "custom_handler"}
    try:
        from lumenis_skill_adapter import get_skill_adapter
        adapter = get_skill_adapter()
        if adapter.available:
            osai_result = adapter.invoke_skill(
                task=ctx.task or json.dumps(ctx.input_payload, ensure_ascii=False),
                skill_id=ctx.skill_id,
                user_permissions=["READ", "AUDIT", "ANALYZE", "RESEARCH", "PLAN", "PATCH_PREVIEW", "TEST", "VERIFY"],
                timeout=60.0)
            if osai_result.get("connected"):
                return {"success": True, "result": osai_result.get("osai"), "source": "osai_adapter"}
            # OSAI 不可用，回退到内置本地
    except Exception:
        pass
    try:
        from skill_registry import get_skill_registry
        reg = get_skill_registry()
        meta = reg.get(ctx.skill_id)
        if meta:
            local = _execute_builtin_local(ctx, meta)
            if local is not None:
                return {"success": True, "result": local, "source": "builtin_local"}
    except Exception:
        pass
    return {"success": False, "error": "no executable handler available", "source": "none", "code": "NO_HANDLER"}


def _execute_builtin_local(ctx, meta):
    sid = ctx.skill_id
    if sid == "zbc.subject_authority_read":
        try:
            from skill_registry import get_skill_registry
            return {"subject_words_count": 0, "registry_total": get_skill_registry().stats().get("total", 0)}
        except Exception: return None
    elif sid == "zbc.skill_registry_snapshot":
        try:
            from skill_registry import get_skill_registry
            return get_skill_registry().stats()
        except Exception: return None
    elif sid == "zbc.agent_boundary_audit":
        return {"identity": {"agent_id": ctx.execution_id, "role": "skill_executor"},
                "permission_scope": ["READ", "ANALYZE"]}
    return None


def _stable_hash(obj):
    import hashlib
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]

def _summarize(obj, max_len=200):
    if obj is None: return ""
    text = json.dumps(obj, ensure_ascii=False, default=str)
    return text[:max_len] + ("..." if len(text) > max_len else "")

def build_evidence(ctx):
    return {"execution_id": ctx.execution_id, "skill_id": ctx.skill_id, "timestamp": ctx.timestamp,
            "input_hash": _stable_hash(ctx.input_payload),
            "output_summary": _summarize(ctx.execute_result),
            "permission": ctx.permission_result, "firewall": ctx.firewall_result,
            "effect_fence": ctx.effect_fence_result,
            "source": ctx.execute_result.get("source") if ctx.execute_result else None}

def evaluate_execution(ctx):
    exec_res = ctx.execute_result or {}
    success = exec_res.get("success", False)
    return {"evaluated": True, "success": success, "quality_score": 0.8 if success else 0.0,
            "auto_admitted": False,
            "validation_required": ctx.action_type in (ActionType.WRITE, ActionType.COMMIT, ActionType.PUSH),
            "validation_status": "pending_manual_validation" if success else "failed_no_validation",
            "reason": "execution completed; requires manual validation" if success else "execution failed"}


def ensure_skill_executions_table():
    try:
        from account.models import get_db
        conn = get_db()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS skill_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL, skill_id TEXT NOT NULL, user_id INTEGER,
                domain TEXT DEFAULT 'SYSTEM', product TEXT DEFAULT 'SYSTEM', task TEXT,
                action_type TEXT DEFAULT 'ANALYZE', input_json TEXT, output_json TEXT,
                status TEXT DEFAULT 'pending', error TEXT, evidence_json TEXT, evaluation_json TEXT,
                permission_json TEXT, firewall_json TEXT, effect_fence_json TEXT,
                duration_ms INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')))""")
            conn.commit()
        finally: conn.close()
    except Exception: pass

def write_trace(ctx, duration_ms=0):
    try:
        from account.models import get_db
        conn = get_db()
        try:
            conn.execute("""INSERT OR REPLACE INTO skill_executions
                (execution_id, skill_id, user_id, domain, product, task, action_type,
                 input_json, output_json, status, error, evidence_json, evaluation_json,
                 permission_json, firewall_json, effect_fence_json, duration_ms)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                ctx.execution_id, ctx.skill_id, ctx.user_id, ctx.domain, ctx.product,
                ctx.task, ctx.action_type.value,
                json.dumps(ctx.input_payload, ensure_ascii=False, default=str)[:4000],
                json.dumps(ctx.execute_result, ensure_ascii=False, default=str)[:4000] if ctx.execute_result else None,
                ctx.status.value, ctx.error,
                json.dumps(ctx.evidence, ensure_ascii=False, default=str)[:4000] if ctx.evidence else None,
                json.dumps(ctx.evaluation, ensure_ascii=False, default=str)[:4000] if ctx.evaluation else None,
                json.dumps(ctx.permission_result, ensure_ascii=False, default=str)[:2000] if ctx.permission_result else None,
                json.dumps(ctx.firewall_result, ensure_ascii=False, default=str)[:2000] if ctx.firewall_result else None,
                json.dumps(ctx.effect_fence_result, ensure_ascii=False, default=str)[:2000] if ctx.effect_fence_result else None,
                duration_ms))
            conn.commit(); return True
        finally: conn.close()
    except Exception: return False

def query_executions(skill_id=None, limit=50, status=None):
    try:
        from account.models import get_db
        conn = get_db()
        try:
            sql = "SELECT * FROM skill_executions"; conds = []; params = []
            if skill_id: conds.append("skill_id=?"); params.append(skill_id)
            if status: conds.append("status=?"); params.append(status)
            if conds: sql += " WHERE " + " AND ".join(conds)
            sql += " ORDER BY created_at DESC LIMIT ?"; params.append(limit)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally: conn.close()
    except Exception: return []

def transition_state(current, target):
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target in allowed: return True, f"{current.value} -> {target.value}"
    return False, f"invalid transition: {current.value} -> {target.value}"


def record_execution_evidence(ctx):
    """连接点a: skill_execution_chain -> evidence_chain 桥接。
    执行链完成后将执行证据写入 evidence_chain.EvidenceStore (zbc_evidence表)，
    走 Contract/Artifact 边界。失败不阻断主链路（旁路记录）。
    """
    try:
        from evidence_chain import EvidenceStore
        store = EvidenceStore()
        exec_res = ctx.execute_result or {}
        raw_content = json.dumps({
            "execution_id": ctx.execution_id,
            "skill_id": ctx.skill_id,
            "task": ctx.task,
            "action_type": ctx.action_type.value,
            "input_payload": ctx.input_payload,
            "execute_result": exec_res,
            "status": ctx.status.value,
            "error": ctx.error,
        }, ensure_ascii=False, default=str)
        ev, is_new = store.add_evidence(
            source_type="skill_execution",
            source_url=f"skill://{ctx.skill_id}/{ctx.execution_id}",
            source_id=ctx.execution_id,
            raw_content=raw_content,
            subject_scope=ctx.domain or "SYSTEM",
            task_id=ctx.execution_id,
            trace_id=ctx.execution_id,
            collection_metadata={
                "skill_id": ctx.skill_id,
                "action_type": ctx.action_type.value,
                "status": ctx.status.value,
                "permission": ctx.permission_result,
                "firewall": ctx.firewall_result,
                "effect_fence": ctx.effect_fence_result,
                "evaluation": ctx.evaluation,
            },
            provider="skill_execution_chain",
            domain_id=ctx.domain or "system",
            product_id=ctx.product or "SYSTEM",
        )
        return {"ok": True, "evidence_id": ev.evidence_id, "is_new": is_new}
    except Exception as e:
        return {"ok": False, "error": str(e), "note": "evidence bridge failed, main chain unaffected"}


def run_execution_chain(skill_id, task="", input_payload=None, action_type=ActionType.ANALYZE,
                        user_id=None, user_role="user", product="SYSTEM", domain="global",
                        skill_info=None, handler=None):
    import time
    start = time.time()
    ctx = SkillExecutionContext(skill_id=skill_id, task=task, input_payload=input_payload or {},
                                 action_type=action_type, user_id=user_id, product=product, domain=domain)
    ctx.permission_result = check_permission(ctx, user_role=user_role, skill_info=skill_info)
    if not ctx.permission_result["allowed"]:
        ctx.status = ExecutionStatus.REJECTED; ctx.error = ctx.permission_result["reason"]
        write_trace(ctx, int((time.time() - start) * 1000)); return ctx
    ctx.firewall_result = action_firewall(ctx)
    if not ctx.firewall_result["allowed"]:
        ctx.status = ExecutionStatus.REJECTED; ctx.error = ctx.firewall_result.get("reason", "action denied")
        write_trace(ctx, int((time.time() - start) * 1000)); return ctx
    ctx.effect_fence_result = effect_fence(ctx)
    ctx.status = ExecutionStatus.RUNNING
    ctx.execute_result = execute_skill(ctx, handler=handler)
    ctx.evidence = build_evidence(ctx)
    ctx.evidence_record = record_execution_evidence(ctx)
    ctx.evaluation = evaluate_execution(ctx)
    if ctx.execute_result.get("success"):
        ctx.status = ExecutionStatus.COMPLETED
    else:
        ctx.status = ExecutionStatus.FAILED; ctx.error = ctx.execute_result.get("error", "execution failed")
    write_trace(ctx, int((time.time() - start) * 1000))
    return ctx

def get_skills_light_status(product=None):
    results = []
    try:
        from account.skills import list_skills
        for s in list_skills(product=product, status="enabled"):
            results.append({"skill_id": s["skill_id"], "name": s.get("name", s["skill_id"]),
                "description": s.get("description", ""), "product": s.get("product", "SYSTEM"),
                "domain": s.get("domain", "global"), "status": "enabled", "state": "enabled",
                "version": s.get("version", "1.0"), "source": "db"})
    except Exception: pass
    try:
        from skill_registry import get_skill_registry
        existing = {r["skill_id"] for r in results}
        for meta in get_skill_registry().list_all():
            if meta.skill_id in existing: continue
            results.append({"skill_id": meta.skill_id, "name": meta.skill_id.replace("zbc.", "").replace("_", " ").title(),
                "description": meta.description, "product": getattr(meta, "product", "SYSTEM"),
                "domain": getattr(meta, "domain", "global"), "status": "registered", "state": "registered",
                "version": meta.version, "risk_level": meta.risk_level.value, "source": "builtin_registry"})
    except Exception: pass
    return results

ensure_skill_executions_table()

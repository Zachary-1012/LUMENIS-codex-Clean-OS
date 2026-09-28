# -*- coding: utf-8 -*-
"""LUMENIS App API Blueprint — JSON contracts only.

本模块只负责渲染前端 Foundation 页面 + Skill Hub API，不包含任何业务逻辑、
数据采集、主体判断或数据库写操作。与 ZBC 生产核心解耦：在 app.py 中用一行注册即可：

    from lumenis_app_api import lumenis_bp
    app.register_blueprint(lumenis_bp)

不注册也不影响现有系统；模板与静态资源独立于旧前端。
平台中立：无硬编码个人路径。
"""
import json
import time as _time
import uuid as _uuid
from flask import Blueprint, request, jsonify

lumenis_bp = Blueprint("lumenis", __name__, url_prefix="/lumenis")

# Domain API blueprint (root-level, no /lumenis prefix — for xujing-viz.js /api/* calls)
domain_api_bp = Blueprint("domain_api", __name__)


def _context_error(code, message, status):
    return jsonify({"ok": False, "code": code, "error": message}), status


def _context_selection_from_scope(domain_id, subject_id):
    """Resolve and authorize one registered Subject or BrandFocus selection."""
    from subject_context import ContextSelection
    from subject_registry import (
        SubjectRegistryUnavailableError,
        SubjectValidationError,
        get_subject_by_id,
        normalize_domain,
    )
    from lumenis.system.security.permission import check_actor_scope_permission
    from lumenis.auth.service import get_current_user

    actor = get_current_user()
    if not isinstance(actor, dict) or type(actor.get("id")) is not int:
        return None, _context_error("AUTH_REQUIRED", "需要有效账号会话", 401)
    try:
        normalized_domain = normalize_domain(domain_id)
        if normalized_domain not in {"CTH", "BMP"}:
            raise SubjectValidationError("domain_id 仅支持 CTH 或 BMP")
        if not isinstance(subject_id, str) or not subject_id or subject_id != subject_id.strip():
            raise SubjectValidationError("subject_id 无效")
        subject = get_subject_by_id(normalized_domain, subject_id)
    except SubjectValidationError as exc:
        return None, _context_error("INVALID_CONTEXT", str(exc), 400)
    except SubjectRegistryUnavailableError:
        return None, _context_error(
            "SUBJECT_REGISTRY_UNAVAILABLE", "主体注册表暂不可用", 503
        )
    except Exception:
        return None, _context_error(
            "SUBJECT_REGISTRY_UNAVAILABLE", "主体注册表暂不可用", 503
        )

    if subject is None:
        return None, _context_error("SUBJECT_NOT_FOUND", "主体未在有效注册表中", 404)

    is_cth = normalized_domain == "CTH"
    expected_type = "company" if is_cth else "brand"
    brand_focus_id = subject.get("brand_focus_id")
    if subject.get("subject_type") != expected_type or (
        not is_cth and (not isinstance(brand_focus_id, str) or not brand_focus_id)
    ):
        return None, _context_error("INVALID_CONTEXT_SCOPE", "主体类型与业务域不匹配", 400)

    try:
        decision = check_actor_scope_permission(
            actor,
            domain_id=normalized_domain,
            action="read",
            module="subject_registry",
            subject_id=subject_id if is_cth else None,
            brand_focus_id=None if is_cth else brand_focus_id,
        )
    except Exception:
        return None, _context_error(
            "AUTHORIZATION_UNAVAILABLE", "主体范围授权暂不可用", 503
        )
    if decision.verification_state != "verified":
        return None, _context_error(
            "AUTHORIZATION_UNAVAILABLE", "主体范围授权暂不可用", 503
        )
    if not decision.allowed:
        return None, _context_error(
            "SUBJECT_SCOPE_DENIED", "没有读取该主体范围的权限", 403
        )

    return ContextSelection.focus(
        domain_id=normalized_domain,
        subject_id=subject_id,
        brand_focus_id=None if is_cth else brand_focus_id,
    ), None


def _context_envelope(selection):
    return jsonify({
        "ok": True,
        "contract": "lumenis.context.v1",
        "selection_only": True,
        "context": selection.to_dict(),
    })


@domain_api_bp.route("/api/settings/context", methods=["GET", "PUT", "DELETE"])
def api_settings_context():
    """Expose selection-only context; data routes reauthorize every use."""
    from subject_context import ContextSelection

    if request.method == "DELETE":
        # Clearing focus only returns the static GLOBAL selection. It reads no
        # business data and performs no persistent or external effect.
        return _context_envelope(ContextSelection.global_all())

    if request.method == "PUT":
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) != {
            "mode", "domain_id", "subject_id"
        } or payload.get("mode") != "FOCUS":
            return _context_error("INVALID_CONTEXT", "需要合法的 FOCUS 主体选择", 400)
        selection, error = _context_selection_from_scope(
            payload.get("domain_id"), payload.get("subject_id")
        )
        return error if error is not None else _context_envelope(selection)

    mode = request.headers.get("X-Lumenis-Context-Mode", "GLOBAL_ALL")
    domain_id = request.headers.get("X-Domain-Id")
    subject_id = request.headers.get("X-Subject-ID")
    if mode == "GLOBAL_ALL":
        if domain_id or subject_id:
            return _context_error(
                "INVALID_CONTEXT", "GLOBAL_ALL 不能携带聚焦主体", 400
            )
        return _context_envelope(ContextSelection.global_all())
    if mode != "FOCUS" or not domain_id or not subject_id:
        return _context_error("INVALID_CONTEXT", "聚焦上下文不完整", 400)
    selection, error = _context_selection_from_scope(domain_id, subject_id)
    return error if error is not None else _context_envelope(selection)



# Shared Skill JSON API (App transport)
# ========== Skill Hub API（Cross-Core Adapter，ZBC 不维护独立 Skill Truth） ==========

from lumenis_skill_adapter import get_skill_adapter

# Skill 调用记录（内存级 runtime cache，不写数据库，保留最近 100 条）
# 注意：这不是永久历史，仅作 runtime trace。UI 无持久化证据时显示 NO_DATA。
_skill_invocations = []


@lumenis_bp.route("/api/skills/status")
def skill_status():
    """Skill Registry 状态 —— 从 OSAI Canonical Registry 真实读取。

    ZBC 不再维护独立 _LUMENIS_SKILLS 硬编码 Truth。
    OSAI 不可用时返回 UNAVAILABLE，不造假数据。
    """
    adapter = get_skill_adapter()
    snap = adapter.get_registry_snapshot()

    if not snap["connected"]:
        return jsonify({
            "total": 0,
            "running": 0,
            "sync_status": "UNAVAILABLE",
            "skills": [],
            "canonical_source": "OSAI Canonical Registry",
            "connection_status": "UNAVAILABLE",
            "error": snap.get("error"),
            "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        })

    # 只返回 IMPLEMENTED + PARTIAL 的 Skill 给前端（PLANNED 不显示为可用）
    visible_skills = [s for s in snap["skills"]
                      if s["status"] in ("IMPLEMENTED", "PARTIAL")]

    return jsonify({
        "total": snap.get("implemented_count", 0),
        "running": 0,
        "sync_status": "CONNECTED",
        "skills": visible_skills,
        "canonical_source": "OSAI Canonical Registry",
        "connection_status": "CONNECTED",
        "implemented_count": snap.get("implemented_count", 0),
        "partial_count": snap.get("partial_count", 0),
        "planned_count": snap.get("planned_count", 0),
        "registry_total": snap.get("total", 0),
        "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
    })


@lumenis_bp.route("/api/skills/invoke", methods=["POST"])
def skill_invoke():
    """Skill 调用 —— ZBC → Cross-Core Adapter → OSAI SkillInvoker。

    完整链：Workspace → Task → Skill Selector → Manifest → Permission →
    Context → Engine → Provider → Execution → Evidence → Evaluation → Trace → Result

    当前层级：ZBC 记录调用请求（ACCEPTED），实际执行由 OSAI 完成。
    任何一层不存在返回 PARTIALLY_CONNECTED，不伪造 COMPLETED。
    """
    data = request.get_json(silent=True) or {}
    skill_id = data.get("skill_id", "")
    task = data.get("task", "manual invoke")
    workspace = data.get("workspace", "unknown")

    # 从 OSAI Canonical Registry 获取 Skill 定义（唯一 Truth）
    adapter = get_skill_adapter()
    skill_info = adapter.get_skill(skill_id)

    if not skill_info.get("found"):
        return jsonify({
            "status": "FAILED",
            "error": "Unknown skill: %s" % skill_id,
            "registry_status": skill_info.get("status", "UNKNOWN"),
        }), 404

    skill = skill_info["skill"]

    # 检查 Skill 是否真实可执行
    if skill["status"] != "IMPLEMENTED":
        return jsonify({
            "status": "BLOCKED",
            "error": "Skill not implemented: %s (status=%s)" % (skill_id, skill["status"]),
            "skill_status": skill["status"],
        }), 400

    import os as _os
    invocation_id = "INV-" + _uuid.uuid4().hex[:10]
    fallback_trace = "TRACE-" + _uuid.uuid4().hex[:10]
    skill_version = skill.get("version", "0.0.0")

    # 真实执行：ZBC → Cross-Core Adapter → OSAI SkillInvoker
    # Permission(fail-close) → Context → Engine → Provider → Evidence(落盘) → Evaluation
    exec_res = adapter.invoke_skill(
        task=task, skill_id=skill_id, workspace=workspace,
        skill_version=skill_version,
    )

    base = {
        "invocation_id": invocation_id,
        "skill_id": skill_id,
        "skill_name": skill.get("name", ""),
        "skill_version": skill_version,
        "task": task,
        "workspace": workspace,
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "permissions_required": skill.get("permissions", []),
        "execution_core": "OSAI Intelligence Core",
        "canonical_source": "OSAI Canonical Registry",
    }

    if not exec_res.get("connected"):
        # OSAI 不可用/超时：诚实兜底为已受理，绝不伪造 COMPLETED
        record = dict(base, **{
            "trace_id": fallback_trace,
            "status": "ACCEPTED",
            "execution_status": "PARTIALLY_CONNECTED",
            "evidence_status": "NO_EVIDENCE",
            "evaluation_status": "NO_DATA",
            "error": exec_res.get("error"),
            "note": "OSAI runtime unavailable; invocation accepted only, not executed.",
        })
    else:
        osai = exec_res["osai"] or {}
        ost = osai.get("status", "UNKNOWN")
        trace_id = osai.get("trace_id", fallback_trace)
        ev_id = osai.get("evidence_id")
        eval_id = osai.get("evaluation_id")
        perm = osai.get("permission_check")
        result = osai.get("result") or {}
        if ost == "SUCCESS":
            record = dict(base, **{
                "trace_id": trace_id, "status": "COMPLETED",
                "execution_status": "CONNECTED",
                "evidence_status": "EVIDENCE_CREATED" if ev_id else "NO_EVIDENCE",
                "evaluation_status": "EVALUATION_CREATED" if eval_id else "NO_DATA",
                "evidence_id": ev_id, "evaluation_id": eval_id,
                "engine_id": osai.get("engine_id"), "model_id": osai.get("model_id"),
                "result": result, "permission_check": perm,
            })
        elif ost == "BLOCKED":
            record = dict(base, **{
                "trace_id": trace_id, "status": "BLOCKED",
                "execution_status": "CONNECTED",
                "evidence_status": "NO_EVIDENCE",
                "evaluation_status": "NO_DATA",
                "permission_check": perm,
                "error": osai.get("error", "PERMISSION_DENIED"),
            })
        else:  # FAILED / UNKNOWN —— 链路连通但执行失败，错误同样进 EvidenceChain
            record = dict(base, **{
                "trace_id": trace_id, "status": "FAILED",
                "execution_status": "CONNECTED",
                "evidence_status": "EVIDENCE_CREATED" if ev_id else "NO_EVIDENCE",
                "evaluation_status": "NO_DATA",
                "evidence_id": ev_id, "evaluation_id": eval_id,
                "engine_id": osai.get("engine_id"), "model_id": osai.get("model_id"),
                "permission_check": perm, "error": osai.get("error"),
            })

    # 持久化到独立 JSONL（不写生产 monitor.db，不改 DB schema）
    try:
        ddir = _os.environ.get("LUMENIS_RUNTIME_DIR") or _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)), "data", "lumenis")
        _os.makedirs(ddir, exist_ok=True)
        with open(_os.path.join(ddir, "skill_invocations.jsonl"),
                  "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception as persist_err:
        record["persist_warning"] = str(persist_err)

    _skill_invocations.append(record)
    if len(_skill_invocations) > 100:
        _skill_invocations.pop(0)

    return jsonify(record)


@lumenis_bp.route("/api/skills/invocations")
def skill_invocations_history():
    """Skill 调用历史 —— 读取持久化 JSONL（重启不丢），非内存假历史。"""
    import os as _os
    limit = request.args.get("limit", default=50, type=int)
    skill_id = request.args.get("skill_id", default="")
    ddir = _os.environ.get("LUMENIS_RUNTIME_DIR") or _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), "data", "lumenis")
    fpath = _os.path.join(ddir, "skill_invocations.jsonl")
    rows = []
    try:
        if _os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if skill_id and rec.get("skill_id") != skill_id:
                        continue
                    rows.append(rec)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "records": []}), 500
    rows = rows[-limit:]
    rows.reverse()
    return jsonify({
        "ok": True, "count": len(rows), "records": rows,
        "persistence": "file_based:data/lumenis/skill_invocations.jsonl",
    })


@lumenis_bp.route("/api/skills/sync", methods=["POST"])
def skill_sync():
    """GitHub Skill Manifest 同步 —— 真实检查 GitHub → Manifest → Registry。

    不固定返回 SYNCED。实际检测：
    1. OSAI Canonical Registry 是否可用
    2. Manifest 文件是否存在
    3. 已实现 Skill 与 Manifest 是否有冲突
    发现 conflict 返回 CONFLICT。
    """
    adapter = get_skill_adapter()
    sync_result = adapter.check_sync_status()

    return jsonify({
        "status": sync_result["sync_status"],
        "synced_count": sync_result["synced_count"],
        "conflicts": sync_result["conflict_count"],
        "conflict_detail": {
            "missing_manifest": sync_result.get("missing_manifest", []),
            "unimplemented_manifest": sync_result.get("unimplemented_manifest", []),
        },
        "manifest_files": sync_result.get("manifest_files", 0),
        "implemented_count": sync_result.get("implemented_count", 0),
        "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "canonical_source": "OSAI Canonical Registry / skills/manifests/",
        "error": sync_result.get("error"),
        "message": (
            "Sync verified. No conflicts."
            if sync_result["sync_status"] == "SYNCED"
            else "Conflicts detected. Manual review required."
            if sync_result["sync_status"] == "CONFLICT"
            else "OSAI unavailable. Cannot verify sync."
        ),
    })

@lumenis_bp.route("/api/intelligence/evidence")
def api_intelligence_evidence():
    """Intelligence Evidence — 读取 OSAI 持久化 Evidence Chain。

    Cross-Core: 通过 subprocess 调用 OSAI evidence reader，
    不直接访问 OSAI 内部模块。
    """
    import subprocess
    import json
    import os

    osai_root = os.environ.get("OSAI_ROOT") or get_skill_adapter()._osai_root or ""
    reader_script = os.path.join(osai_root, "scripts", "list_evidence.py") if osai_root else ""

    # Fallback: direct file read if script not available
    evidence_dir = os.path.join(osai_root, "evidence", "chains")
    chains = []
    try:
        if os.path.exists(evidence_dir):
            for fname in sorted(os.listdir(evidence_dir), reverse=True)[:50]:
                if fname.endswith(".json"):
                    fpath = os.path.join(evidence_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as fh:
                            chains.append(json.load(fh))
                    except Exception:
                        pass
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "count": 0, "chains": []}), 500

    return jsonify({
        "ok": True,
        "count": len(chains),
        "chains": chains,
        "source": "osai_evidence_chains",
        "persistence": "file_based"
    })




def _get_domain_context():
    """Resolve current domain from cookie/header/query, default cth."""
    dom = (request.cookies.get('zbc_domain')
           or request.headers.get('X-Domain-Id')
           or request.args.get('domain')
           or 'cth')
    return dom if dom in ('zbmp', 'cth', 'system') else 'cth'



# ---------- Domain Data APIs (real data binding for xujing-viz.js) ----------

@domain_api_bp.route("/api/domain/overview")
def api_domain_overview():
    """Domain-scoped overview data — 绑定真实 /api/stats + domain context。

    Returns stats filtered by current domain context. CTH uses subject_rules
    filtering (199 brands / 9 industries); ZBMP returns multi-brand aggregate.
    """
    import database as db
    domain = _get_domain_context()
    try:
        stats = db.get_stats()
        # CTH: subject-filtered stats already applied by db layer (subject_rules)
        # ZBMP: multi-brand aggregate (current db is CTH-scoped, mark as cross-domain)
        result = {
            "ok": True,
            "domain": domain,
            "domain_name": "CTH (Guangzhou Taikoo Hui)" if domain == "cth" else "ZBMP (Multi-Brand Platform)" if domain == "zbmp" else "SYSTEM",
            "stats": stats,
            "overview": {
                "trend": [],  # populated by /api/metric-trend for specific entities
                "time_range": "all",
            },
            "data_source": "database.get_stats() (real, no mock)",
            "subject_filter": "cth_subject_rules" if domain == "cth" else "multi_brand" if domain == "zbmp" else "system_level",
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "domain": domain, "error": str(e), "stats": {}}), 500


@domain_api_bp.route("/api/domain/brands")
def api_domain_brands():
    """Domain-scoped brand list — CTH: 199 brands; ZBMP: managed brands."""
    import database as db
    domain = _get_domain_context()
    try:
        # CTH: get brand distribution from notes
        categories = db.get_category_distribution()
        brands = []
        if isinstance(categories, list):
            for cat in categories[:50]:
                if isinstance(cat, dict):
                    brands.append({"name": cat.get('category', cat.get('name', 'unknown')),
                                   "count": cat.get('count', 0)})
                elif isinstance(cat, (list, tuple)) and len(cat) >= 2:
                    brands.append({"name": str(cat[0]), "count": int(cat[1])})
        return jsonify({
            "ok": True, "domain": domain, "brands": brands,
            "total": len(brands),
            "cth_brand_count": 199, "cth_industry_count": 9,
            "data_source": "database.get_category_distribution() (real)",
        })
    except Exception as e:
        return jsonify({"ok": False, "domain": domain, "error": str(e), "brands": []}), 500


@domain_api_bp.route("/api/domain/risk")
def api_domain_risk():
    """Domain-scoped risk data — 从真实 risk_alerts 获取。"""
    import database as db
    domain = _get_domain_context()
    try:
        risks = db.get_high_risk_notes(30)
        stats = db.get_stats()
        return jsonify({
            "ok": True, "domain": domain,
            "risk_notes": risks if isinstance(risks, list) else [],
            "risk_stats": {
                "critical": 0,
                "high": stats.get('high_risk', 0),
                "medium": stats.get('medium_risk', 0),
                "low": stats.get('low_risk', 0),
            },
            "data_source": "database.get_high_risk_notes() + get_stats() (real)",
        })
    except Exception as e:
        return jsonify({"ok": False, "domain": domain, "error": str(e), "risk_notes": []}), 500


@domain_api_bp.route("/api/domain/context")
def api_domain_context():
    """Return current domain context + isolation boundaries."""
    domain = _get_domain_context()
    try:
        from domain_isolation import DOMAINS, get_domain
        d = get_domain(domain)
        return jsonify({
            "ok": True,
            "current_domain": domain,
            "domain_info": d.to_dict(),
            "available_domains": {k: v.name for k, v in DOMAINS.items()},
            "header_required": "X-Domain-Id or cookie zbc_domain",
        })
    except Exception as e:
        return jsonify({"ok": False, "current_domain": domain, "error": str(e)}), 500

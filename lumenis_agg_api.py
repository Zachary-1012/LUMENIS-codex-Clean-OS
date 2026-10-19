# -*- coding: utf-8 -*-
"""LUMENIS Aggregation API — 序境体验层只读/受控聚合端点（无 url_prefix，全局 /api 路径）。

职责：为 LUMENIS 前端页面提供真实数据聚合，全部来自：
  - .env 配置（只回传 provider/model 名，绝不回传任何 API Key/Secret）
  - LUMENIS SQLite（只读 SELECT，不写生产业务数据）
  - OSAI Intelligence Core（动态只读 import，不可用时返回 UNAVAILABLE，不造假）
  - Git（subprocess 只读 rev-parse/status）

红线：
  - 不修改 Production Truth，不绕过 subject_hit / CollectorGuard
  - 唯一受控写操作是 KOS 专业号接入口（enable/disable/import），仅操作
    professional_accounts / professional_metrics 两张表，由用户点击显式触发。
  - 平台中立：通过 OSAI_ROOT 环境变量 + 相对发现定位跨仓，不硬编码个人盘符。
"""
import os
import sys
import sqlite3
import subprocess
import platform
from pathlib import Path
from lumenis.shared.database import DatabaseRepository, main_db_path
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

agg_bp = Blueprint("lumenis_agg", __name__)

# ---------- 路径与仓库发现（平台中立，禁止硬编码个人路径） ----------

_ZBC_ROOT = Path(__file__).resolve().parent


def _osai_root():
    """定位 OSAI 仓库根：优先环境变量，其次同级目录探测。"""
    env = os.environ.get("OSAI_ROOT")
    if env and Path(env).exists():
        return Path(env)
    for candidate in (_ZBC_ROOT.parent / "Zachary-OS-AI",
                      _ZBC_ROOT.parent / "Zachary OS AI"):
        if candidate.exists():
            return candidate
    return None


def _db_path():
    """生产数据库路径（只读使用）。"""
    p = Path(main_db_path())
    return p if p.exists() else None


def _db_readonly():
    """返回只读连接；数据库不存在时返回 None。"""
    db = _db_path()
    if not db:
        return None
    return DatabaseRepository(str(db)).connect(
        timeout=5, read_only=True, wal=False
    )


def _osai_module(name):
    """安全、幂等地只读 import OSAI 模块；失败返回 None（不抛给前端）。"""
    root = _osai_root()
    if not root:
        return None
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    try:
        return __import__(f"osai_engine.{name}", fromlist=[name])
    except Exception:
        return None


def _git_info(repo_path: Path):
    """只读读取 git HEAD SHA / branch / 工作区状态。"""
    if not repo_path or not repo_path.exists():
        return {"available": False, "status": "UNAVAILABLE"}
    def _run(args):
        try:
            out = subprocess.run(["git"] + args, cwd=str(repo_path),
                                 capture_output=True, text=True, timeout=8)
            return out.stdout.strip() if out.returncode == 0 else ""
        except Exception:
            return ""
    sha = _run(["rev-parse", "--short", "HEAD"])
    branch = _run(["rev-parse", "--abbrev-ref", "HEAD"])
    status = _run(["status", "--porcelain"])
    remote = _run(["config", "--get", "remote.origin.url"])
    return {
        "available": bool(sha),
        "head_sha": sha or "UNKNOWN",
        "branch": branch or "UNKNOWN",
        "remote": remote or "",
        "dirty_files": len([l for l in status.splitlines() if l.strip()]) if status else 0,
        "clean": not bool(status),
    }


# =====================================================================
# Intelligence：模型 / Agent / Evaluation / Research（跨核只读）
# =====================================================================

@agg_bp.route("/api/intelligence/models")
def intelligence_models():
    """Report the bound Owned Gateway route; configuration strings are not runtime proof."""
    try:
        from lumenis.system.ai_gateway.core import owned_service_observation

        raw_status = owned_service_observation(request.args.get("domain_id"))
    except Exception:
        raw_status = None
    status = raw_status if isinstance(raw_status, dict) else {}
    binding = status.get("service_binding")
    if not isinstance(binding, str) or len(binding) > 64:
        binding = "NOT_VERIFIED"
    state = status.get("state")
    if not isinstance(state, str) or len(state) > 64:
        state = "UNKNOWN"
    available = status.get("available") is True and binding == "BOUND"
    model = status.get("model_id")
    if not available or not isinstance(model, str) or not model.strip() or len(model) > 128:
        model = None
    reason = status.get("reason")
    if (not isinstance(reason, str) or not reason or len(reason) > 128
            or not reason.isascii() or not reason.replace("_", "").isalnum()):
        reason = "OWNED_RUNTIME_STATUS_UNAVAILABLE" if not status else None
    provider = {
        "provider": "owned",
        "kind": "owned",
        "model": model,
        "configured": binding == "BOUND",
        "credential_present": None,
        "active": available,
        "available": available,
        "state": state,
        "service_binding": binding,
        "fallback_allowed": False,
    }
    providers = [provider]
    selected_provider = "owned"
    selected_available = available
    selected_gateway = {
        "provider": "owned", "state": state, "service_binding": binding,
        "available": available, "reason": reason, "fallback_allowed": False,
    }
    from lumenis.system.ai_gateway import user_api_adapter

    if user_api_adapter.is_selected():
        # Explicit selection is retained; configuration never proves a live call.
        configured = user_api_adapter.is_configured()
        user_model = user_api_adapter.config().get("model") if configured else None
        if not isinstance(user_model, str) or len(user_model) > 128:
            user_model = None
        user_state = "CONFIGURED_NOT_VERIFIED" if configured else "NOT_CONFIGURED"
        provider["active"] = False
        selected_provider = "user_api"
        selected_available = None
        providers.append({
            "provider": "user_api", "kind": "user_selected", "model": user_model,
            "configured": configured, "credential_present": None, "active": True,
            "available": None, "state": user_state, "service_binding": "NOT_VERIFIED",
            "fallback_allowed": False,
        })
        selected_gateway = {
            "provider": "user_api", "state": user_state, "service_binding": "NOT_VERIFIED",
            "available": None, "reason": "USER_API_NOT_PROBED", "fallback_allowed": False,
        }
    return jsonify({
        "ok": True,
        "active_provider": selected_provider,
        "provider_agnostic": True,
        "fallback_chain": [],
        "runtime_available": selected_available,
        "gateway": selected_gateway,
        "providers": providers,
        "domain_statuses": status.get("domains", {}),
        "truth_boundary": "AI is enhancement only; OEVIRA Canonical data and Evidence remain authoritative",
    })


@agg_bp.route("/api/agents/status")
def agents_status():
    """Agent Center —— OSAI Agent 类型与 Harness 状态（只读）。"""
    agent_specs = [
        {"agent_id": "AGENT-ENG", "name": "Engineering Agent", "role": "工程执行/修复自愈",
         "layer": "L1-Intelligence"},
        {"agent_id": "AGENT-PATCH", "name": "Patch Agent", "role": "最小代码补丁生成",
         "layer": "L1-Intelligence"},
        {"agent_id": "AGENT-RESEARCH", "name": "Research Agent", "role": "外部研究/证据",
         "layer": "L1-Intelligence"},
        {"agent_id": "AGENT-EVAL", "name": "Evaluation Agent", "role": "结果评估/回归",
         "layer": "L1-Intelligence"},
    ]
    # Permission gate 真实读取
    perm_mod = _osai_module("permission_gate")
    boundary = {}
    if perm_mod:
        try:
            gate = perm_mod.PermissionGate()
            boundary = gate.boundary()
            levels = perm_mod.LEVELS
        except Exception:
            boundary, levels = {}, {}
    else:
        levels = {}
    return jsonify({
        "ok": True,
        "agents": agent_specs,
        "total": len(agent_specs),
        "running": 0,  # 无真实运行中的 Agent，诚实显示 0（不做假实时）
        "permission_boundary": boundary,
        "permission_levels": levels,
        "human_only": ["HUMAN_APPROVAL", "COMMIT", "PUSH"],
        "osai_connected": perm_mod is not None,
    })


@agg_bp.route("/api/evaluation/status")
def evaluation_status():
    """Evaluation Center —— 基于持久化 Evidence 真实统计，无数据则 NO_DATA。"""
    chains = _load_evidence_chains(limit=200)
    total = len(chains)
    by_status = {}
    for ch in chains:
        st = ch.get("status", "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1
    dims = ["correctness", "completeness", "regression", "safety",
            "latency", "cost", "tool_success", "evidence_quality"]
    return jsonify({
        "ok": True,
        "total_evaluations": total,
        "by_status": by_status,
        "dimensions": dims,
        "state": "NO_DATA" if total == 0 else "CONNECTED",
        "evidence_source": "OSAI evidence/chains (file-persisted)",
    })


def _load_evidence_chains(limit=50):
    root = _osai_root()
    chains = []
    if not root:
        return chains
    chain_dir = root / "evidence" / "chains"
    if not chain_dir.exists():
        return chains
    import json
    files = sorted(chain_dir.glob("*.json"), reverse=True)[:limit]
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                chains.append(json.load(fh))
        except Exception:
            continue
    return chains


@agg_bp.route("/api/research/status")
def research_status():
    rp_mod = _osai_module("research_pipeline")
    if not rp_mod:
        return jsonify({"ok": False, "state": "UNAVAILABLE", "pipeline": {}})
    try:
        rp = rp_mod.get_research_pipeline()
        snap = rp.snapshot()
        return jsonify({"ok": True, "state": "CONNECTED", "pipeline": snap})
    except Exception as e:
        return jsonify({"ok": False, "state": "ERROR", "error": str(e), "pipeline": {}})


@agg_bp.route("/api/research/pipeline")
def research_pipeline_view():
    """按研究阶段分组返回（External Research → Internal Design → Self-developed）。"""
    rp_mod = _osai_module("research_pipeline")
    if not rp_mod:
        return jsonify({"ok": False, "state": "UNAVAILABLE", "stages": {}})
    try:
        rp = rp_mod.get_research_pipeline()
        stages = {}
        for stage in ("SOURCE", "RESEARCH", "DESIGN", "IMPLEMENT", "VERIFY", "ACCEPTED"):
            try:
                recs = rp.list_by_stage(stage)
                stages[stage] = [r.to_dict() for r in recs]
            except Exception:
                stages[stage] = []
        return jsonify({"ok": True, "state": "CONNECTED", "stages": stages})
    except Exception as e:
        return jsonify({"ok": False, "state": "ERROR", "error": str(e), "stages": {}})


@agg_bp.route("/api/research/start", methods=["POST"])
def research_start():
    """创建一条外部研究记录（受控写 OSAI 研究管线，不写 ZBC 生产库）。"""
    rp_mod = _osai_module("research_pipeline")
    if not rp_mod:
        return jsonify({"ok": False, "status": "UNAVAILABLE",
                        "error": "OSAI Research Pipeline unavailable"}), 503
    data = request.get_json(silent=True) or {}
    source = (data.get("source") or "").strip()
    source_type = (data.get("source_type") or "external_doc").strip()
    title = (data.get("title") or "").strip()
    if not source or not title:
        return jsonify({"ok": False, "status": "VALIDATION_ERROR",
                        "error": "source and title are required"}), 400
    try:
        rp = rp_mod.get_research_pipeline()
        rec = rp.create_research(source=source, source_type=source_type, title=title)
        return jsonify({"ok": True, "status": "CREATED", "record": rec.to_dict()})
    except Exception as e:
        return jsonify({"ok": False, "status": "ERROR", "error": str(e)}), 500


# =====================================================================
# Operations：权限 / 仓库 / 运行时（只读）
# =====================================================================

@agg_bp.route("/api/operations/permissions")
def operations_permissions():
    """Permission Gate 矩阵 —— 真实读取 OSAI LEVELS 与 Agent 边界（fail-close）。"""
    perm_mod = _osai_module("permission_gate")
    if not perm_mod:
        return jsonify({"ok": False, "state": "UNAVAILABLE", "levels": {}})
    try:
        levels = perm_mod.LEVELS
        default_max = getattr(perm_mod, "AGENT_DEFAULT_MAX", "VERIFY")
        human_only = list(getattr(perm_mod, "AGENT_HUMAN_ONLY", ()))
        gate = perm_mod.PermissionGate()
        boundary = gate.boundary()
        rows = []
        for name, rank in sorted(levels.items(), key=lambda x: x[1]):
            rows.append({
                "level": name,
                "rank": rank,
                "agent_auto_allowed": name in boundary.get("agent_auto", []),
                "requires_human": name in human_only,
            })
        return jsonify({
            "ok": True, "state": "CONNECTED",
            "default_agent_ceiling": str(default_max),
            "fail_policy": "FAIL_CLOSE",  # 权限异常即阻断，不 fail-open
            "human_only": human_only,
            "boundary": boundary,
            "levels": rows,
        })
    except Exception as e:
        return jsonify({"ok": False, "state": "ERROR", "error": str(e)}), 500


@agg_bp.route("/api/system/repository")
def system_repository():
    """Repository Registry —— LUMENIS + OSAI（+GGI）真实 git 状态，只读。"""
    repos = [
        {"repository_id": "ZBC", "name": "LUMENIS-codex-Clean-OS", "role": "Production Core",
         "path": str(_ZBC_ROOT), "git": _git_info(_ZBC_ROOT)},
    ]
    osai = _osai_root()
    if osai:
        repos.append({"repository_id": "OSAI", "name": "Zachary-OS-AI",
                      "role": "Intelligence Core", "path": str(osai),
                      "git": _git_info(osai)})
    ggi = _ZBC_ROOT.parent / "global-growth-intelligence"
    if ggi.exists():
        repos.append({"repository_id": "GGI", "name": "global-growth-intelligence",
                      "role": "Independent Research Product", "path": str(ggi),
                      "git": _git_info(ggi)})
    return jsonify({"ok": True, "repositories": repos,
                    "physically_merged": False,
                    "note": "Repositories stay physically independent; logical fusion via contracts."})


@agg_bp.route("/api/system/runtime")
def system_runtime():
    """Local Runtime —— 进程/平台/DB 真实统计（只读）。"""
    db = _db_path()
    db_info = {"exists": bool(db)}
    conn = _db_readonly()
    if conn:
        try:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            counts = {}
            for t in ("notes", "daily_reports", "events", "kos_operations"):
                if t in tables:
                    counts[t] = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            db_info = {"exists": True, "table_count": len(tables), "row_counts": counts}
        finally:
            conn.close()
    domains = ("cth", "zbmp", "system")
    runtime_by_domain = {
        domain_id: {
            "total_workers": None,
            "running": None,
            "failed": None,
            "paused": None,
            "dlq_count": None,
            "workers": None,
        }
        for domain_id in domains
    }
    guardian_status = {
        "lease_manager": "UNKNOWN",
        "heartbeat_monitor": "UNKNOWN",
        "reaper": "UNKNOWN",
        "checkpoint": "UNKNOWN",
    }
    guardian_health = "UNKNOWN"
    all_workers = None
    health = None
    dlq_stats = None
    workers_available = False
    health_available = False
    dlq_available = False

    # The application launcher starts the app_main singleton. Read that same
    # owner rather than the independent default singleton. Worker rows provide
    # domain counts; get_tasks_by_domain swallows SQL errors as empty lists.
    try:
        from runtime_guardian import get_guardian
        guardian = get_guardian("app_main")
        workers_result = guardian.list_lifecycle_workers()
        if not isinstance(workers_result, list):
            raise TypeError("RuntimeGuardian returned a non-list worker snapshot")
        all_workers = workers_result
        workers_available = True

        for domain_id in domains:
            domain_workers = [
                worker for worker in all_workers
                if isinstance(worker, dict) and worker.get("domain_id") == domain_id
            ]
            runtime_by_domain[domain_id] = {
                "total_workers": len(domain_workers),
                "running": sum(
                    1 for worker in domain_workers
                    if worker.get("status") in ("running", "resuming")
                ),
                "failed": sum(
                    1 for worker in domain_workers
                    if worker.get("status") in ("failed", "dead", "stopping")
                ),
                "paused": sum(
                    1 for worker in domain_workers
                    if worker.get("status") == "paused"
                ),
                # The current public DLQ API only provides global stats. The
                # domain helper swallows query failures as empty lists, so it
                # cannot support a trustworthy per-domain zero.
                "dlq_count": None,
                "workers": [
                    {
                        "worker_id": worker.get("worker_id"),
                        "worker_name": worker.get("worker_name"),
                        "status": worker.get("status", "UNKNOWN"),
                        "last_heartbeat_at": worker.get("last_heartbeat_at"),
                    }
                    for worker in domain_workers[:20]
                ],
            }

        try:
            health_result = guardian.health_check()
            if isinstance(health_result, dict):
                health = health_result
                health_available = True
        except Exception:  # noqa: BLE001 - preserve partial owner observations
            health = None

        try:
            dlq_result = guardian.dlq.stats()
            if isinstance(dlq_result, dict):
                dlq_stats = dlq_result
                dlq_available = True
        except Exception:  # noqa: BLE001 - preserve partial owner observations
            dlq_stats = None
    except Exception:  # noqa: BLE001 - unknown worker snapshot must not become zero
        all_workers = None

    if isinstance(health, dict):
        observed_health = health.get("overall")
        if isinstance(observed_health, str) and observed_health.strip():
            guardian_health = observed_health

    lease_workers = [
        worker for worker in (all_workers or [])
        if isinstance(worker, dict) and str(worker.get("lease_owner") or "").strip()
    ]
    heartbeat_workers = [
        worker for worker in (all_workers or [])
        if isinstance(worker, dict) and worker.get("last_heartbeat_at")
    ]
    checkpoint_workers = [
        worker for worker in (all_workers or [])
        if isinstance(worker, dict) and worker.get("last_checkpoint_at")
    ]
    if workers_available:
        if lease_workers:
            guardian_status["lease_manager"] = "OBSERVED"
        if heartbeat_workers:
            guardian_status["heartbeat_monitor"] = "OBSERVED"
        if checkpoint_workers:
            guardian_status["checkpoint"] = "OBSERVED"

    reaper_running = health.get("reaper_running") if isinstance(health, dict) else None
    if isinstance(reaper_running, bool):
        guardian_status["reaper"] = "ACTIVE" if reaper_running else "STOPPED"

    runtime_ready = workers_available and health_available and dlq_available
    runtime_state = "READY" if runtime_ready else (
        "PARTIAL" if workers_available else "UNAVAILABLE"
    )
    response = {
        "guardian_status": guardian_status,
        "ok": runtime_ready,
        "state": runtime_state,
        "guardian_health": guardian_health,
        "python": platform.python_version(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "zbc_root": str(_ZBC_ROOT),
        "osai_root": str(_osai_root()) if _osai_root() else "NOT_FOUND",
        "database": db_info,
        "server_time": datetime.now().isoformat(timespec="seconds"),
        "runtime_by_domain": runtime_by_domain,
        "domain_id": "system",
        "product_id": "SYSTEM",
        "guardian": {
            "lease": {
                "status": guardian_status["lease_manager"],
                "observed_workers": len(lease_workers) if workers_available else None,
            },
            "heartbeat": {
                "status": guardian_status["heartbeat_monitor"],
                "observed_workers": len(heartbeat_workers) if workers_available else None,
            },
            "reaper": {
                "status": (
                    "RUNNING" if reaper_running is True else
                    "STOPPED" if reaper_running is False else "UNKNOWN"
                ),
                "last_run": None,
            },
            "checkpoint": {
                "status": guardian_status["checkpoint"],
                "observed_workers": len(checkpoint_workers) if workers_available else None,
            },
        },
        "dlq": dlq_stats,
    }
    return jsonify(response), 200 if runtime_ready else 503


# =====================================================================
# Production：报告（只读）+ KOS 专业号接入口（受控）
# =====================================================================

@agg_bp.route("/api/production/reports")
def production_reports():
    """报告中心 —— daily_reports 真实列表（只读，按日期倒序）。"""
    conn = _db_readonly()
    if not conn:
        return jsonify({"ok": False, "state": "DB_UNAVAILABLE", "reports": []})
    try:
        rtype = request.args.get("type", "").strip()
        sql = "SELECT * FROM daily_reports"
        params = ()
        if rtype:
            sql += " WHERE report_type=?"
            params = (rtype,)
        sql += " ORDER BY report_date DESC, id DESC LIMIT 100"
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        return jsonify({"ok": True, "state": "CONNECTED", "total": len(rows),
                        "reports": rows})
    finally:
        conn.close()


def _kos_pro():
    """惰性导入 KOS 专业号模块。"""
    try:
        import kos_professional
        kos_professional.init_db()
        return kos_professional
    except Exception as e:
        current_app.logger.warning("kos_professional unavailable: %s", e)
        return None


@agg_bp.route("/api/kos/professional/status")
def kos_professional_status():
    from kos_routes import _professional_scoped_response
    return _professional_scoped_response("status")


@agg_bp.route("/api/kos/professional/enable", methods=["POST"])
def kos_professional_enable():
    from kos_routes import _professional_scoped_response
    return _professional_scoped_response("enable")


@agg_bp.route("/api/kos/professional/disable", methods=["POST"])
def kos_professional_disable():
    from kos_routes import _professional_scoped_response
    return _professional_scoped_response("disable")


@agg_bp.route("/api/kos/professional/import", methods=["POST"])
def kos_professional_import():
    from kos_routes import _professional_scoped_response
    return _professional_scoped_response("import")


def register_agg_api(app):
    app.register_blueprint(agg_bp)

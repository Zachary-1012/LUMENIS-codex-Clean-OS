"""SYSTEM-owned Creator Ops for 序境 / LUMENIS.

This is a human-readable operating surface built *on top of* the existing
``system_health_api`` summary.  It does not start/stop a collector, restart a
runtime, publish content, access credentials, or create a second health/DB
truth.  POST endpoints intentionally remain subject to the application's
existing PermissionGate when mounted by app.py.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import psutil
from flask import Blueprint, Response, jsonify, request

system_creator_ops_bp = Blueprint("system_creator_ops", __name__)

_CPU_PREVIOUS: Dict[str, float] = {}
_REDACT_PATTERNS = (
    (re.compile(r"(authorization\s*[:=]\s*(?:bearer\s+)?)([^\s,;]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(bearer\s+)([A-Za-z0-9._~+/=-]{8,})", re.I), r"\1[REDACTED]"),
    (re.compile(r"([?&](?:access_?token|api_?key|key|secret|token|cookie|password)=)([^&#\s]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"((?:api[_-]?key|secret|token|cookie|password|x-api-key)\s*[:=]\s*[\"']?)([^\s,\"']+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9_-]{32,}\b"), "[REDACTED]"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _data_root() -> Path:
    # Reuse the existing system-health runtime data root; do not create a new
    # product database or store under the repository by accident.
    from system_health_api import get_data_dir
    return Path(get_data_dir())


def _store_path() -> Path:
    return _data_root() / "ops" / "creator_ops.json"


def _redact(value: Any) -> str:
    text = str(value or "")
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _read_store() -> Dict[str, Any]:
    try:
        value = json.loads(_store_path().read_text(encoding="utf-8"))
        if isinstance(value, dict):
            return {
                "schema_version": 1,
                "costs": value.get("costs", [])[-500:] if isinstance(value.get("costs"), list) else [],
                "feedback": value.get("feedback", [])[-500:] if isinstance(value.get("feedback"), list) else [],
            }
    except Exception:
        pass
    return {"schema_version": 1, "costs": [], "feedback": []}


def _write_store(value: Dict[str, Any]) -> None:
    target = _store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="creator_ops_", suffix=".json", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _system_health_payload() -> Dict[str, Any]:
    """Reuse the existing canonical health summary instead of recomputing it."""
    try:
        from system_health_api import system_health_summary
        result = system_health_summary()
        response: Response = result[0] if isinstance(result, tuple) else result
        payload = response.get_json(silent=True)
        if isinstance(payload, dict):
            return payload
    except Exception as exc:  # source health must remain explicit, never faked
        return {"ok": False, "overall_status": "unknown", "diagnostic_hints": [f"系统健康摘要不可用：{type(exc).__name__}"]}
    return {"ok": False, "overall_status": "unknown", "diagnostic_hints": ["系统健康摘要没有返回结构化数据"]}


def _runtime_snapshot() -> Dict[str, Any]:
    process = psutil.Process(os.getpid())
    try:
        memory = process.memory_info()
        key = str(os.getpid())
        previous = _CPU_PREVIOUS.get(key)
        cpu = process.cpu_percent(interval=None)
        _CPU_PREVIOUS[key] = time.monotonic()
        cpu_state = "observed" if previous is not None else "warming_up"
        return {
            "pid": os.getpid(),
            "uptime_seconds": max(0, round(time.time() - process.create_time())),
            "rss_bytes": int(memory.rss),
            "vms_bytes": int(memory.vms),
            "process_cpu_percent": round(float(cpu), 1) if previous is not None else None,
            "cpu_state": cpu_state,
            "cpu_scope": "当前 Python 进程；不把宿主机 CPU 或云账户配额伪装为已观测。",
        }
    except Exception as exc:
        return {"state": "unknown", "detail": f"运行时进程指标不可用：{type(exc).__name__}"}


def _storage_snapshot() -> Dict[str, Any]:
    try:
        usage = shutil.disk_usage(_data_root())
        available_percent = round((usage.free / usage.total) * 100, 2) if usage.total else None
        return {
            "state": "attention" if available_percent is not None and available_percent < 10 else "healthy",
            "total_bytes": int(usage.total),
            "available_bytes": int(usage.free),
            "available_percent": available_percent,
            "scope": "LUMENIS 受保护运行数据所在文件系统，不是云厂商账户配额。",
        }
    except Exception as exc:
        return {"state": "unknown", "available_percent": None, "detail": f"数据卷不可观测：{type(exc).__name__}"}


def _supervisor_snapshot() -> Dict[str, Any]:
    state_file = _data_root() / "supervisor_state.json"
    try:
        value = json.loads(state_file.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            return {
                "state": _redact(value.get("status") or "unknown"),
                "updated_at": _redact(value.get("updated_at") or ""),
                "restarts": value.get("restarts"),
                "fast_crashes": value.get("fast_crashes"),
                "observed": True,
            }
    except Exception:
        pass
    return {"state": "not_observed", "observed": False, "detail": "尚未发现 supervisor_state.json；不表示监督器一定未运行。"}


def _safe_build_sha() -> str | None:
    candidate = os.environ.get("LUMENIS_BUILD_SHA") or os.environ.get("GITHUB_SHA") or os.environ.get("RAILWAY_GIT_COMMIT_SHA") or ""
    return candidate if re.fullmatch(r"[a-fA-F0-9]{7,64}", candidate) else None


def _cost_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
    active: List[Dict[str, Any]] = []
    for item in data.get("costs", []):
        try:
            if datetime.fromisoformat(str(item.get("occurred_at", "")).replace("Z", "+00:00")).timestamp() >= start:
                active.append(item)
        except Exception:
            continue
    tracked = round(sum(float(item.get("amount_usd", 0)) for item in active), 2) if active else None
    try:
        budget = float(os.environ.get("LUMENIS_OPS_MONTHLY_BUDGET_USD", ""))
        if budget < 0:
            raise ValueError
        budget = round(budget, 2)
    except Exception:
        budget = None
    return {
        "tracking": "manual" if active else "not_connected",
        "actual_provider_billing": "not_connected",
        "month_tracked_usd": tracked,
        "month_entry_count": len(active),
        "budget_usd": budget,
        "budget_state": "not_configured" if budget is None else "over_budget" if (tracked or 0) > budget else "within_budget",
        "note": "金额来自本地手工录入，不是云厂商账单 API。" if active else "尚未接入账单；未录入不表示成本为 0。",
    }


def build_system_creator_ops_summary() -> Dict[str, Any]:
    health = _system_health_payload()
    data = _read_store()
    runtime = _runtime_snapshot()
    storage = _storage_snapshot()
    supervisor = _supervisor_snapshot()
    costs = _cost_summary(data)
    diagnostics: List[Dict[str, str]] = []
    overall = str(health.get("overall_status") or "unknown")
    if overall != "ok":
        for hint in health.get("diagnostic_hints") or ["现有 System Health 需要查看"]:
            diagnostics.append({"severity": "attention", "title": "System Health 需要查看", "detail": _redact(hint), "automatic": "false"})
    if storage.get("state") == "attention":
        diagnostics.append({"severity": "warning", "title": "数据卷空间偏低", "detail": f"可用空间 {storage.get('available_percent')}%", "automatic": "false"})
    if costs["tracking"] == "not_connected":
        diagnostics.append({"severity": "info", "title": "成本尚未接入", "detail": costs["note"], "automatic": "false"})
    if not _safe_build_sha():
        diagnostics.append({"severity": "info", "title": "构建来源未验证", "detail": "未注入格式合法的 LUMENIS_BUILD_SHA/GITHUB_SHA。", "automatic": "false"})
    return {
        "schema": "lumenis-system-creator-ops-v1",
        "generated_at": _now(),
        "scope": {
            "owner": "SYSTEM",
            "health_truth": "/api/system/health/summary",
            "telemetry": False,
            "actions": "advisory-only; never restart, deploy, rollback, publish, delete, or access credentials",
        },
        "overall": overall,
        "system_health": health,
        "runtime": runtime,
        "storage": storage,
        "supervisor": supervisor,
        "delivery": {"build_sha": _safe_build_sha(), "build_verified": bool(_safe_build_sha()), "release_status": "not inferred from runtime"},
        "costs": costs,
        "feedback": {"open_count": len(data.get("feedback", [])), "latest": list(reversed(data.get("feedback", [])[-20:])), "privacy": "本地保存且在落盘前脱敏。"},
        "diagnostics": diagnostics,
    }


def _body() -> Dict[str, Any]:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError("JSON body must be an object")
    return value


def _string(value: Any, field: str, maximum: int, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{field} is required")
    if len(text) > maximum:
        raise ValueError(f"{field} must be at most {maximum} characters")
    return _redact(text)


@system_creator_ops_bp.route("/api/system/ops/summary")
def system_creator_ops_summary():
    return jsonify(build_system_creator_ops_summary())


@system_creator_ops_bp.route("/api/system/ops/events")
def system_creator_ops_events():
    data = _read_store()
    return jsonify({"schema": "lumenis-system-creator-ops-events-v1", "generated_at": _now(), "costs": list(reversed(data["costs"][-100:])), "feedback": list(reversed(data["feedback"][-100:])), "privacy": "SYSTEM local-only, secret-redacted."})


@system_creator_ops_bp.route("/api/system/ops/report")
def system_creator_ops_report():
    summary = build_system_creator_ops_summary()
    actions = summary["diagnostics"] or [{"severity": "info", "title": "无本地规则触发项", "detail": "仍应使用独立监控验证公网入口。"}]
    lines = [
        "# 序境 / LUMENIS SYSTEM Ops Brief",
        "",
        f"- System Health: {summary['overall']}",
        f"- 构建来源: {summary['delivery']['build_sha'] or '未验证'}",
        f"- 本月成本: {summary['costs']['month_tracked_usd'] if summary['costs']['month_tracked_usd'] is not None else '未接入/未录入'}",
        f"- 开放反馈: {summary['feedback']['open_count']}",
        "",
        "## 建议动作",
    ]
    lines.extend(f"{index}. [{item['severity']}] {item['title']}：{item['detail']}" for index, item in enumerate(actions, 1))
    lines.extend(["", "## 边界", "本简报只组合既有 System Health 和本地脱敏 Ops 记录；不代表云账单、用户增长、外部可用性或已完成发布，也不会自动执行运行时操作。"])
    return jsonify({"schema": "lumenis-system-creator-ops-report-v1", "generated_at": summary["generated_at"], "summary": summary, "markdown": "\n".join(lines)})


@system_creator_ops_bp.route("/api/system/ops/costs", methods=["POST"])
def system_creator_ops_costs():
    try:
        body = _body()
        amount = round(float(body.get("amount_usd")), 2)
        if not 0 <= amount <= 1_000_000:
            raise ValueError("amount_usd must be between 0 and 1000000")
        occurred_at = str(body.get("occurred_at") or _now())
        datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        entry = {"id": f"cost_{uuid.uuid4().hex[:12]}", "amount_usd": amount, "category": _string(body.get("category", "Other"), "category", 60, True), "note": _string(body.get("note", ""), "note", 280), "occurred_at": occurred_at, "created_at": _now()}
        data = _read_store(); data["costs"] = (data["costs"] + [entry])[-500:]; _write_store(data)
        return jsonify({"ok": True, "cost": entry}), 201
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@system_creator_ops_bp.route("/api/system/ops/feedback", methods=["POST"])
def system_creator_ops_feedback():
    try:
        body = _body()
        severity = _string(body.get("severity", "normal"), "severity", 12).lower()
        if severity not in {"low", "normal", "high", "critical"}:
            raise ValueError("severity must be low, normal, high, or critical")
        entry = {"id": f"feedback_{uuid.uuid4().hex[:12]}", "title": _string(body.get("title"), "title", 120, True), "detail": _string(body.get("detail"), "detail", 4000, True), "severity": severity, "status": "open", "created_at": _now()}
        data = _read_store(); data["feedback"] = (data["feedback"] + [entry])[-500:]; _write_store(data)
        return jsonify({"ok": True, "feedback": entry}), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@system_creator_ops_bp.route("/system/ops")
def system_creator_ops_page():
    """Small responsive SYSTEM entry page; data is loaded only from same-origin protected APIs."""
    return Response("""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'><title>序境 SYSTEM Ops</title><style>body{margin:0;background:#0e1317;color:#edf5f2;font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}main{max-width:1320px;margin:auto;padding:clamp(16px,3vw,42px)}h1{margin:0}p{color:#aebbb7}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0}.card{min-width:0;border:1px solid #273734;border-radius:13px;background:#151d1b;padding:15px}.label{font-size:12px;color:#9cb2aa}.value{font-size:24px;font-weight:750;overflow-wrap:anywhere}.detail{font-size:13px;color:#b6c7c1}.diag{border-left:4px solid #d6a44a;margin:9px 0;padding:10px;background:#1d2018;border-radius:7px}.diag.warning{border-color:#e16c68}.actions{display:flex;gap:9px;flex-wrap:wrap}button{min-height:44px;border:0;border-radius:9px;padding:0 14px;font:inherit;font-weight:700;background:#43b886;color:#062518}textarea,input,select{box-sizing:border-box;width:100%;min-height:44px;margin:5px 0;border-radius:8px;border:1px solid #3b5049;background:#0e1513;color:#edf5f2;padding:9px;font:inherit}textarea{min-height:200px;resize:vertical}@media(max-width:480px){main{padding:14px}.grid{grid-template-columns:1fr}}</style></head><body><main><div class='actions'><div><h1>SYSTEM Ops</h1><p>序境运行、交付、成本与反馈的本地可读工作台。不会自动重启、发布、回滚、删除或读取凭据。</p></div><button id='refresh'>刷新</button></div><section id='cards' class='grid'></section><section class='card'><h2>诊断与建议</h2><div id='diagnostics'></div></section><section class='grid'><div class='card'><h2>登记成本</h2><input id='amount' inputmode='decimal' placeholder='金额 USD'><input id='category' placeholder='类别，例如 Hosting'><input id='cost-note' placeholder='备注（自动脱敏）'><button id='save-cost'>保存（通过既有权限门）</button></div><div class='card'><h2>提交反馈</h2><input id='title' placeholder='标题'><select id='severity'><option>normal</option><option>high</option><option>critical</option><option>low</option></select><input id='detail' placeholder='问题现象（不要粘贴密钥）'><button id='save-feedback'>保存（通过既有权限门）</button></div></section><section class='card'><div class='actions'><h2>交付简报</h2><button id='copy'>复制</button></div><textarea id='report' readonly></textarea></section></main><script>const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));const bytes=n=>n==null?'未观测':n>1073741824?(n/1073741824).toFixed(1)+' GB':(n/1048576).toFixed(1)+' MB';async function api(url,opt){let r=await fetch(url,opt),j=await r.json();if(!r.ok)throw Error(j.error||r.status);return j}function card(k,v,d){return `<div class='card'><div class='label'>${esc(k)}</div><div class='value'>${esc(v)}</div><div class='detail'>${esc(d||'')}</div></div>`}async function load(){try{let[s,r]=await Promise.all([api('/api/system/ops/summary'),api('/api/system/ops/report')]),h=s.system_health||{},run=s.runtime||{},st=s.storage||{},c=s.costs||{};$('#cards').innerHTML=card('System Health',s.overall,'唯一健康真相：/api/system/health/summary')+card('进程内存',bytes(run.rss_bytes),'运行 '+(run.uptime_seconds??'—')+'s')+card('进程 CPU',run.process_cpu_percent==null?'采样中':run.process_cpu_percent+'%',run.cpu_scope)+card('数据卷',st.available_percent==null?'未观测':st.available_percent+'% 可用',st.scope)+card('构建来源',s.delivery?.build_sha||'未验证',s.delivery?.release_status)+card('本月成本',c.month_tracked_usd==null?'未接入':'$'+c.month_tracked_usd,c.note)+card('开放反馈',s.feedback?.open_count||0,s.feedback?.privacy);$('#diagnostics').innerHTML=(s.diagnostics||[]).map(x=>`<div class='diag ${esc(x.severity)}'><b>${esc(x.title)}</b><div class='detail'>${esc(x.detail)}</div></div>`).join('')||'<p>当前没有本地规则触发项。</p>';$('#report').value=r.markdown||''}catch(e){$('#diagnostics').textContent='加载失败：'+e.message}}$('#refresh').onclick=load;$('#copy').onclick=()=>navigator.clipboard?.writeText($('#report').value);$('#save-cost').onclick=async()=>{try{await api('/api/system/ops/costs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({amount_usd:$('#amount').value,category:$('#category').value||'Other',note:$('#cost-note').value})});await load()}catch(e){alert('保存失败：'+e.message)}};$('#save-feedback').onclick=async()=>{try{await api('/api/system/ops/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:$('#title').value,detail:$('#detail').value,severity:$('#severity').value})});await load()}catch(e){alert('保存失败：'+e.message)}};load()</script></body></html>""", mimetype="text/html")

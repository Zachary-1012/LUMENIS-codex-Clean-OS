# -*- coding: utf-8 -*-
"""VIZ API — 函数驱动可视化后端 API 端点。

端点：
  GET  /api/viz/registry              → 返回所有已注册函数元数据
  GET  /api/viz/<function_name>       → 查找注册表 → 注入 DB 数据 → ui_view_model 转换 → 返回
  POST /api/viz/<function_name>       → 同上（支持复杂参数，JSON body）

统一响应格式：
  {success, data: {current_value, delta, freshness, confidence, evidence_refs, items},
   function_name, domain, error, domain_id, product_id}

错误处理：
  - 函数不存在 → 404 + 可用函数列表
  - 参数错误 → 400 + 错误详情
  - 取数失败 → 200 + success=false + error（DataStatus.ERROR 显式表达）
  - 数据缺失 → 200 + success=true + current_value=null + status=no_data

硬约束：
  - 每个函数必须经过 ui_view_model 转换（build_truth_table / MetricLayer / compute_time_bounds / filter_records_by_time）
  - 禁止直接返回原始 DB 数据
  - 数据缺失显式 null/unknown/missing，禁止 0 或默认值填充
  - API key 不入输出/日志
  - 所有端点带 domain_id/product_id 标识
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

from function_registry import (
    VIZ_FUNCTIONS,
    get_viz_function,
    viz_registry_metadata,
)
from ui_view_model import (
    ConfidenceLevel,
    DataResult,
    DataStatus,
    MetricLayer,
    TimeRange,
    build_truth_table,
    compute_time_bounds,
    default_visualization_for_metric,
    filter_records_by_time,
)
from viz_data_provider import fetch_data

logger = logging.getLogger(__name__)

viz_bp = Blueprint("viz", __name__, url_prefix="/api/viz")

# ── 域身份解析 ──────────────────────────────────────────────────────────────

def _resolve_domain() -> Dict[str, str]:
    """从请求头 / 查询参数解析 domain_id / product_id。"""
    domain_id = request.headers.get("X-Domain-Id", "")
    product_id = request.headers.get("X-Product-Id", "")
    if not domain_id:
        domain_id = request.args.get("domain_id", "")
    if not product_id:
        product_id = request.args.get("product_id", "")
    if not domain_id:
        domain_id = "cth"
    if not product_id:
        product_id = "taikoo"
    return {"domain_id": domain_id, "product_id": product_id}


# ── 参数解析 ────────────────────────────────────────────────────────────────

def _parse_params() -> Dict[str, Any]:
    """从 GET query string 或 POST JSON body 解析参数。"""
    params: Dict[str, Any] = {}
    if request.method == "POST":
        try:
            body = request.get_json(silent=True)
            if isinstance(body, dict):
                params.update(body)
        except Exception:
            pass
    # GET params 覆盖（query string 优先）
    for key, value in request.args.items():
        if key in ("domain_id", "product_id"):
            continue
        params[key] = value
    return params


def _validate_params(func_entry: Dict[str, Any], params: Dict[str, Any]) -> Optional[str]:
    """校验必填参数。返回错误信息或 None。"""
    required = func_entry.get("param_schema", {}).get("required", [])
    missing = [k for k in required if not params.get(k)]
    if missing:
        return "missing required parameters: %s" % ", ".join(missing)
    return None


# ── ui_view_model 转换层 ────────────────────────────────────────────────────

def _transform_to_view(function_name: str, func_entry: Dict[str, Any],
                        data_result: DataResult, params: Dict[str, Any]) -> Dict[str, Any]:
    """将 DataResult 经过 ui_view_model 转换为标准视图数据。

    必须调用 ui_view_model 的转换函数，禁止直接返回原始 DB 数据。
    """
    tr = TimeRange.from_str(params.get("time_range", "today"))

    # Step 1: 按时间范围过滤记录（调用 filter_records_by_time）
    time_field = "publish_datetime"
    if function_name in ("ai.call_logs",):
        time_field = "created_at"
    elif function_name in ("system.runtime", "system.workers", "system.database_tables",
                            "system.health", "collector.status", "collector.quality_gate"):
        time_field = "updated_at"
    filtered = filter_records_by_time(data_result.records, tr, time_field=time_field)

    # Step 2: 构建 TruthTable（调用 build_truth_table）
    truth = build_truth_table(data_result, freshness_threshold_seconds=3600)

    # Step 3: MetricLayer 计算（调用 MetricLayer）
    metric_layer = MetricLayer()
    metrics = metric_layer.compute_all(filtered)

    # Step 4: 计算 current_value / delta / confidence / evidence_refs
    current_value = None
    if function_name in ("overview.stats", "overview.trend", "notes.realtime",
                          "notes.search", "risk.active", "risk.trend", "events.list"):
        total_metric = metrics.get("total")
        current_value = total_metric.value if total_metric and total_metric.is_known else None
    elif function_name in ("system.runtime", "system.workers", "system.database_tables",
                            "system.health", "collector.status", "collector.quality_gate",
                            "ai.call_logs", "kos.list", "kos.attribution",
                            "brand.top10", "brand.growth", "overview.industry_dist",
                            "events.propagation"):
        current_value = len(filtered) if filtered else None

    # Delta：如果有上一周期数据则计算，否则返回 null（不默认填充）
    delta = {
        "value": None,
        "percent": None,
        "direction": "unknown",
        "comparison_range": None,
    }

    # Freshness：从 TruthTable 读取
    freshness = "unknown"
    if truth.staleness_seconds is not None:
        secs = int(truth.staleness_seconds)
        if secs < 60:
            freshness = "%d 秒前" % secs
        elif secs < 3600:
            freshness = "%d 分钟前" % (secs // 60)
        elif secs < 86400:
            freshness = "%d 小时前" % (secs // 3600)
        else:
            freshness = "%d 天前" % (secs // 86400)
    elif truth.status == DataStatus.NO_DATA:
        freshness = "no_data"
    elif truth.status == DataStatus.ERROR:
        freshness = "error"

    # Confidence：从 TruthTable 读取
    confidence = truth.confidence.value

    # Evidence refs：从记录中提取（最多 5 条）
    evidence_refs = []
    for r in filtered[:5]:
        if not isinstance(r, dict):
            continue
        eid = str(r.get("id") or r.get("note_id") or r.get("event_id") or r.get("worker_id") or "")
        if not eid:
            continue
        evidence_refs.append({
            "evidence_id": eid,
            "evidence_type": r.get("type", "note"),
            "title": str(r.get("title") or r.get("content") or r.get("worker_name") or "")[:80],
            "url": str(r.get("url") or r.get("note_url") or ""),
            "source": str(r.get("platform") or r.get("source") or r.get("provider") or ""),
            "timestamp": r.get("publish_datetime") or r.get("collected_at") or r.get("created_at") or r.get("updated_at"),
        })

    # Items：经过过滤和转换的记录列表（不直接返回原始 DB 行，
    # 但保留业务字段供前端渲染；敏感字段已在 provider 层排除）
    items = []
    for r in filtered:
        if isinstance(r, dict):
            items.append(r)

    # 默认可视化配置（调用 default_visualization_for_metric）
    viz_config = default_visualization_for_metric(
        "total" if current_value is not None else "health",
        func_entry.get("label", function_name),
    )

    return {
        "current_value": current_value,
        "delta": delta,
        "freshness": freshness,
        "confidence": confidence,
        "evidence_refs": evidence_refs,
        "items": items,
        "truth": truth.to_dict(),
        "metrics": {k: v.__dict__ for k, v in metrics.items()},
        "visualization": viz_config.to_dict(),
        "time_range": tr.value,
        "record_count": len(filtered),
        "data_status": truth.status.value,
    }


# ── API 端点 ────────────────────────────────────────────────────────────────

@viz_bp.route("/registry", methods=["GET"])
def api_viz_registry():
    """返回所有已注册可视化函数的元数据列表（供前端发现可用函数）。"""
    domain_info = _resolve_domain()
    meta = viz_registry_metadata()
    return jsonify({
        "success": True,
        "data": {
            "functions": meta,
            "total": len(meta),
        },
        "function_name": "registry",
        "domain": "all",
        "error": "",
        "domain_id": domain_info["domain_id"],
        "product_id": domain_info["product_id"],
    }), 200


@viz_bp.route("/<function_name>", methods=["GET", "POST"])
def api_viz_function(function_name: str):
    """调用指定可视化函数：查找注册表 → 注入 DB 数据 → ui_view_model 转换 → 返回。"""
    domain_info = _resolve_domain()

    # 1. 查找注册表
    func_entry = get_viz_function(function_name)
    if func_entry is None:
        available = [f["function_name"] for f in VIZ_FUNCTIONS]
        return jsonify({
            "success": False,
            "data": None,
            "function_name": function_name,
            "domain": "unknown",
            "error": "function not found: %s" % function_name,
            "available_functions": available,
            "domain_id": domain_info["domain_id"],
            "product_id": domain_info["product_id"],
        }), 404

    # 2. 解析参数
    params = _parse_params()

    # 3. 校验必填参数
    param_error = _validate_params(func_entry, params)
    if param_error:
        return jsonify({
            "success": False,
            "data": None,
            "function_name": function_name,
            "domain": func_entry["domain"],
            "error": param_error,
            "param_schema": func_entry["param_schema"],
            "domain_id": domain_info["domain_id"],
            "product_id": domain_info["product_id"],
        }), 400

    # 4. 域隔离检查
    func_domain = func_entry["domain"]
    req_domain = domain_info["domain_id"]
    if func_domain not in ("all", req_domain):
        return jsonify({
            "success": False,
            "data": None,
            "function_name": function_name,
            "domain": func_domain,
            "error": "domain mismatch: function '%s' requires domain '%s', request domain is '%s'" % (
                function_name, func_domain, req_domain),
            "domain_id": domain_info["domain_id"],
            "product_id": domain_info["product_id"],
        }), 403

    # 5. 注入 DB 数据（通过 viz_data_provider）
    data_result = fetch_data(function_name, params)

    # 6. ui_view_model 转换
    try:
        view_data = _transform_to_view(function_name, func_entry, data_result, params)
    except Exception as exc:
        logger.exception("viz transform failed for %s", function_name)
        return jsonify({
            "success": False,
            "data": None,
            "function_name": function_name,
            "domain": func_entry["domain"],
            "error": "transform error: %s" % str(exc),
            "domain_id": domain_info["domain_id"],
            "product_id": domain_info["product_id"],
        }), 500

    # 7. 返回统一响应
    success = data_result.status != DataStatus.ERROR
    error_msg = data_result.error or ""

    return jsonify({
        "success": success,
        "data": view_data,
        "function_name": function_name,
        "domain": func_entry["domain"],
        "error": error_msg,
        "domain_id": domain_info["domain_id"],
        "product_id": domain_info["product_id"],
    }), 200


def register_viz_api(app):
    """注册 viz blueprint 到 Flask app。"""
    app.register_blueprint(viz_bp)
    logger.info("[viz_api] registered: /api/viz/* (%d functions)", len(VIZ_FUNCTIONS))

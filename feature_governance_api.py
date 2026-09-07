# -*- coding: utf-8 -*-
"""
ZBC Feature Governance API Blueprint
提供 Feature Registry 的只读查询端点，用于前端导航、依赖分析和治理看板。

数据来源: audit/feature_governance/ 下的 JSON 交付物（由 _build_feature_registry.py 生成）。
硬约束: 只读，不修改任何业务逻辑；加载失败时返回空结果而非 500。
"""
import json
import os
from flask import Blueprint, jsonify, abort

feature_governance_bp = Blueprint("feature_governance", __name__, url_prefix="/api/feature-registry")

# 数据文件目录
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit", "feature_governance")


def _load_json(name):
    """安全加载 JSON，文件不存在或解析失败时返回 None。"""
    path = os.path.join(_DATA_DIR, name)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print("[feature_governance] load %s failed: %s" % (name, e))
    return None


def _build_tree(features):
    """从 feature_registry 的扁平列表按 parent_id 构建嵌套树。"""
    if not features:
        return []
    by_id = {f["feature_id"]: f for f in features}
    children = {}
    roots = []
    for fid, feat in by_id.items():
        pid = feat.get("parent_id")
        if pid and pid in by_id:
            children.setdefault(pid, []).append(fid)
        else:
            roots.append(fid)

    def node(fid):
        f = by_id[fid]
        return {
            "feature_id": fid,
            "name": f.get("canonical_name", fid),
            "level": f.get("level"),
            "type": f.get("type"),
            "status": f.get("status"),
            "owner": f.get("canonical_owner"),
            "children": [node(c) for c in sorted(children.get(fid, []))],
        }

    return [node(r) for r in sorted(roots)]


@feature_governance_bp.route("/tree", methods=["GET"])
def get_tree():
    """返回功能树 JSON（L0→L1→L2→L3→L4 嵌套结构）。"""
    reg = _load_json("feature_registry.json")
    if not reg:
        return jsonify({"ok": False, "error": "feature_registry.json not found", "tree": []}), 404
    tree = _build_tree(reg.get("features", []))
    return jsonify({
        "ok": True,
        "total": len(reg.get("features", [])),
        "metadata": reg.get("metadata", {}),
        "tree": tree,
    })


@feature_governance_bp.route("/capability-map", methods=["GET"])
def get_capability_map():
    """返回能力图 JSON（Feature→Provider→API→Service→DB，Caller→UI/Agent/Skill）。"""
    cap = _load_json("capability_map.json")
    if cap is None:
        return jsonify({"ok": False, "error": "capability_map.json not found"}), 404
    return jsonify({
        "ok": True,
        "total": len(cap) if isinstance(cap, dict) else 0,
        "capability_map": cap,
    })


@feature_governance_bp.route("/feature/<feature_id>", methods=["GET"])
def get_feature(feature_id):
    """返回单个 feature 的完整信息。"""
    reg = _load_json("feature_registry.json")
    if not reg:
        return jsonify({"ok": False, "error": "feature_registry.json not found"}), 404
    for f in reg.get("features", []):
        if f.get("feature_id") == feature_id:
            return jsonify({"ok": True, "feature": f})
    # 尝试模糊匹配（前缀）
    matches = [f for f in reg.get("features", [])
               if f.get("feature_id", "").startswith(feature_id)]
    if len(matches) == 1:
        return jsonify({"ok": True, "feature": matches[0], "matched_by": "prefix"})
    if matches:
        return jsonify({
            "ok": True,
            "note": "%d matches by prefix, returning first" % len(matches),
            "feature": matches[0],
            "matches": [m["feature_id"] for m in matches[:20]],
        })
    return jsonify({"ok": False, "error": "feature not found: %s" % feature_id}), 404


@feature_governance_bp.route("/governance-report", methods=["GET"])
def get_governance_report():
    """返回治理报告摘要（统计 + P0/P1/P2 计数）。"""
    reg = _load_json("feature_registry.json")
    dups = _load_json("duplicates.json")
    wrong = _load_json("wrong_ownership.json")
    orph = _load_json("orphans.json")
    unc = _load_json("unclassified.json")

    features = reg.get("features", []) if reg else []
    from collections import Counter
    by_status = dict(Counter(f.get("status", "?") for f in features))
    by_type = dict(Counter(f.get("type", "?") for f in features))
    by_level = dict(Counter(f.get("level", "?") for f in features))

    # P0: API_DRIFT + DUPLICATE 核心业务
    p0_count = by_status.get("API_DRIFT", 0) + (dups.get("metadata", {}).get("total", 0) if dups else 0)
    # P1: UNCLASSIFIED type + wrong ownership
    p1_count = (wrong.get("metadata", {}).get("total", 0) if wrong else 0) + by_type.get("UNCLASSIFIED", 0)
    # P2: DEAD_FEATURE + hidden + orphans
    p2_count = by_status.get("DEAD_FEATURE", 0) + (orph.get("metadata", {}).get("total", 0) if orph else 0)

    return jsonify({
        "ok": True,
        "summary": {
            "total_features": len(features),
            "by_status": by_status,
            "by_type": by_type,
            "by_level": by_level,
        },
        "governance_counts": {
            "duplicates": dups.get("metadata", {}).get("total", 0) if dups else 0,
            "wrong_ownership": wrong.get("metadata", {}).get("total", 0) if wrong else 0,
            "orphans": orph.get("metadata", {}).get("total", 0) if orph else 0,
            "unclassified": unc.get("metadata", {}).get("total", 0) if unc else 0,
            "P0": p0_count,
            "P1": p1_count,
            "P2": p2_count,
        },
    })


@feature_governance_bp.route("/runtime-matrix", methods=["GET"])
def get_runtime_matrix():
    """返回 Runtime Contract 矩阵（每个 feature 的 UI/API/Service/DB/Schema/Runtime/数据/交互）。"""
    matrix = _load_json("feature_runtime_matrix.json")
    if matrix is None:
        return jsonify({"ok": False, "error": "feature_runtime_matrix.json not found"}), 404
    return jsonify({
        "ok": True,
        "total": matrix.get("metadata", {}).get("total", 0),
        "status_distribution": matrix.get("metadata", {}).get("status_distribution", {}),
        "matrix": matrix.get("matrix", []),
    })


print("[feature_governance] blueprint registered: /api/feature-registry/*")

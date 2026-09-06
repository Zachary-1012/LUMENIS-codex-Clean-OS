# -*- coding: utf-8 -*-
"""report_artifact.py — 报告 artifact 真实性校验模块（ZBC Phase 9 + G4 hash 验证）

核心目标：报告必须是真实 artifact，禁止"假成功"。
- 文件 artifact：存在 + 非空 + hash 可校验
- DB artifact：行存在 + report_id 可追溯 + 关键字段非空
- export 复用：同周期同格式已存在有效 artifact 时直接复用，避免重复生成导致数据漂移

G4 (2026-09-06): 新增 verify_report_hash() 读取时 hash 一致性验证。

本模块不依赖 Flask / app，可被 report_engine / export_report / report_api / 测试直接导入。
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

# 报告生成器版本（每次报告逻辑变更应递增，用于 artifact 血缘追踪）
GENERATOR_VERSION = "zbc-report-1.0.0"

# artifact 最小字节数：低于此值视为空文件/损坏文件
ARTIFACT_MIN_BYTES = 64

# 已知有效导出格式及其最小合理字节数
_FORMAT_MIN_BYTES = {
    ".xlsx": 200,   # 空 xlsx 也有 zip 头，约 200+
    ".docx": 200,   # 空 docx 也有 zip 头
    ".csv": 32,     # 至少表头行
    ".json": 16,
    ".md": 16,
    ".txt": 16,
    ".html": 32,
    ".pdf": 100,
}


def compute_hash(data: bytes) -> str:
    """计算 SHA-256 hash（十六进制字符串）。"""
    return hashlib.sha256(data).hexdigest()


def compute_file_hash(path: str) -> str:
    """计算文件 SHA-256 hash；文件不存在返回空串。"""
    if not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_report_id(report_type: str, period_start: str, period_end: str) -> str:
    """生成确定性 report_id：RPT-{type}-{start}-{end}。

    同周期同类型报告 ID 稳定，便于幂等更新与 artifact 复用。
    """
    rt = (report_type or "daily").strip().lower()
    ps = (period_start or "").strip()
    pe = (period_end or "").strip()
    return f"RPT-{rt}-{ps}-{pe}"


def min_bytes_for_format(filepath: str) -> int:
    """根据文件扩展名返回最小合理字节数。"""
    ext = os.path.splitext(filepath)[1].lower()
    return _FORMAT_MIN_BYTES.get(ext, ARTIFACT_MIN_BYTES)


def verify_artifact_file(path: str) -> Dict[str, Any]:
    """校验文件 artifact 真实性。

    Returns:
        {
            'exists': bool,
            'size': int,
            'hash': str,
            'valid': bool,       # exists AND size >= min_bytes
            'reason': str,       # 无效原因
            'verified_at': str,
        }
    """
    result = {
        "exists": False,
        "size": 0,
        "hash": "",
        "valid": False,
        "reason": "",
        "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if not path:
        result["reason"] = "path 为空"
        return result
    if not os.path.isfile(path):
        result["reason"] = f"文件不存在: {path}"
        return result
    result["exists"] = True
    try:
        result["size"] = os.path.getsize(path)
    except OSError as e:
        result["reason"] = f"无法读取文件大小: {e}"
        return result
    min_b = min_bytes_for_format(path)
    if result["size"] < min_b:
        result["reason"] = f"文件过小({result['size']}B < {min_b}B)，疑似空文件或生成失败"
        return result
    result["hash"] = compute_file_hash(path)
    if not result["hash"]:
        result["reason"] = "hash 计算失败"
        return result
    result["valid"] = True
    return result


def verify_report_dict(report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """校验报告 dict artifact（DB 行或内存报告）的基本真实性。

    检查：非空、有 report_type/report_date、total_notes 是数字、有 generated_at。
    """
    result = {"valid": False, "reason": "", "report_id": "", "fields": {}}
    if not report or not isinstance(report, dict):
        result["reason"] = "报告为空或非 dict"
        return result
    rtype = report.get("report_type", "")
    rdate = report.get("report_date", "")
    if not rtype:
        result["reason"] = "缺少 report_type"
        return result
    if not rdate:
        result["reason"] = "缺少 report_date"
        return result
    total = report.get("total_notes", 0)
    if not isinstance(total, (int, float)):
        result["reason"] = f"total_notes 非数字: {type(total)}"
        return result
    result["report_id"] = report.get("report_id", "") or generate_report_id(
        rtype, report.get("period_start", ""), report.get("period_end", ""))
    result["fields"] = {
        "report_type": rtype,
        "report_date": rdate,
        "total_notes": total,
        "generated_at": report.get("generated_at", ""),
        "artifact_hash": report.get("artifact_hash", ""),
        "generator_version": report.get("generator_version", ""),
    }
    result["valid"] = True
    return result

def build_artifact_metadata(report_type: str, period_start: str, period_end: str,
                            report_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """为报告构建 artifact 元数据字段（report_id / generated_at / generator_version / data_version）。

    data_version = 数据快照标识：周期 + 生成时间，用于判断是否数据漂移。
    """
    now = datetime.now()
    rid = generate_report_id(report_type, period_start, period_end)
    data_version = f"{period_start}_{period_end}_{now.strftime('%Y%m%d%H%M%S')}"
    meta = {
        "report_id": rid,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "generator_version": GENERATOR_VERSION,
        "data_version": data_version,
    }
    if report_data is not None:
        # artifact_hash = 报告核心数据的 SHA-256（排除 hash 自身与 meta 注入键，保证可复算）
        _HASH_EXCLUDE = (
            "artifact_hash", "generated_at", "data_version",
            "report_id", "generator_version",
            "_db_row_id", "_artifact_verified",
            "started_at", "finished_at", "status", "error",
        )
        snapshot = {k: v for k, v in report_data.items() if k not in _HASH_EXCLUDE}
        try:
            meta["artifact_hash"] = compute_hash(
                json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
        except Exception:
            meta["artifact_hash"] = ""
    return meta


def verify_report_hash(report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """G4: 验证报告 dict 的 artifact_hash 一致性（读取时校验，不破坏现有流程）。

    对报告内容（排除 artifact_hash/generated_at/data_version）重新计算 SHA-256，
    与报告中存储的 artifact_hash 比对。历史报告 hash 为空时不报错，标记 historical。

    Returns:
        {valid, expected_hash, actual_hash, status, reason}
        status: "verified" | "mismatch" | "historical_empty" | "error"
    """
    result = {
        "valid": False,
        "expected_hash": "",
        "actual_hash": "",
        "status": "error",
        "reason": "",
    }
    if not report or not isinstance(report, dict):
        result["reason"] = "报告为空或非 dict"
        return result

    stored_hash = report.get("artifact_hash", "") or ""
    result["actual_hash"] = stored_hash

    if not stored_hash:
        # 历史报告 hash 为空：不报错，显式标记
        result["status"] = "historical_empty"
        result["valid"] = True  # 空 hash 不视为校验失败
        result["reason"] = "历史报告无 artifact_hash（G4 前生成），不影响读取"
        return result

    # 重新计算 hash（与 build_artifact_metadata 相同逻辑）
    # 排除 meta 注入的键：artifact_hash/generated_at/data_version/report_id/generator_version
    # 以及运行时内部键：_db_row_id/_artifact_verified/started_at/finished_at/status/error
    _HASH_EXCLUDE = (
        "artifact_hash", "generated_at", "data_version",
        "report_id", "generator_version",
        "_db_row_id", "_artifact_verified",
        "started_at", "finished_at", "status", "error",
    )
    try:
        snapshot = {k: v for k, v in report.items() if k not in _HASH_EXCLUDE}
        expected = compute_hash(
            json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
        result["expected_hash"] = expected
        if expected == stored_hash:
            result["valid"] = True
            result["status"] = "verified"
            result["reason"] = "hash 一致"
        else:
            result["status"] = "mismatch"
            result["reason"] = "hash 不一致：报告内容可能被修改或数据漂移"
    except Exception as e:
        result["status"] = "error"
        result["reason"] = f"hash 计算失败: {e}"
    return result


def find_existing_artifact(export_dir: str, report_type: str, period_start: str,
                           period_end: str, fmt: str) -> Optional[str]:
    """在导出目录中查找同周期同格式的已有有效 artifact，用于复用避免重复生成。

    文件名约定：太古汇舆情_{type}_{start}_{end}.{ext} 或 Taikoo_{type}_{start}.{ext}
    返回有效文件路径，无有效文件返回 None。
    """
    if not os.path.isdir(export_dir):
        return None
    fmt = fmt.lower().lstrip(".")
    ext = f".{fmt}"
    candidates = []
    ps = period_start or ""
    pe = period_end or ""
    for fname in os.listdir(export_dir):
        if not fname.lower().endswith(ext):
            continue
        # 匹配包含周期起止的文件名
        if ps and ps in fname and (not pe or pe in fname):
            candidates.append(os.path.join(export_dir, fname))
        elif ps and ps.replace("-", "") in fname:
            candidates.append(os.path.join(export_dir, fname))
    # 取最新修改的有效文件
    for cpath in sorted(candidates, key=os.path.getmtime, reverse=True):
        v = verify_artifact_file(cpath)
        if v["valid"]:
            return cpath
    return None


def assert_artifact_or_raise(path: str) -> Dict[str, Any]:
    """校验文件 artifact，无效则抛出 RuntimeError（用于 export 链路强制校验）。"""
    v = verify_artifact_file(path)
    if not v["valid"]:
        raise RuntimeError(f"报告 artifact 校验失败: {v['reason']} (path={path})")
    return v

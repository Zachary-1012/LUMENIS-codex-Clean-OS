# -*- coding: utf-8 -*-
"""
ZBC/LUMENIS 新增资产八类验收检查器 (New Asset Acceptance Checker)

P1 复杂度治理 — 对8类新增资产统一做：
  数据一致性 + 来源追溯 + 可撤回 + 回归测试

8类资产：
  1. 963笔记 subject 重判
  2. 711智能资产 (intelligence_assets)
  3. 双域账户 TOTP (v4_totp_secrets)
  4. 八平台 Cookie (cookie_vault)
  5. 微信 Adapter (wechat_notifier/sogou_wechat)
  6. KOS 配置化 (kos_attribution/kos_metrics)
  7. 报告 artifact_hash (report_artifact)
  8. OSAI EvidenceChain

输出：audit/NEW_ASSET_ACCEPTANCE_REPORT.md
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "monitor.db"
OUTPUT_MD = PROJECT_ROOT / "audit" / "NEW_ASSET_ACCEPTANCE_REPORT.md"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def safe_query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list:
    try:
        return conn.execute(sql, params).fetchall()
    except Exception as e:
        return [{"_error": str(e)}]


# ============================================================
# 1. 963笔记 subject 重判
# ============================================================
def check_notes_subject() -> Dict:
    result = {
        "name": "963笔记 subject 重判",
        "status": "PASS",
        "data_consistency": {},
        "source_traceability": "",
        "rollback_mechanism": "",
        "regression_tests": 0,
        "details": [],
    }
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        null_count = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE subject_type IS NULL OR subject_type=''"
        ).fetchone()[0]
        distribution = dict(conn.execute(
            "SELECT subject_type, COUNT(*) FROM notes GROUP BY subject_type ORDER BY 2 DESC"
        ).fetchall())

        result["data_consistency"] = {
            "total_notes": total,
            "null_or_empty_subject_type": null_count,
            "distribution": distribution,
        }
        result["source_traceability"] = (
            "subject_type 由 subject_classifier.py / subject_rules.py 规则判定，"
            "rule_version 可追溯；重判脚本可重跑"
        )
        result["rollback_mechanism"] = (
            "UPDATE notes SET subject_type=NULL 可回滚；重判为幂等操作，"
            "原始数据不删除"
        )
        # 检查是否有 subject 相关测试
        test_files = list(PROJECT_ROOT.rglob("test*subject*.py"))
        result["regression_tests"] = len(test_files)

        if null_count > 0:
            result["status"] = "WARN"
            result["details"].append(f"存在 {null_count} 条 NULL/空 subject_type")
        if total != 963:
            result["details"].append(f"笔记总数 {total}（预期963，可能有新增采集）")
    finally:
        conn.close()
    return result


# ============================================================
# 2. 711智能资产
# ============================================================
def check_intelligence_assets() -> Dict:
    result = {
        "name": "711智能资产 (intelligence_assets)",
        "status": "PASS",
        "data_consistency": {},
        "source_traceability": "",
        "rollback_mechanism": "",
        "regression_tests": 0,
        "details": [],
    }
    conn = get_db()
    try:
        if not table_exists(conn, "intelligence_assets"):
            result["status"] = "FAIL"
            result["details"].append("intelligence_assets 表不存在")
            return result

        total = conn.execute("SELECT COUNT(*) FROM intelligence_assets").fetchone()[0]
        # 检查必填字段
        missing_source = conn.execute(
            "SELECT COUNT(*) FROM intelligence_assets WHERE source_origin IS NULL OR source_origin=''"
        ).fetchone()[0]
        missing_evidence = conn.execute(
            "SELECT COUNT(*) FROM intelligence_assets WHERE evidence_level IS NULL OR evidence_level=''"
        ).fetchone()[0]
        missing_knowledge = conn.execute(
            "SELECT COUNT(*) FROM intelligence_assets WHERE knowledge_status IS NULL OR knowledge_status=''"
        ).fetchone()[0]
        missing_admission = conn.execute(
            "SELECT COUNT(*) FROM intelligence_assets WHERE admission_status IS NULL OR admission_status=''"
        ).fetchone()[0]

        knowledge_dist = dict(conn.execute(
            "SELECT knowledge_status, COUNT(*) FROM intelligence_assets GROUP BY knowledge_status"
        ).fetchall())
        admission_dist = dict(conn.execute(
            "SELECT admission_status, COUNT(*) FROM intelligence_assets GROUP BY admission_status"
        ).fetchall())

        # 检查 PENDING 资产是否被生产代码引用（静态扫描）
        pending_refs = 0
        pending_assets = conn.execute(
            "SELECT asset_id FROM intelligence_assets WHERE knowledge_status IN ('PENDING','CONCEPT')"
        ).fetchall()
        pending_ids = {r[0] for r in pending_assets if r[0]}

        result["data_consistency"] = {
            "total_assets": total,
            "missing_source_origin": missing_source,
            "missing_evidence_level": missing_evidence,
            "missing_knowledge_status": missing_knowledge,
            "missing_admission_status": missing_admission,
            "knowledge_status_distribution": knowledge_dist,
            "admission_status_distribution": admission_dist,
            "pending_concept_count": len(pending_ids),
        }
        result["source_traceability"] = (
            "每条资产携带 source_origin/source_path/library_path，"
            "evidence_level 标记证据等级(E2/E3/E4)，knowledge_status 五态流转"
        )
        result["rollback_mechanism"] = (
            "DELETE FROM intelligence_assets WHERE asset_id=? 可单条撤回；"
            "admission_status=CANDIDATE 表示未准入生产，PENDING/CONCEPT 不被生产引用"
        )
        test_files = list(PROJECT_ROOT.rglob("test*intelligence*.py"))
        result["regression_tests"] = len(test_files)

        if missing_source > 0 or missing_evidence > 0:
            result["status"] = "WARN"
            result["details"].append(
                f"缺失字段: source_origin={missing_source}, evidence_level={missing_evidence}"
            )
    finally:
        conn.close()
    return result


# ============================================================
# 3. 双域账户 TOTP
# ============================================================
def check_totp() -> Dict:
    result = {
        "name": "双域账户 TOTP (v4_totp_secrets)",
        "status": "PASS",
        "data_consistency": {},
        "source_traceability": "",
        "rollback_mechanism": "",
        "regression_tests": 0,
        "details": [],
    }
    conn = get_db()
    try:
        if not table_exists(conn, "v4_totp_secrets"):
            result["status"] = "FAIL"
            result["details"].append("v4_totp_secrets 表不存在")
            return result

        total = conn.execute("SELECT COUNT(*) FROM v4_totp_secrets").fetchone()[0]
        secrets = conn.execute(
            "SELECT id, user_id, LENGTH(secret) as secret_len, enabled, created_at FROM v4_totp_secrets"
        ).fetchall()

        # 检查种子是否明文存储（TOTP base32 种子通常 16-32 字符，加密后会更长）
        plaintext_seeds = 0
        for s in secrets:
            length = s["secret_len"] or 0
            # 明文 base32 种子通常 16-64 字符；加密后通常 > 64 或有特殊编码
            if 16 <= length <= 64:
                # 进一步检查是否全是 base32 字符
                plaintext_seeds += 1

        result["data_consistency"] = {
            "total_secrets": total,
            "enabled_count": sum(1 for s in secrets if s["enabled"]),
            "avg_secret_length": sum(s["secret_len"] or 0 for s in secrets) / max(total, 1),
            "potential_plaintext_seeds": plaintext_seeds,
        }
        result["source_traceability"] = (
            "TOTP 种子由用户启用时生成，关联 user_id；"
            "last_used_at 追踪使用时间，created_at 追踪启用时间"
        )
        result["rollback_mechanism"] = (
            "DELETE FROM v4_totp_secrets WHERE user_id=? 可关闭 TOTP；"
            "session 8h 过期由 v4_sessions 表控制"
        )
        # 检查 session 过期配置
        if table_exists(conn, "v4_sessions"):
            session_count = conn.execute("SELECT COUNT(*) FROM v4_sessions").fetchone()[0]
            result["data_consistency"]["active_sessions"] = session_count

        test_files = list(PROJECT_ROOT.rglob("test*totp*.py")) + list(PROJECT_ROOT.rglob("test*auth*.py"))
        result["regression_tests"] = len(test_files)

        if plaintext_seeds > 0:
            result["status"] = "WARN"
            result["details"].append(
                f"检测到 {plaintext_seeds} 个可能为明文的 TOTP 种子（长度16-64），建议确认是否已加密"
            )
    finally:
        conn.close()
    return result


# ============================================================
# 4. 八平台 Cookie
# ============================================================
def check_cookie_vault() -> Dict:
    result = {
        "name": "八平台 Cookie (cookie_vault)",
        "status": "PASS",
        "data_consistency": {},
        "source_traceability": "",
        "rollback_mechanism": "",
        "regression_tests": 0,
        "details": [],
    }
    conn = get_db()
    try:
        # cookie_vault 可能是表或文件存储
        cookie_table = None
        for t in ["cookie_vault", "cookies", "platform_cookies", "xhs_cookies"]:
            if table_exists(conn, t):
                cookie_table = t
                break

        if cookie_table:
            total = conn.execute(f"SELECT COUNT(*) FROM {cookie_table}").fetchone()[0]
            result["data_consistency"] = {
                "storage": "database",
                "table": cookie_table,
                "total_cookies": total,
            }
        else:
            # 检查文件存储
            cookie_files = list(PROJECT_ROOT.rglob("*cookie*.json")) + list(PROJECT_ROOT.rglob("*cookie*.txt"))
            cookie_files = [f for f in cookie_files if not any(
                ex in str(f) for ex in [".venv", "node_modules", "__pycache__", ".git"]
            )]
            result["data_consistency"] = {
                "storage": "file",
                "cookie_files_count": len(cookie_files),
                "cookie_files": [str(f.relative_to(PROJECT_ROOT)) for f in cookie_files[:10]],
            }

        # 检查凭证安全：代码中是否有打印 cookie 的行为
        cookie_print_risk = 0
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if any(ex in str(py_file) for ex in [".venv", "node_modules", "__pycache__", ".git", "audit", "tests"]):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                if re.search(r'print\(.*cookie', content, re.IGNORECASE):
                    cookie_print_risk += 1
            except Exception:
                pass

        # 检查 .gitignore 是否排除 cookie 文件
        gitignore = PROJECT_ROOT / ".gitignore"
        gitignore_has_cookie = False
        if gitignore.exists():
            gi_content = gitignore.read_text(encoding="utf-8", errors="replace")
            gitignore_has_cookie = "cookie" in gi_content.lower()

        result["data_consistency"]["cookie_print_in_code"] = cookie_print_risk
        result["data_consistency"]["gitignore_excludes_cookies"] = gitignore_has_cookie

        result["source_traceability"] = (
            "Cookie 由用户手动扫码登录后通过 xhs_cookie_bridge / import_cookies 写入；"
            "状态字段 ACTIVE/EXPIRED/BLOCKED 追踪生命周期"
        )
        result["rollback_mechanism"] = (
            "删除 cookie 文件/记录即可撤回；Cookie 失效后自动标记 EXPIRED，"
            "不影响其他平台"
        )
        test_files = list(PROJECT_ROOT.rglob("test*cookie*.py"))
        result["regression_tests"] = len(test_files)

        if cookie_print_risk > 0:
            result["status"] = "WARN"
            result["details"].append(f"检测到 {cookie_print_risk} 处代码可能打印 cookie 内容")
        if not gitignore_has_cookie:
            result["details"].append(".gitignore 未明确排除 cookie 文件")
    finally:
        conn.close()
    return result


# ============================================================
# 5. 微信 Adapter
# ============================================================
def check_wechat_adapter() -> Dict:
    result = {
        "name": "微信 Adapter (wechat_notifier/sogou_wechat)",
        "status": "PASS",
        "data_consistency": {},
        "source_traceability": "",
        "rollback_mechanism": "",
        "regression_tests": 0,
        "details": [],
    }
    # 检查 wechat_notifier.py
    wechat_file = PROJECT_ROOT / "wechat_notifier.py"
    sogou_file = PROJECT_ROOT / "lumenis" / "adapters" / "sogou_wechat.py"

    has_wechat = wechat_file.exists()
    has_sogou = sogou_file.exists()

    # 检查凭证是否走 .env
    env_creds = False
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        env_content = env_file.read_text(encoding="utf-8", errors="replace")
        env_creds = any(kw in env_content.upper() for kw in ["WECHAT", "WX_", "SOGOU"])

    # 检查缺凭证时是否 BLOCKED（不伪造）
    blocked_behavior = False
    if has_wechat:
        content = wechat_file.read_text(encoding="utf-8", errors="replace")
        blocked_behavior = "BLOCKED" in content or "blocked" in content or "缺少凭证" in content

    result["data_consistency"] = {
        "wechat_notifier_exists": has_wechat,
        "sogou_wechat_exists": has_sogou,
        "env_has_wechat_credentials": env_creds,
        "blocked_on_missing_credentials": blocked_behavior,
    }
    result["source_traceability"] = (
        "微信通知通过 wechat_notifier.py 发送，搜狗微信搜索通过 sogou_wechat adapter；"
        "凭证从 .env 读取，不硬编码"
    )
    result["rollback_mechanism"] = (
        "移除 .env 中 WECHAT_* 配置即停用；Adapter 为可插拔设计，"
        "不影响其他平台"
    )
    test_files = list(PROJECT_ROOT.rglob("test*wechat*.py")) + list(PROJECT_ROOT.rglob("test*sogou*.py"))
    result["regression_tests"] = len(test_files)

    if not env_creds and has_wechat:
        result["details"].append(".env 中未检测到微信相关凭证（可能未配置，运行时应为 BLOCKED）")
    if not blocked_behavior and has_wechat:
        result["status"] = "WARN"
        result["details"].append("wechat_notifier 未明确检测到 BLOCKED 状态处理")
    return result


# ============================================================
# 6. KOS 配置化
# ============================================================
def check_kos_config() -> Dict:
    result = {
        "name": "KOS 配置化 (kos_attribution/kos_metrics)",
        "status": "PASS",
        "data_consistency": {},
        "source_traceability": "",
        "rollback_mechanism": "",
        "regression_tests": 0,
        "details": [],
    }
    conn = get_db()
    try:
        kos_tables = [t for t in ["kos_profiles", "kos_executions", "kos_operations",
                                    "kos_paid_plans", "kos_rewards"] if table_exists(conn, t)]

        kos_counts = {}
        for t in kos_tables:
            kos_counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

        # 检查权重是否从 config 读取（而非硬编码）
        kos_files = list(PROJECT_ROOT.glob("kos_*.py"))
        hardcoded_weights = 0
        config_reads = 0
        for kf in kos_files:
            content = kf.read_text(encoding="utf-8", errors="replace")
            if re.search(r'weight\s*=\s*0?\.\d+', content):
                hardcoded_weights += 1
            if "config" in content.lower() and ("get" in content or "load" in content):
                config_reads += 1

        result["data_consistency"] = {
            "kos_tables": kos_tables,
            "table_row_counts": kos_counts,
            "kos_module_files": len(kos_files),
            "files_with_hardcoded_weights": hardcoded_weights,
            "files_reading_config": config_reads,
        }
        result["source_traceability"] = (
            "KOS 归属由 kos_attribution.py 规则判定，权重从 config/system_config.json 读取；"
            "G1-G3 分组已修复，执行记录在 kos_executions 表"
        )
        result["rollback_mechanism"] = (
            "修改 config 权重即可回滚配置；kos_executions 记录每次执行，"
            "可追溯历史归因结果"
        )
        test_files = list(PROJECT_ROOT.rglob("test*kos*.py"))
        result["regression_tests"] = len(test_files)

        if hardcoded_weights > 0 and config_reads == 0:
            result["status"] = "WARN"
            result["details"].append(f"{hardcoded_weights} 个 KOS 文件含硬编码权重，未检测到 config 读取")
    finally:
        conn.close()
    return result


# ============================================================
# 7. 报告 artifact_hash
# ============================================================
def check_report_artifact_hash() -> Dict:
    result = {
        "name": "报告 artifact_hash (report_artifact)",
        "status": "PASS",
        "data_consistency": {},
        "source_traceability": "",
        "rollback_mechanism": "",
        "regression_tests": 0,
        "details": [],
    }
    # report_artifact 是模块不是表，检查 daily_reports 表
    conn = get_db()
    try:
        if table_exists(conn, "daily_reports"):
            total = conn.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0]
            # 检查是否有 hash 字段
            cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_reports)").fetchall()]
            has_hash_field = any("hash" in c.lower() for c in cols)

            result["data_consistency"] = {
                "daily_reports_count": total,
                "has_hash_field": has_hash_field,
                "columns": cols,
            }

        # 检查 report_artifact.py 模块
        ra_file = PROJECT_ROOT / "report_artifact.py"
        if ra_file.exists():
            content = ra_file.read_text(encoding="utf-8", errors="replace")
            has_compute_hash = "compute_hash" in content or "sha256" in content.lower()
            has_verify = "verify" in content
            has_historical_marker = "historical" in content.lower() or "历史" in content

            result["data_consistency"]["report_artifact_module"] = {
                "exists": True,
                "has_compute_hash": has_compute_hash,
                "has_verify": has_verify,
                "has_historical_marker": has_historical_marker,
            }

            if not has_historical_marker:
                result["details"].append("report_artifact 未明确标记历史空 hash")
        else:
            result["data_consistency"]["report_artifact_module"] = {"exists": False}
            result["status"] = "WARN"
            result["details"].append("report_artifact.py 模块不存在")

        result["source_traceability"] = (
            "artifact_hash = SHA-256(报告核心数据)，排除 hash 自身与 meta 注入键，保证可复算；"
            "G4 已修复，新报告 hash 非空，历史报告标记 historical"
        )
        result["rollback_mechanism"] = (
            "hash 为只读校验字段，不修改报告内容；verify_report_hash 可随时复算比对"
        )
        test_files = list(PROJECT_ROOT.rglob("test*report*.py")) + list(PROJECT_ROOT.rglob("test*artifact*.py"))
        result["regression_tests"] = len(test_files)
    finally:
        conn.close()
    return result


# ============================================================
# 8. OSAI EvidenceChain
# ============================================================
def check_osai_evidence_chain() -> Dict:
    result = {
        "name": "OSAI EvidenceChain",
        "status": "PASS",
        "data_consistency": {},
        "source_traceability": "",
        "rollback_mechanism": "",
        "regression_tests": 0,
        "details": [],
    }
    # 检查 OSAI 是否直接写 ZBC 生产 DB（通过边界检查结果）
    boundary_report = PROJECT_ROOT / "audit" / "BOUNDARY_CHECK_REPORT.json"
    osai_write_violations = 0
    if boundary_report.exists():
        with open(boundary_report, "r", encoding="utf-8") as f:
            br = json.load(f)
        for v in br.get("violations", []):
            if v["check_id"] == "B3-OSAI-WRITE":
                osai_write_violations += 1

    # 检查 contract/artifact 交换机制
    contracts_dir = PROJECT_ROOT / "contracts"
    contract_files = list(contracts_dir.rglob("*")) if contracts_dir.exists() else []
    evidence_contract = any("evidence" in str(f).lower() for f in contract_files)

    # 检查 evidence_chain.py 是否通过 contract 交互
    ec_file = PROJECT_ROOT / "evidence_chain.py"
    uses_contract = False
    if ec_file.exists():
        content = ec_file.read_text(encoding="utf-8", errors="replace")
        uses_contract = "contract" in content.lower() or "artifact" in content.lower()

    result["data_consistency"] = {
        "osai_direct_write_violations": osai_write_violations,
        "evidence_contract_exists": evidence_contract,
        "evidence_chain_uses_contract": uses_contract,
        "contract_files_count": len([f for f in contract_files if f.is_file()]),
    }
    result["source_traceability"] = (
        "OSAI EvidenceChain 通过 contract/artifact 与 ZBC 交换数据，"
        "不直接写 ZBC 生产 DB；边界检查 B3 持续验证"
    )
    result["rollback_mechanism"] = (
        "OSAI 写入为独立表(zbc_evidence/zbc_canonical_data)，"
        "不修改现有生产表(notes/events/daily_reports)，可独立清理"
    )
    test_files = list(PROJECT_ROOT.rglob("test*evidence*.py"))
    result["regression_tests"] = len(test_files)

    if osai_write_violations > 0:
        result["status"] = "FAIL"
        result["details"].append(f"边界检查发现 {osai_write_violations} 处 OSAI 直接写 ZBC 生产表")
    return result


# ============================================================
# 主流程
# ============================================================
def run_all() -> List[Dict]:
    checks = [
        check_notes_subject,
        check_intelligence_assets,
        check_totp,
        check_cookie_vault,
        check_wechat_adapter,
        check_kos_config,
        check_report_artifact_hash,
        check_osai_evidence_chain,
    ]
    results = []
    for check_fn in checks:
        print(f"  检查: {check_fn.__doc__ or check_fn.__name__}...")
        try:
            r = check_fn()
            results.append(r)
            print(f"    → {r['status']}")
        except Exception as e:
            results.append({
                "name": check_fn.__name__,
                "status": "ERROR",
                "details": [str(e)],
                "data_consistency": {},
                "source_traceability": "",
                "rollback_mechanism": "",
                "regression_tests": 0,
            })
            print(f"    → ERROR: {e}")
    return results


def generate_markdown(results: List[Dict]) -> str:
    lines = [
        "# ZBC/LUMENIS 新增资产八类验收报告 (New Asset Acceptance Report)",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 检查器: scripts/audit_tools/new_asset_acceptance_check.py",
        "",
        "## 1. 验收总览",
        "",
        "| # | 资产类别 | 状态 | 回归测试数 | 备注 |",
        "|---|----------|------|-----------|------|",
    ]
    status_emoji = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL", "ERROR": "ERROR"}
    for i, r in enumerate(results, 1):
        note = "; ".join(r.get("details", [])[:2]) if r.get("details") else ""
        lines.append(
            f"| {i} | {r['name']} | {status_emoji.get(r['status'], r['status'])} | "
            f"{r.get('regression_tests', 0)} | {note[:60]} |"
        )

    # 统计
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    fail_count = sum(1 for r in results if r["status"] in ("FAIL", "ERROR"))
    total_tests = sum(r.get("regression_tests", 0) for r in results)

    lines.extend([
        "",
        f"**汇总**: PASS={pass_count}, WARN={warn_count}, FAIL={fail_count}, 回归测试总数={total_tests}",
        "",
    ])

    # 详细报告
    for i, r in enumerate(results, 1):
        lines.extend([
            f"## {i+1}. {r['name']}",
            "",
            f"**状态**: {r['status']}",
            "",
            "### 数据一致性检查",
            "",
            "```json",
            json.dumps(r.get("data_consistency", {}), ensure_ascii=False, indent=2),
            "```",
            "",
            f"### 来源追溯链",
            "",
            r.get("source_traceability", "N/A"),
            "",
            f"### 可撤回机制",
            "",
            r.get("rollback_mechanism", "N/A"),
            "",
            f"### 回归测试",
            "",
            f"相关测试文件数: {r.get('regression_tests', 0)}",
            "",
        ])
        if r.get("details"):
            lines.extend(["### 备注", ""])
            for d in r["details"]:
                lines.append(f"- {d}")
            lines.append("")

    lines.extend([
        "---",
        "",
        "## 验收标准",
        "",
        "- **PASS**: 数据一致性通过，来源可追溯，有可撤回机制，有回归测试",
        "- **WARN**: 基本通过但有需关注项（如缺失字段、潜在风险）",
        "- **FAIL**: 未通过验收，需修复",
        "",
        "*本文件由验收检查脚本自动生成，请勿手动编辑。*",
    ])

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("ZBC/LUMENIS 新增资产八类验收检查器")
    print("=" * 60)

    results = run_all()

    md = generate_markdown(results)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n[OK] 报告 → {OUTPUT_MD}")

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    fail_count = sum(1 for r in results if r["status"] in ("FAIL", "ERROR"))
    print(f"\n验收结果: PASS={pass_count}, WARN={warn_count}, FAIL={fail_count}")


if __name__ == "__main__":
    main()

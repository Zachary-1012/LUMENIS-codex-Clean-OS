# -*- coding: utf-8 -*-
"""LUMENIS Production Core Contract Adapter (read-only).

本模块以 LUMENIS P0 契约兼容的 dict 形状，只读暴露 ZBC（Production Core）
的生产事实，供 OSAI / Skill 通过 Contract 调用，而不是直接 import ZBC 业务模块。

硬约束：
- 所有函数只读，不写数据库、不修改生产核心。
- 不触碰 app.py / risk_engine / collector / models / migrations 等生产业务核心。
- 不打印主体词表内容（可能敏感），只报告计数与存在性。
- stdlib only。
"""
import os
import sys

_ZBC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_ADAPTER_VERSION = "0.1.0"
_LUMENIS_CONTRACTS_VERSION = "P0-v1-20260905"

LUMENIS_RED_LINES = [
    "①不合并两Git Repository",
    "②不删除ZBC生产业务核心",
    "③subject_hit()/Subject Authority不可被Skill绕过",
    "④AI永远不是业务事实最终裁判",
    "⑤Skill无无限权限",
    "⑥Agent不绕过HUMAN_APPROVAL",
    "⑦不允许无限Engineering Loop",
    "⑧不静默删除数据",
    "⑨文档不代替源码事实",
    "⑩所有改变可追溯到Evidence",
]


def _load_subject_rules():
    """惰性加载 subject_rules；失败返回 None，绝不抛异常。

    仅读取常量长度与函数存在性，不调用任何有副作用的函数。
    """
    if _ZBC_ROOT not in sys.path:
        sys.path.insert(0, _ZBC_ROOT)
    try:
        import subject_rules  # noqa: F401  仅读取常量与函数存在性
        return subject_rules
    except Exception as exc:  # noqa: BLE001  只读探测，任何失败都降级
        return exc


def production_core_snapshot():
    """ZBC 生产核心只读快照。"""
    return {
        "core": "Production Core",
        "repo": "Z-Brand-Core",
        "role": "production",
        "brand": "LUMENIS / 序境",
        "subject_authority": (
            "subject_hit() / SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS locked "
            "(read-only, not bypassable by Skill)"
        ),
        "capabilities": [
            "subject", "brand", "content", "public_opinion", "event",
            "risk", "kos_kol_koc", "campaign", "case", "report", "collector",
        ],
        "red_lines": LUMENIS_RED_LINES,
        "contracts_implemented": {
            "task": "read-only consumer",
            "trace": "read-only consumer",
            "evidence": "read-only consumer (uses existing evidence_store.py)",
            "evaluation": "read-only consumer",
            "lifecycle": "read-only consumer",
            "skill": "read-only consumer",
            "ai_gateway": "read-only consumer",
        },
    }


def subject_authority_readonly():
    """主体口径保护状态只读汇总。

    只报告 SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS 的长度，以及 subject_hit
    函数是否存在；绝不返回词表具体内容。
    """
    sr = _load_subject_rules()
    note = "counts only, contents not exposed"
    if isinstance(sr, Exception):
        return {
            "status": "module_not_found",
            "detail": "%s: %s" % (type(sr).__name__, sr),
            "subject_words_count": None,
            "exclude_words_count": None,
            "subject_hit_present": False,
            "note": note,
        }
    subject_words = getattr(sr, "SUBJECT_WORDS", None)
    exclude_words = getattr(sr, "SUBJECT_EXCLUDE_WORDS", None)
    return {
        "status": "ok",
        "subject_words_count": len(subject_words) if subject_words is not None else 0,
        "exclude_words_count": len(exclude_words) if exclude_words is not None else 0,
        "subject_hit_present": callable(getattr(sr, "subject_hit", None)),
        "note": note,
    }


def contract_compatibility():
    """声明本适配层实现的 LUMENIS 契约版本与角色。"""
    return {
        "adapter_version": _ADAPTER_VERSION,
        "lumenis_contracts_version": _LUMENIS_CONTRACTS_VERSION,
        "role": "Production Core read-only adapter",
        "exposes": [
            "production_core_snapshot",
            "subject_authority_readonly",
            "contract_compatibility",
        ],
        "writes": False,
        "db_writes": False,
    }


def get_production_facts():
    """轻量只读运行时事实聚合（不连数据库）。"""
    return {
        "python_executable": sys.executable,
        "cwd": os.getcwd(),
        "adapter_version": _ADAPTER_VERSION,
    }


def repository_registry_snapshot():
    """ZBC Repository Registry 只读快照（供 OSAI 双核联调）。

    不硬编码路径，通过 __file__ 动态定位 repo root。
    跨 Windows/macOS 兼容。
    """
    import subprocess
    repo_root = _ZBC_ROOT
    def _git(args):
        try:
            r = subprocess.run(["git"] + args, cwd=repo_root,
                               capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""
    return {
        "repository_id": "zbc-production-core",
        "name": "Z-Brand-Core",
        "role": "production",
        "root_path": repo_root,
        "git_remote": _git(["config", "--get", "remote.origin.url"]),
        "default_branch": "main",
        "current_branch": _git(["branch", "--show-current"]),
        "current_sha": _git(["rev-parse", "HEAD"]),
        "runtime": "python-flask-sqlite",
        "permissions": {
            "db_write": "production_only",
            "subject_rules": "locked_not_bypassable",
            "agent_commit": "requires_human_approval",
        },
        "status": "active",
    }


def permission_gate_snapshot():
    """ZBC Permission Gate 只读快照。

    声明 ZBC 侧的权限等级与默认策略，供 OSAI Permission Gate 对齐。
    不实际修改权限，只暴露事实。
    """
    return {
        "levels": [
            "READ", "AUDIT", "ANALYZE", "RESEARCH", "PLAN",
            "PATCH_PREVIEW", "TEST", "VERIFY",
            "HUMAN_APPROVAL", "COMMIT", "PUSH",
        ],
        "defaults": {
            "READ": "ALLOW",
            "AUDIT": "ALLOW",
            "ANALYZE": "ALLOW",
            "RESEARCH": "ALLOW",
            "PLAN": "ALLOW",
            "PATCH_PREVIEW": "ALLOW",
            "TEST": "ALLOW",
            "VERIFY": "ALLOW",
            "HUMAN_APPROVAL": "REQUIRED",
            "COMMIT": "BLOCKED_UNTIL_APPROVED",
            "PUSH": "BLOCKED_UNTIL_APPROVED",
        },
        "production_truth_protected": [
            "subject_hit()",
            "SUBJECT_WORDS",
            "SUBJECT_EXCLUDE_WORDS",
            "CollectorGuard",
            "aggregate_events()",
            "build_daily_report()",
            "data/monitor.db",
        ],
        "agent_may_not": [
            "modify_subject_rules",
            "bypass_subject_filter",
            "delete_production_data",
            "auto_commit_main",
            "auto_push_main",
            "auto_merge",
        ],
    }

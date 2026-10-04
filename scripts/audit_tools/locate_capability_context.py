"""Find the bounded LUMENIS context for one capability before changing it.

This is a navigation aid, not a product authority or an implementation audit.
It reports current rules separately from historical research and fails closed
when a requested file cannot be routed to one existing owner family.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CURRENT = (
    "AGENTS.md",
    "00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md",
    "00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md",
    "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
    "00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",
)

# These entries point to existing owners. Historical material is discovered
# per query, so a new research file does not require a manual registry edit.
FAMILIES = {
    "global_context": {
        "concern": "Global universe, focus context and data maturity",
        "terms": ("global", "focus", "全域", "聚焦", "主体"),
        "roots": ("subject_context.py", "subject_registry.py", "lumenis/shared/database", "lumenis/system/security"),
        "rules": ("00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md",),
    },
    "database": {
        "concern": "Shared Database",
        "terms": ("database", "migration", "schema", "数据库", "迁移"),
        "roots": ("lumenis/shared/database", "migrations", "canonical_data.py"),
        "rules": (),
    },
    "identity_permission": {
        "concern": "SYSTEM Permission/effects",
        "terms": ("account", "auth", "permission", "session", "权限", "账号", "身份"),
        "roots": ("account", "lumenis/auth", "lumenis/system/security"),
        "rules": ("00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md",),
    },
    "evidence": {
        "concern": "Shared Evidence",
        "terms": ("evidence", "lineage", "provenance", "证据", "溯源"),
        "roots": ("lumenis/shared/evidence", "canonical_data.py"),
        "rules": (),
    },
    "collector": {
        "concern": "SYSTEM collection",
        "terms": ("collector", "collection", "acquisition", "采集", "来源"),
        "roots": ("lumenis/system/collector",),
        "rules": ("00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md",),
    },
    "product_api": {
        "concern": "Product Core composition/API",
        "terms": ("api", "contract", "binding", "scope", "接口", "绑定"),
        "roots": ("app.py", "lumenis_app_api.py", "experience_runtime.py", "experience_screens.py"),
        "rules": ("00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md",),
    },
    "browser": {
        "concern": "SYSTEM browser/session",
        "terms": ("browser", "xhs", "rednote", "浏览器", "小红书"),
        "roots": ("lumenis/system/browser", "xhs_cookie_bridge.py", "xhs_p0_orchestrator.py"),
        "rules": ("00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md",),
    },
    "runtime": {
        "concern": "Startup/runtime",
        "terms": ("runtime", "startup", "scheduler", "recovery", "运行", "恢复"),
        "roots": ("lumenis/system/runtime", "run_supervised.py", "scripts/start_production.ps1"),
        "rules": (),
    },
    "ai_gateway": {
        "concern": "SYSTEM AI runtime",
        "terms": ("gateway", "model", "ollama", "jev", "模型", "网关"),
        "roots": ("lumenis/system/ai_gateway", "ai_api.py", "local_ai_client.py"),
        "rules": (),
    },
    "agents_skills": {
        "concern": "Shared skills/agent execution",
        "terms": ("agent", "skill", "memory", "智能体", "技能", "记忆"),
        "roots": ("lumenis/shared/agents/skills", "agent_runtime", "agent_capability", "agent_memory/working.py"),
        "rules": (),
    },
    "content_creation": {
        "concern": "Shared Content & Creation",
        "terms": ("creation", "content", "video", "podcast", "创作", "制作", "视频", "播客"),
        "roots": ("lumenis/shared/content_creation", "lumenis/shared/reporting/artifact.py", "content_generation.py", "podcast", "scripts/pitch_parser.py", "scripts/pitch_export.py", "scripts/campaign_plan.py", "scripts/perspective_adapter.py", "app/lib/features"),
        "rules": ("00-GOVERNANCE/LUMENIS-CONTENT-CREATION-LEARNING-SOURCE-CONTRACT-V1-20260911.md",),
    },
    "reporting": {
        "concern": "Shared Evaluation/Learning/Reporting",
        "terms": ("report", "export", "报告", "导出"),
        "roots": ("lumenis/shared/reporting", "reporting"),
        "rules": (),
    },
    "evaluation_learning": {
        "concern": "Shared Evaluation/Learning/Reporting",
        "terms": ("evaluation", "learning", "memory", "反馈", "评估", "学习", "记忆"),
        "roots": ("lumenis/shared/evaluation", "lumenis/shared/learning", "agent_memory/base.py"),
        "rules": (),
    },
    "cth_job": {
        "concern": "CTH/BMP business callers",
        "terms": ("cth", "commercial", "运营", "商业"),
        "roots": ("api_dual_domain.py", "subject_context.py", "subject_registry.py", "case_deep_analysis.py", "event_graph.py", "risk_engine.py", "app/lib/features"),
        "rules": ("00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md",),
    },
    "bmp_job": {
        "concern": "CTH/BMP business callers",
        "terms": ("bmp", "brand", "market", "品牌", "市场"),
        "roots": ("api_dual_domain.py", "subject_context.py", "subject_registry.py", "brand_knowledge_base.py", "brand_propagation.py", "ad_intelligence", "app/lib/features"),
        "rules": ("00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md",),
    },
    "experience": {
        "concern": "Experience authority",
        "terms": ("experience", "flutter", "screen", "体验", "界面"),
        "roots": ("app/lib", "website", "contracts/experience"),
        "rules": ("00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md", "00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md"),
    },
    "release": {
        "concern": "Tests and release evidence",
        "terms": ("release", "operating", "ci", "上线", "发布", "验收"),
        "roots": (".github/workflows", "deployment", "tests/release"),
        "rules": ("00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",),
    },
}

QUERY_EQUIVALENTS = {
    "播客": ("播客", "podcast"),
    "podcast": ("podcast", "播客"),
    "视频": ("视频", "video"),
    "video": ("video", "视频"),
    "比稿": ("比稿", "pitch", "提案"),
    "pitch": ("pitch", "比稿", "提案"),
    "提案": ("提案", "pitch", "比稿"),
    "聚焦": ("聚焦", "focus"),
    "focus": ("focus", "聚焦"),
    "采集": ("采集", "collection", "collector"),
    "collection": ("collection", "采集"),
    "权限": ("权限", "permission"),
    "permission": ("permission", "权限"),
}

_LOCAL_REFERENCE = re.compile(r"`([^`\n]+\.(?:md|json|py))`|\]\(([^)#]+\.(?:md|json|py))\)", re.IGNORECASE)
_GIT_BLOB_REFERENCE = re.compile(r"\b([0-9a-f]{40}):((?:00-GOVERNANCE|contracts|intelligence_library)/[^`\s]+\.(?:md|json))", re.IGNORECASE)


def _relative_existing(paths: tuple[str, ...] | list[str]) -> list[str]:
    return [p for p in paths if (ROOT / p).exists()]


def _matching_files(terms: tuple[str, ...], roots: tuple[str, ...], *, docs: bool) -> list[str]:
    """Search only named owner roots; pathlib preserves Chinese Windows paths."""
    found = []
    needles = tuple(term.casefold() for term in terms if term)
    for root in _relative_existing(roots):
        path = ROOT / root
        candidates = path.rglob("*") if path.is_dir() else (path,)
        for candidate in candidates:
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(ROOT).as_posix()
            if docs and (candidate.suffix.lower() not in {".md", ".json"} or relative.startswith("00-GOVERNANCE/evidence/")):
                continue
            if not docs and candidate.suffix.lower() not in {".py", ".dart", ".md", ".json", ".yaml", ".yml"}:
                continue
            name = relative.casefold()
            if any(term in name for term in needles):
                found.append(relative)
                continue
            try:
                contents = candidate.read_text(encoding="utf-8", errors="replace").casefold()
            except OSError:
                continue
            if any(term in contents for term in needles):
                found.append(relative)
    return sorted(set(found))


def _rank(path: str, terms: tuple[str, ...]) -> tuple[int, int, str]:
    name = Path(path).name.casefold()
    folded = path.casefold()
    needles = tuple(term.casefold() for term in terms if term)
    tier = 0 if any(term in name for term in needles) else 1 if any(term in folded for term in needles) else 2
    return (tier, path.count("/"), path)


def _owner_row(concern: str) -> list[str] | None:
    index = ROOT / "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md"
    if not index.is_file():
        return None
    prefix = f"| {concern} |"
    for line in index.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return [part.strip() for part in line.strip().strip("|").split("|")]
    return None


def _linked_context(rule_paths: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Follow one hop from the exact capability rules to named local inputs."""
    found = set()
    missing = set()
    for rule in rule_paths:
        rule_path = ROOT / rule
        if not rule_path.is_file():
            continue
        contents = rule_path.read_text(encoding="utf-8", errors="replace")
        for match in _LOCAL_REFERENCE.finditer(contents):
            raw = (match.group(1) or match.group(2)).replace("\\", "/")
            if any(marker in raw for marker in ("<", ">", "*", "{", "}")):
                continue
            candidate = ROOT / raw
            if not candidate.is_file():
                candidate = rule_path.parent / raw
            if candidate.is_file():
                try:
                    found.add(candidate.resolve().relative_to(ROOT.resolve()).as_posix())
                except ValueError:
                    continue
            elif raw.startswith(("00-GOVERNANCE/", "contracts/", "intelligence_library/")):
                missing.add(raw)
    return sorted(found), sorted(missing)


def _historical_git_provenance(paths: list[str]) -> list[dict[str, str]]:
    result = []
    for path in paths:
        log = subprocess.run(
            ["git", "log", "--all", "--diff-filter=A", "--format=%H", "--", path],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if log.returncode != 0:
            continue
        commit = next((line for line in log.stdout.splitlines() if line), "")
        if commit:
            result.append({"path": path, "introduced_at": commit, "status": "HISTORICAL_ONLY"})
    return result


def _pinned_historical_blobs(rule_paths: tuple[str, ...]) -> list[dict[str, str]]:
    found = []
    seen = set()
    for rule in rule_paths:
        path = ROOT / rule
        if not path.is_file():
            continue
        for commit, blob_path in _GIT_BLOB_REFERENCE.findall(path.read_text(encoding="utf-8", errors="replace")):
            if (commit, blob_path) in seen:
                continue
            seen.add((commit, blob_path))
            check = subprocess.run(
                ["git", "cat-file", "-e", f"{commit}:{blob_path}"],
                cwd=ROOT, capture_output=True,
            )
            found.append({
                "commit": commit,
                "path": blob_path,
                "status": "HISTORICAL_ONLY" if check.returncode == 0 else "BROKEN_HISTORICAL_REFERENCE",
            })
    return found


def locate(family: str, query: str, limit: int) -> dict:
    item = FAMILIES[family]
    terms = QUERY_EQUIVALENTS.get(query.casefold(), (query,)) if query else item["terms"]
    rules = list(dict.fromkeys((*CURRENT, *item["rules"])))
    missing_rules = [p for p in rules if not (ROOT / p).is_file()]
    source_roots = _relative_existing(item["roots"])
    missing_owner_roots = [p for p in item["roots"] if p not in source_roots]
    owner_row = _owner_row(item["concern"])
    docs = _matching_files(terms, ("00-GOVERNANCE", "contracts"), docs=True)
    research = _matching_files(terms, ("intelligence_library",), docs=True)
    source = _matching_files(terms, tuple(source_roots), docs=False)
    tests = _matching_files(terms, ("tests", "app/test"), docs=False)
    linked, missing_linked = _linked_context(item["rules"])
    # Exact task words outrank broad family aliases; full lists remain available
    # via --limit, while counts prevent a truncated list being mistaken as complete.
    docs.sort(key=lambda p: _rank(p, terms))
    research.sort(key=lambda p: _rank(p, terms))
    source.sort(key=lambda p: _rank(p, terms))
    tests.sort(key=lambda p: _rank(p, terms))
    return {
        "capability": family,
        "query": query,
        "search_terms": list(terms),
        "status": (
            "MISSING_REQUIRED_RULE" if missing_rules else
            "OWNER_ROUTE_UNAVAILABLE" if not source_roots or owner_row is None else
            "ROUTED_WITH_MISSING_HISTORICAL_INPUT" if missing_linked else
            "ROUTED_NOT_VERIFIED"
        ),
        "current_rules": _relative_existing(rules),
        "missing_rules": missing_rules,
        "directly_linked_context": linked,
        "missing_linked_context": missing_linked,
        "historical_git_provenance": _historical_git_provenance(missing_linked),
        "pinned_historical_blobs": _pinned_historical_blobs(item["rules"]),
        "owner_roots": source_roots,
        "source_owner_index_row": owner_row,
        "missing_owner_roots": missing_owner_roots,
        "related_document_candidates": docs[:limit],
        "related_document_count": len(docs),
        "historical_research_candidates": research[:limit],
        "historical_research_count": len(research),
        "historical_research_search_state": "MATCHED" if research else "NO_MATCH_FOR_THESE_TERMS",
        "source_candidates": source[:limit],
        "source_count": len(source),
        "test_candidates": tests[:limit],
        "test_count": len(tests),
        "next_step": "Read the active owner row and exact matching files; classify historical research as input, never implementation proof.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capability", choices=sorted(FAMILIES))
    parser.add_argument("--path", help="Existing source path; route by longest owner root")
    parser.add_argument("--query", default="", help="Specific task word, e.g. podcast or 播客")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    family = args.capability
    if args.path:
        target = args.path.replace("\\", "/").lstrip("./")
        if not (ROOT / target).exists():
            parser.error("path does not exist in the current tree; use --capability to inspect a historical or missing path")
        matches = sorted(
            ((len(root), key) for key, item in FAMILIES.items() for root in item["roots"]
             if target == root or target.startswith(root.rstrip("/") + "/")),
            reverse=True,
        )
        if not matches:
            parser.error("path has no owner route; inspect Source Owner Index and name --capability explicitly")
        best_length = matches[0][0]
        best_families = {key for length, key in matches if length == best_length}
        if len(best_families) > 1 and not family:
            parser.error(
                "path spans multiple owner families: " + ", ".join(sorted(best_families))
                + "; name --capability and verify the active owner row"
            )
        routed = family if family in best_families else matches[0][1]
        if family and family != routed:
            parser.error(f"path routes to {routed}, not {family}; resolve the owner before editing")
        family = routed
    if not family:
        parser.error("provide --capability or --path; never infer ownership from a keyword alone")
    result = locate(family, args.query.strip(), args.limit)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["missing_rules"] or not result["owner_roots"] or result["source_owner_index_row"] is None else 0


if __name__ == "__main__":
    raise SystemExit(main())

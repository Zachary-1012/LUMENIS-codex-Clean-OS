#!/usr/bin/env python3
"""Build a deterministic, read-only inventory of Heritage source mirrors."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


TEXT_EXTENSIONS = {
    ".md", ".txt", ".rst", ".adoc", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".csv", ".tsv", ".sql", ".py", ".js",
    ".jsx", ".ts", ".tsx", ".html", ".css", ".scss", ".sh", ".ps1",
    ".bat", ".xml", ".graphql",
}

KNOWLEDGE_DIRS = {
    "docs", "doc", "research", "learning", "intelligence_library", "audit",
    "audits", "contracts", "contract", "evidence", "governance", "adr",
    "adrs", "tests", "test", "agent", "agents", "ai", "schemas", "schema",
    "taxonomy", "design", "ux", "heritage_intelligence",
}

SKIP_PARTS = {
    "node_modules", ".venv", "venv", "dist", "build", "__pycache__",
    ".git", "vendor", "site-packages",
}

DOMAIN_RULES = {
    "korean": [
        "korean", "k-drama", "kdrama", "fansub", "subtitle", "translation",
        "localization", "i18n", "ko-kr", "zh-ko-en", "韩语", "韩剧", "字幕",
        "汉化", "本地化", "문화", "한국어",
    ],
    "xiaohongshu": ["xiaohongshu", "xhs", "小红书", "rednote"],
    "platform": [
        "platform", "adapter", "douyin", "tiktok", "weibo", "bilibili",
        "kuaishou", "zhihu", "podcast", "小红书", "抖音", "微博", "快手",
        "知乎", "平台", "采集", "collector", "auth", "cdp", "playwright",
    ],
    "data_metrics": [
        "metric", "truth_table", "truth-table", "dashboard", "trend", "ranking",
        "drill", "field_contract", "dfs", "attribution", "emv", "visualization",
        "data_presentation", "数据", "指标", "表格", "趋势", "归因", "可视化",
    ],
    "kos_kol_koc": ["kos", "kol", "koc", "ugc", "creator", "influencer", "达人"],
    "podcast": ["podcast", "播客"],
    "ui_ux": [
        "ui", "ux", "responsive", "mobile", "tablet", "drawer", "motion",
        "interaction", "design", "frontend", "template", "static", "页面",
        "交互", "动效", "响应式", "设计",
    ],
    "ai_agent": [
        "ai", "agent", "llm", "ollama", "zhipu", "glm", "memory", "learning",
        "evaluation", "prompt", "permission", "firewall", "effect_fence",
        "gateway", "智能", "模型", "代理", "学习", "评测",
    ],
    "evidence_contract": [
        "evidence", "contract", "schema", "taxonomy", "state_machine",
        "permission_matrix", "truth", "证据", "契约", "口径", "分类法",
    ],
    "engineering": [
        "engineering", "runtime", "security", "release", "deployment", "audit",
        "verify", "verification", "ci", "migration", "governance", "工程",
        "运行", "安全", "发布", "部署", "审计", "迁移", "治理",
    ],
    "decision_memory": ["decision", "adr", "correction", "decision_memory", "决策", "纠偏"],
    "regression_memory": [
        "regression", "incident", "bug", "failure", "test", "fix", "回归",
        "故障", "修复", "测试",
    ],
    "domain_methodology": [
        "campaign", "public_opinion", "content", "consumer", "event", "case",
        "risk", "report", "commercial", "brand", "operations", "舆情", "内容",
        "消费者", "事件", "案例", "风险", "报告", "商业", "品牌", "运营",
    ],
}


def run_git(repo: Path, *args: str, text: bool = True) -> str | bytes:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    proc = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True,
        text=text, encoding="utf-8" if text else None, errors="replace" if text else None,
        env=env,
    )
    return proc.stdout


def refs(repo: Path) -> list[dict[str, str]]:
    raw = run_git(
        repo, "for-each-ref",
        "--format=%(refname:short)%00%(objectname)%00%(committerdate:iso8601)%00%(subject)",
        "refs/heads",
    )
    rows = []
    for line in str(raw).splitlines():
        name, sha, date, subject = (line.split("\0", 3) + [""] * 4)[:4]
        rows.append({"branch": name, "commit": sha, "commit_date": date, "subject": subject})
    return rows


def tree(repo: Path, commit: str) -> list[dict[str, object]]:
    raw = run_git(repo, "ls-tree", "-r", "-l", "-z", commit, text=False)
    rows = []
    for record in bytes(raw).split(b"\0"):
        if not record:
            continue
        meta, path_raw = record.split(b"\t", 1)
        mode, kind, blob, size = meta.decode("ascii", "replace").split()
        rows.append({
            "mode": mode,
            "kind": kind,
            "blob": blob,
            "size": None if size == "-" else int(size),
            "path": path_raw.decode("utf-8", "replace"),
        })
    return rows


def changed_paths(repo: Path, base: str, tip: str) -> set[str]:
    try:
        merge_base = str(run_git(repo, "merge-base", base, tip)).strip()
        if not merge_base:
            return set()
        raw = run_git(repo, "diff", "--name-only", "-z", merge_base, tip, text=False)
        return {p.decode("utf-8", "replace") for p in bytes(raw).split(b"\0") if p}
    except subprocess.CalledProcessError:
        return set()


def normalized_path(path: str) -> str:
    return path.replace("\\", "/").casefold()


def domains_for(path: str, branches: list[str], branch_changed: bool) -> list[str]:
    p = normalized_path(path)
    haystack = p
    if branch_changed:
        haystack += " " + " ".join(branches).casefold()
    tokens = set(re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+|[\uac00-\ud7af]+", haystack))

    def matches(term: str) -> bool:
        folded = term.casefold()
        if folded.isascii() and len(folded) <= 4 and folded.replace("-", "").isalnum():
            return folded in tokens
        return folded in haystack

    domains = []
    for domain, terms in DOMAIN_RULES.items():
        if any(matches(term) for term in terms):
            domains.append(domain)
    return domains


def is_candidate(path: str, domains: list[str], branch_changed: bool) -> bool:
    p = Path(path)
    parts = {part.casefold() for part in p.parts}
    if parts & SKIP_PARTS:
        return False
    in_knowledge_dir = bool(parts & KNOWLEDGE_DIRS)
    return bool(domains) or in_knowledge_dir or (branch_changed and p.suffix.casefold() in TEXT_EXTENSIONS)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mirror-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    repo_names = ["clean", "zbrand", "osai", "ggi", "command"]
    default_branch = {name: "main" for name in repo_names}
    repo_summaries = []
    branch_rows: list[dict[str, object]] = []
    inventory_rows: list[dict[str, object]] = []
    observations_by_key: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    tip_meta_by_repo: dict[str, dict[str, dict[str, object]]] = {}

    for repo_name in repo_names:
        repo = args.mirror_root / f"{repo_name}.git"
        repo_refs = refs(repo)
        refs_by_tip: dict[str, list[str]] = defaultdict(list)
        for row in repo_refs:
            refs_by_tip[row["commit"]].append(row["branch"])
        default_ref = default_branch[repo_name]
        default_sha = next((r["commit"] for r in repo_refs if r["branch"] == default_ref), "")

        tips: dict[str, dict[str, object]] = {}
        all_branch_observations = 0
        for tip, branch_aliases in sorted(refs_by_tip.items()):
            entries = tree(repo, tip)
            changed = changed_paths(repo, default_sha, tip) if default_sha and tip != default_sha else set()
            tips[tip] = {"branches": sorted(branch_aliases), "entries": entries, "changed": changed}
            all_branch_observations += len(entries) * len(branch_aliases)
            for entry in entries:
                key = (str(entry["path"]), str(entry["blob"]), tip)
                observations_by_key[(repo_name, *key[:2])].update(branch_aliases)

        tip_meta_by_repo[repo_name] = tips
        unique_paths = {str(e["path"]) for t in tips.values() for e in t["entries"]}
        unique_blobs = {str(e["blob"]) for t in tips.values() for e in t["entries"]}
        unique_versions = {(str(e["path"]), str(e["blob"])) for t in tips.values() for e in t["entries"]}
        unique_tip_observations = sum(len(t["entries"]) for t in tips.values())
        repo_summaries.append({
            "repository": repo_name,
            "branches": len(repo_refs),
            "unique_tip_commits": len(tips),
            "branch_file_observations": all_branch_observations,
            "unique_tip_file_observations": unique_tip_observations,
            "unique_paths": len(unique_paths),
            "unique_path_blob_versions": len(unique_versions),
            "unique_blobs": len(unique_blobs),
            "default_branch": default_ref,
            "default_commit": default_sha,
        })
        for row in repo_refs:
            tip_info = tips[row["commit"]]
            branch_rows.append({
                "repository": repo_name,
                **row,
                "tip_alias_count": len(tip_info["branches"]),
                "tip_file_count": len(tip_info["entries"]),
                "changed_from_default_merge_base": len(tip_info["changed"]),
            })

    clean_tips = tip_meta_by_repo["clean"]
    clean_paths = {str(e["path"]): str(e["blob"]) for t in clean_tips.values() for e in t["entries"]}
    clean_blobs = {str(e["blob"]) for t in clean_tips.values() for e in t["entries"]}

    seen_versions: set[tuple[str, str, str]] = set()
    for repo_name, tips in tip_meta_by_repo.items():
        for tip, info in tips.items():
            branches = list(info["branches"])
            changed = set(info["changed"])
            for entry in info["entries"]:
                path = str(entry["path"])
                blob = str(entry["blob"])
                version_key = (repo_name, path, blob)
                if version_key in seen_versions:
                    continue
                seen_versions.add(version_key)
                all_branches = sorted(observations_by_key[(repo_name, path, blob)])
                branch_changed = path in changed
                domains = domains_for(path, all_branches, branch_changed)
                if not is_candidate(path, domains, branch_changed):
                    continue
                if blob in clean_blobs:
                    current_equivalent = "EXACT_BLOB"
                elif path in clean_paths:
                    current_equivalent = "SAME_PATH_DIFFERENT_BLOB"
                else:
                    current_equivalent = "NO_EXACT_CURRENT_EQUIVALENT"
                inventory_rows.append({
                    "repository": repo_name,
                    "source_branches": ";".join(all_branches),
                    "source_tip": tip,
                    "source_path": path,
                    "source_blob": blob,
                    "size_bytes": entry["size"],
                    "extension": Path(path).suffix.casefold(),
                    "branch_changed": branch_changed,
                    "domains": ";".join(domains),
                    "current_equivalent": current_equivalent,
                    "inventory_status": "INDEXED",
                })

    blob_groups: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(inventory_rows):
        blob_groups[str(row["source_blob"])].append(idx)
    duplicate_rows = []
    exact_duplicate_observations = 0
    for blob, indices in blob_groups.items():
        if len(indices) < 2:
            continue
        exact_duplicate_observations += len(indices) - 1
        members = [inventory_rows[i] for i in indices]
        duplicate_rows.append({
            "source_blob": blob,
            "member_count": len(members),
            "repositories": ";".join(sorted({str(m["repository"]) for m in members})),
            "paths": ";".join(sorted({str(m["source_path"]) for m in members})),
        })

    domain_counts: Counter[str] = Counter()
    for row in inventory_rows:
        for domain in str(row["domains"]).split(";"):
            if domain:
                domain_counts[domain] += 1

    summary = {
        "repositories_scanned": len(repo_names),
        "branches_scanned": sum(int(r["branches"]) for r in repo_summaries),
        "unique_tip_commits": sum(int(r["unique_tip_commits"]) for r in repo_summaries),
        "branch_file_observations": sum(int(r["branch_file_observations"]) for r in repo_summaries),
        "unique_tip_file_observations": sum(int(r["unique_tip_file_observations"]) for r in repo_summaries),
        "candidate_path_blob_versions": len(inventory_rows),
        "candidate_unique_blobs": len(blob_groups),
        "exact_duplicate_groups": len(duplicate_rows),
        "exact_duplicate_path_blob_observations": exact_duplicate_observations,
        "current_exact_blob_matches": sum(r["current_equivalent"] == "EXACT_BLOB" for r in inventory_rows),
        "current_same_path_different_blob": sum(r["current_equivalent"] == "SAME_PATH_DIFFERENT_BLOB" for r in inventory_rows),
        "no_exact_current_equivalent": sum(r["current_equivalent"] == "NO_EXACT_CURRENT_EQUIVALENT" for r in inventory_rows),
        "domain_candidate_counts": dict(sorted(domain_counts.items())),
        "repositories": repo_summaries,
    }

    write_csv(
        args.output / "branch_inventory.csv",
        ["repository", "branch", "commit", "commit_date", "subject", "tip_alias_count", "tip_file_count", "changed_from_default_merge_base"],
        branch_rows,
    )
    write_csv(
        args.output / "asset_file_index.csv",
        ["repository", "source_branches", "source_tip", "source_path", "source_blob", "size_bytes", "extension", "branch_changed", "domains", "current_equivalent", "inventory_status"],
        sorted(inventory_rows, key=lambda r: (str(r["repository"]), str(r["source_path"]), str(r["source_blob"]))),
    )
    write_csv(
        args.output / "exact_duplicate_groups.csv",
        ["source_blob", "member_count", "repositories", "paths"],
        sorted(duplicate_rows, key=lambda r: (-int(r["member_count"]), str(r["source_blob"]))),
    )
    (args.output / "inventory_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

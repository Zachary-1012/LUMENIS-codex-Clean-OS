#!/usr/bin/env python3
"""Index knowledge-related file versions across every reachable Git commit."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

from heritage_inventory import domains_for, is_candidate


def git(repo: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    ).stdout


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def commit_branches(repo: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    refs = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
    for branch in refs:
        for commit in git(repo, "rev-list", branch).splitlines():
            result[commit].add(branch)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mirror-root", required=True, type=Path)
    parser.add_argument("--tip-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    with args.tip_inventory.open("r", encoding="utf-8-sig", newline="") as fh:
        tip_rows = list(csv.DictReader(fh))
    tip_versions = {(r["repository"], r["source_path"], r["source_blob"]) for r in tip_rows}
    clean_paths: dict[str, str] = {}
    clean_blobs: set[str] = set()
    for row in tip_rows:
        if row["repository"] == "clean":
            clean_paths[row["source_path"]] = row["source_blob"]
            clean_blobs.add(row["source_blob"])

    repo_names = ["clean", "zbrand", "osai", "ggi", "command"]
    commit_rows: list[dict[str, object]] = []
    versions: dict[tuple[str, str, str], dict[str, object]] = {}
    repository_summary = []

    for repo_name in repo_names:
        repo = args.mirror_root / f"{repo_name}.git"
        default_branch = "main"
        contains = commit_branches(repo)
        raw = git(
            repo, "-c", "core.quotepath=false", "log", "--all", "--reverse", "--topo-order", "--no-renames", "--raw",
            "--no-abbrev", "--date=iso-strict", "--format=@@@%H%x00%cI%x00%P%x00%s",
        )
        current: dict[str, str] | None = None
        repo_commits: set[str] = set()
        raw_change_observations = 0
        for line in raw.splitlines():
            if line.startswith("@@@"):
                parts = line[3:].split("\0", 3)
                if len(parts) != 4:
                    current = None
                    continue
                sha, date, parents, subject = parts
                current = {"commit": sha, "date": date, "parents": parents, "subject": subject}
                if sha not in repo_commits:
                    repo_commits.add(sha)
                    commit_rows.append({
                        "repository": repo_name,
                        "commit": sha,
                        "commit_date": date,
                        "parents": parents,
                        "subject": subject,
                        "reachable_from_branches": ";".join(sorted(contains.get(sha, set()))),
                    })
                continue
            if current is None or not line.startswith(":") or "\t" not in line:
                continue
            meta, path = line.split("\t", 1)
            fields = meta.split()
            if len(fields) < 5:
                continue
            new_blob = fields[3]
            status = fields[4]
            if status.startswith("D") or set(new_blob) == {"0"}:
                continue
            raw_change_observations += 1
            branches = sorted(contains.get(current["commit"], set()))
            branch_specific = default_branch not in branches
            domains = domains_for(path, branches, branch_specific)
            if not is_candidate(path, domains, branch_specific):
                continue
            key = (repo_name, path, new_blob)
            item = versions.get(key)
            if item is None:
                if new_blob in clean_blobs:
                    equivalent = "EXACT_BLOB"
                elif path in clean_paths:
                    equivalent = "SAME_PATH_DIFFERENT_BLOB"
                else:
                    equivalent = "NO_EXACT_CURRENT_EQUIVALENT"
                item = {
                    "repository": repo_name,
                    "source_path": path,
                    "source_blob": new_blob,
                    "first_seen_commit": current["commit"],
                    "first_seen_date": current["date"],
                    "last_seen_commit": current["commit"],
                    "last_seen_date": current["date"],
                    "observed_commits": set(),
                    "reachable_from_branches": set(),
                    "domains": set(domains),
                    "current_equivalent": equivalent,
                    "inventory_status": "INDEXED",
                    "present_at_scanned_tip": key in tip_versions,
                }
                versions[key] = item
            item["last_seen_commit"] = current["commit"]
            item["last_seen_date"] = current["date"]
            item["observed_commits"].add(current["commit"])
            item["reachable_from_branches"].update(branches)
            item["domains"].update(domains)

        repository_summary.append({
            "repository": repo_name,
            "reachable_commits": len(repo_commits),
            "raw_change_observations": raw_change_observations,
            "historical_candidate_versions": sum(1 for key in versions if key[0] == repo_name),
            "historical_only_candidate_versions": sum(1 for key, value in versions.items() if key[0] == repo_name and not value["present_at_scanned_tip"]),
        })

    version_rows = []
    for item in versions.values():
        version_rows.append({
            **item,
            "observed_commits": ";".join(sorted(item["observed_commits"])),
            "reachable_from_branches": ";".join(sorted(item["reachable_from_branches"])),
            "domains": ";".join(sorted(item["domains"])),
        })

    summary = {
        "repositories_scanned": len(repo_names),
        "reachable_commits_scanned": len(commit_rows),
        "historical_candidate_path_blob_versions": len(version_rows),
        "historical_only_candidate_versions": sum(not bool(r["present_at_scanned_tip"]) for r in version_rows),
        "current_exact_blob_matches": sum(r["current_equivalent"] == "EXACT_BLOB" for r in version_rows),
        "current_same_path_different_blob": sum(r["current_equivalent"] == "SAME_PATH_DIFFERENT_BLOB" for r in version_rows),
        "no_exact_current_equivalent": sum(r["current_equivalent"] == "NO_EXACT_CURRENT_EQUIVALENT" for r in version_rows),
        "repositories": repository_summary,
    }
    write_csv(
        args.output / "commit_inventory.csv",
        ["repository", "commit", "commit_date", "parents", "subject", "reachable_from_branches"],
        commit_rows,
    )
    write_csv(
        args.output / "historical_asset_versions.csv",
        ["repository", "source_path", "source_blob", "first_seen_commit", "first_seen_date", "last_seen_commit", "last_seen_date", "observed_commits", "reachable_from_branches", "domains", "current_equivalent", "inventory_status", "present_at_scanned_tip"],
        sorted(version_rows, key=lambda r: (str(r["repository"]), str(r["source_path"]), str(r["source_blob"]))),
    )
    (args.output / "history_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

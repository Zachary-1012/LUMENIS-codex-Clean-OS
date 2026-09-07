#!/usr/bin/env python3
"""Branch convergence audit - batch data collection (read-only)."""
import subprocess
import json
import os
from datetime import datetime

REPO = r"D:\Taikoo-monitor-new"

def run_git(args, check=True):
    """Run git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if check and result.returncode != 0:
        return None
    return result.stdout.strip()

def get_all_branches():
    """Get all local and remote branches, normalized."""
    branches = set()
    # Local branches
    out = run_git(["branch", "--format=%(refname:short)"])
    if out:
        for line in out.splitlines():
            line = line.strip().lstrip("* ").strip()
            if line and line != "main":
                branches.add(line)
    # Remote branches
    out = run_git(["branch", "-r", "--format=%(refname:short)"])
    if out:
        for line in out.splitlines():
            line = line.strip()
            if line and not line.endswith("HEAD") and line != "origin/main":
                branches.add(line)
    return sorted(branches)

def is_ancestor(branch):
    """Check if branch is fully contained in main."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", branch, "main"],
        cwd=REPO, capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0

def get_ahead_count(branch):
    """Number of commits in branch not in main."""
    out = run_git(["rev-list", "--count", f"main..{branch}"], check=False)
    try:
        return int(out) if out else 0
    except:
        return -1

def get_behind_count(branch):
    """Number of commits in main not in branch."""
    out = run_git(["rev-list", "--count", f"{branch}..main"], check=False)
    try:
        return int(out) if out else 0
    except:
        return -1

def get_last_commit(branch):
    """Last commit date and message."""
    out = run_git(["log", "-1", "--format=%ci|%s", branch], check=False)
    if out and "|" in out:
        parts = out.split("|", 1)
        return parts[0].strip(), parts[1].strip()[:80]
    return "unknown", "unknown"

def get_unique_files(branch):
    """Files changed in branch but not in main (diff main...branch)."""
    out = run_git(["diff", "--name-only", f"main...{branch}"], check=False)
    if out:
        return [l.strip() for l in out.splitlines() if l.strip()]
    return []

def get_merge_base(branch):
    out = run_git(["merge-base", "main", branch], check=False)
    return out[:12] if out else "unknown"

def main():
    branches = get_all_branches()
    print(f"Total branches to audit: {len(branches)}")
    
    results = []
    for i, br in enumerate(branches):
        print(f"[{i+1}/{len(branches)}] {br}")
        ancestor = is_ancestor(br)
        ahead = get_ahead_count(br)
        behind = get_behind_count(br)
        last_date, last_msg = get_last_commit(br)
        files = get_unique_files(br)
        mb = get_merge_base(br)
        
        results.append({
            "branch": br,
            "is_ancestor_of_main": ancestor,
            "ahead_count": ahead,
            "behind_count": behind,
            "last_commit_date": last_date,
            "last_commit_msg": last_msg,
            "merge_base": mb,
            "unique_file_count": len(files),
            "unique_files": files[:50],  # cap for preview
        })
    
    out_path = os.path.join(REPO, "audit", "convergence", "raw_branch_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nDone. Data written to {out_path}")
    print(f"Ancestors (A candidates): {sum(1 for r in results if r['is_ancestor_of_main'])}")
    print(f"Non-ancestors: {sum(1 for r in results if not r['is_ancestor_of_main'])}")

if __name__ == "__main__":
    main()

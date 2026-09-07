#!/usr/bin/env python3
"""Deep analysis of non-ancestor branches."""
import subprocess
import json
import os

REPO = r"D:\Taikoo-monitor-new"

NON_ANCESTORS = [
    "feat/lumenis-p0-p1-source-convergence",
    "feat/zbc-full-upgrade-v1",
    "origin/feat/lumenis-product-convergence",
    "origin/feat/lumenis-product-convergence-docs-final3",
    "origin/research/kdrama-fansub-study-20260903-final",
]

def run_git(args, check=True):
    result = subprocess.run(
        ["git"] + args, cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    if check and result.returncode != 0:
        return None
    return result.stdout.strip()

def get_unique_commits(branch):
    out = run_git(["log", "--oneline", f"main..{branch}"])
    if not out:
        return []
    commits = []
    for line in out.splitlines():
        parts = line.strip().split(" ", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0], "msg": parts[1][:120]})
    return commits

def get_diff_stat(branch):
    out = run_git(["diff", "--stat", f"main...{branch}"])
    return out if out else "no diff"

def get_full_file_list(branch):
    out = run_git(["diff", "--name-only", f"main...{branch}"])
    if not out:
        return []
    return [l.strip() for l in out.splitlines() if l.strip()]

def check_dangerous_patterns(branch):
    """Check for dangerous operations in diff."""
    dangers = []
    # Get the full diff for key files
    out = run_git(["diff", f"main...{branch}", "--", "*.py", "*.sql", "*.md"])
    if out:
        lines = out.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("+") and not line.startswith("+++"):
                lower = line.lower()
                if any(kw in lower for kw in ["drop table", "delete from", "truncate", "remove table"]):
                    dangers.append(f"DB destructive: {line.strip()[:120]}")
                if any(kw in lower for kw in ["api_key", "secret_key", "password", "token"]) and "=" in lower:
                    if "os.getenv" not in lower and "env" not in lower:
                        dangers.append(f"Potential hardcoded secret: {line.strip()[:120]}")
                if "subject_words" in lower and ("= []" in lower or "= []" in lower):
                    dangers.append(f"Subject words modification: {line.strip()[:120]}")
    return dangers[:20]

def get_commit_detail(branch, commit_hash):
    out = run_git(["show", "--stat", "--format=%H%n%an%n%ai%n%s", commit_hash])
    return out if out else ""

def main():
    results = {}
    for br in NON_ANCESTORS:
        print(f"\n{'='*60}")
        print(f"Analyzing: {br}")
        print(f"{'='*60}")
        
        commits = get_unique_commits(br)
        print(f"  Unique commits: {len(commits)}")
        for c in commits:
            print(f"    {c['hash']} {c['msg']}")
        
        files = get_full_file_list(br)
        print(f"  Changed files: {len(files)}")
        
        diff_stat = get_diff_stat(br)
        dangers = check_dangerous_patterns(br)
        
        results[br] = {
            "unique_commits": commits,
            "changed_files": files,
            "diff_stat": diff_stat,
            "dangers": dangers,
        }
    
    out_path = os.path.join(REPO, "audit", "convergence", "deep_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDeep analysis written to {out_path}")

if __name__ == "__main__":
    main()

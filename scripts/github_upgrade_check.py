#!/usr/bin/env python3
"""Check GitHub for a newer Z-Brand-Core revision and emit a Doubao upgrade task.

This script is intentionally local-only: it does not modify source code, credentials,
Cookies, databases or platform accounts. It only compares the remote Git HEAD with
local Git HEAD and writes a deterministic task file for the local AI/dev workflow.

Usage:
    python scripts/github_upgrade_check.py
    python scripts/github_upgrade_check.py --repo-dir .

The local machine should run this after each local development task and periodically
via Windows Task Scheduler. Doubao can read the generated task file, inspect the GitHub
revision, audit the local source, run tests, and only then apply compatible changes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = "Zachary-1012/Z-Brand-Core"
DEFAULT_BRANCH = "main"
TASK_FILE = Path(".runtime") / "github_upgrade_task.md"
STATE_FILE = Path(".runtime") / "github_upgrade_state.json"


def run_git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def remote_head() -> str:
    url = f"https://api.github.com/repos/{REPO}/commits/{DEFAULT_BRANCH}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Z-Brand-Core-upgrade-check"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.load(response)
    return payload["sha"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", default=".")
    args = parser.parse_args()

    repo_dir = Path(args.repo_dir).resolve()
    local_head = run_git(repo_dir, "rev-parse", "HEAD")
    remote = remote_head()
    now = datetime.now(timezone.utc).isoformat()

    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if local_head == remote:
        TASK_FILE.write_text(
            "# GitHub 升级检查\n\n"
            f"时间: {now}\n"
            f"仓库: {REPO}\n"
            f"本地 HEAD: `{local_head}`\n"
            f"GitHub main: `{remote}`\n\n"
            "状态：已同步。无需自动修改源码。继续执行本地健康检查即可。\n",
            encoding="utf-8",
        )
        status = "synced"
    else:
        TASK_FILE.write_text(
            "# GitHub 升级任务（供豆包/本地开发代理执行）\n\n"
            f"时间: {now}\n"
            f"仓库: {REPO}\n"
            f"本地 HEAD: `{local_head}`\n"
            f"GitHub main: `{remote}`\n\n"
            "## 执行顺序\n"
            "1. 先读取 GitHub 最新提交和变更文件。\n"
            "2. 先审计、再修改；禁止直接覆盖本地生产源码。\n"
            "3. 保留现有数据库、主体过滤、风险、事件、报告等核心逻辑。\n"
            "4. 优先采用向后兼容的小补丁。\n"
            "5. 小红书为主平台，抖音为第二重点；其他五个平台只维护 Adapter 插槽。\n"
            "6. 禁止复制 MediaCrawler 的受限许可证代码；仅可独立实现兼容接口和设计思想。\n"
            "7. 禁止绕过验证码、安全验证、IP 风控或平台访问控制。\n"
            "8. 修改后运行现有测试、语法检查和关键回归测试。\n"
            "9. 测试通过后才允许提交 Git。\n"
            "10. 将变更摘要、测试结果和回滚方式写入升级日志。\n\n"
            "## 绝对保护项\n"
            "- `SUBJECT_WORDS`\n"
            "- `SUBJECT_EXCLUDE_WORDS`\n"
            "- `subject_hit()`\n"
            "- `_subject_sql_and_values()`\n"
            "- `aggregate_events()` 主体过滤\n"
            "- `build_daily_report()` 主体过滤\n"
            "- `publish_datetime` / `captured_at` 时间口径\n"
            "- 生产 SQLite 数据及历史数据\n\n"
            "## 完成条件\n"
            "本次任务只有在代码、测试、数据安全和 Git 状态全部正常时才标记完成。\n",
            encoding="utf-8",
        )
        status = "upgrade_available"

    STATE_FILE.write_text(
        json.dumps(
            {"checked_at": now, "local_head": local_head, "remote_head": remote, "status": status},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"status={status} local={local_head} remote={remote}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

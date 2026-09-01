# -*- coding: utf-8 -*-
"""Z-Brand Core 每日定时安全同步（计划任务 08:00 / 18:00 / 00:00 调用，用户说“同步”也可手动跑）。

流程（全程不交互、不抛异常、不 force push、不提交任何敏感凭证）：
  1) 非破坏健康检查：关键模块可导入、monitor.db 只读 quick_check。
  2) 走版本中心安全闸：仅源码/模板/配置/迁移/版本与日志入库；Cookie/Key/.env/*.db/Profile 一律禁入。
  3) 有合规改动才成提交（无改动不制造空提交）。
  4) fetch 远程；远程领先则 rebase 整合（保留全部历史，冲突即 abort 并报告，绝不覆盖远程）。
  5) push origin main：直连优先、有限退避、必要时回退本机代理；失败保留本地提交并如实报告。
用法：.venv\\Scripts\\python.exe scripts\\daily_git_sync.py
"""
from __future__ import annotations

import io
import os
import sqlite3
import sys
import traceback
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

LOG = os.path.join(ROOT, "logs", "git_sync.log")
DB = os.path.join(ROOT, "data", "monitor.db")


def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def health_check() -> tuple[bool, str]:
    """只读、非破坏：关键模块可导入 + 生产库只读 quick_check（绝不写库）。"""
    try:
        import subject_rules  # noqa: F401  主体红线模块
        from v4_upgrade.version_center.git_manager import GitVersionManager  # noqa: F401
        if os.path.exists(DB):
            uri = "file:" + DB.replace("\\", "/") + "?mode=ro"
            con = sqlite3.connect(uri, uri=True)
            row = con.execute("PRAGMA quick_check").fetchone()
            con.close()
            if not row or str(row[0]).lower() != "ok":
                return False, f"DB quick_check={row}"
        return True, "modules importable; db read-only quick_check ok"
    except Exception as e:  # noqa: BLE001
        return False, f"health check error: {type(e).__name__}: {e}"


def main() -> int:
    log("=" * 20 + " daily git sync start " + "=" * 20)
    ok_health, health_msg = health_check()
    log(f"[1/5] health: {ok_health} :: {health_msg}")
    if not ok_health:
        log("ABORT: 健康检查未通过，跳过本次自动同步（不做任何写/推送操作）。")
        return 2

    try:
        from v4_upgrade.version_center.git_manager import GitVersionManager
        gm = GitVersionManager(ROOT)

        # [2/5] 安全闸 + 本地成版本（不推送）
        ts = datetime.now().strftime("%H:%M")
        _curv = gm.current_version() or ""
        _curv = _curv if str(_curv).startswith("v") else "v" + str(_curv)
        assert _curv.startswith("v") and len(_curv) >= 2, f"版本号格式异常: {_curv!r}"
        saved = gm.save_version(f"{_curv} 定时同步版本（{ts}）", do_push=False, author="daily-sync")
        if not saved.get("ok"):
            log(f"[2/5] 安全闸拦截/提交失败：{saved.get('error')} blocked={saved.get('blocked')}")
            # 安全闸拦截属于硬失败，终止（可能有敏感文件误入），等待人工
            return 3
        committed = saved.get("committed", False)
        sha = saved.get("sha", "")
        files = saved.get("committed_files", [])
        if committed:
            log(f"[2/5] 本地成版本 sha={sha} files={len(files)}")
            for f in files[:40]:
                log("        + " + f)
        else:
            log(f"[2/5] 无合规改动，不制造空提交（{saved.get('message')}）")

        # [3/5] fetch + rebase 整合远程
        fetch = gm._run_remote(["fetch", "origin", "main"], timeout=60)
        if not fetch["ok"]:
            log(f"[3/5] fetch 失败（保留本地提交，等待下一时点重试）：{fetch.get('err') or fetch.get('out')}")
            return 4
        behind_ahead = gm._run(["rev-list", "--left-right", "--count", "HEAD...origin/main"])
        log(f"[3/5] fetch ok; 本地/远程 领先计数={behind_ahead.get('out','?')}")
        cnt = (behind_ahead.get("out") or "0 0").split()
        remote_ahead = int(cnt[1]) if len(cnt) == 2 and cnt[1].isdigit() else 0
        if remote_ahead > 0:
            rb = gm._run(["rebase", "origin/main"], timeout=90)
            if not rb["ok"]:
                gm._run(["rebase", "--abort"])
                log(f"[3/5] rebase 冲突，已 abort，保留双方历史、未推送：{rb.get('err') or rb.get('out')}")
                return 5
            log("[3/5] rebase 整合远程完成（线性历史，无 force）")
        else:
            log("[3/5] 远程无新增，无需 rebase")

        # [4/5] push（直连退避 + 代理回退）
        push = gm.push()
        if not push["ok"]:
            log(f"[4/5] push 最终失败（本地提交已保留）：{push.get('err') or push.get('out')}")
            return 6
        via = push.get("via_proxy") or push.get("via") or "direct"
        log(f"[4/5] push 成功（{via}）")

        # [5/5] 确认远程同步
        gm._run_remote(["fetch", "origin", "main"], timeout=60)
        gap = gm._run(["rev-list", "--left-right", "--count", "HEAD...origin/main"])
        log(f"[5/5] 推送后 本地/远程 计数={gap.get('out','?')}（0 0 即完全同步）")
        head = gm._run(["rev-parse", "--short", "HEAD"])
        log(f"DONE sync ok; committed={committed} sha={head.get('out','')}")
        return 0
    except Exception as e:  # noqa: BLE001
        log("FATAL 未预期异常，已捕获不抛出：" + f"{type(e).__name__}: {e}")
        log(traceback.format_exc())
        return 7


if __name__ == "__main__":
    sys.exit(main())

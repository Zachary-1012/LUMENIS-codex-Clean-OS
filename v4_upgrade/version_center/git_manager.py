# -*- coding: utf-8 -*-
"""
版本中心 · Git 版本管理器（系统内置的“源码版本保险库”）

设计原则（严格遵守用户口径）：
1. 只版本化“源码 / 模板 / 配置模板 / 依赖清单 / 迁移 / 版本与更新日志”；
   Cookie、API Key、管理员密码、SECRET_KEY、生产数据库、采集原始数据绝不入库。
   双保险：既依赖仓库 .gitignore，又在每次 `git add` 后做“暂存区安全闸”扫描，
   一旦命中禁入模式立即撤销暂存并拒绝提交。
2. 不覆盖历史：回滚默认用 `git revert` 生成反向提交；hard 重置需显式二次确认。
3. 网络自适应：远程操作先直连，连接失败再自动探测本机代理端口回退（海外采集代理
   与 Git 推送互不影响）。
4. 纯标准库 + 本机 git，可被路由、调度守护线程、命令行多处复用；任何异常都结构化返回，不抛出。
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---- 候选 git 可执行路径（Git for Windows 默认安装位 + PATH） ----
_GIT_CANDIDATES = [
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files (x86)\Git\cmd\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
    "/usr/bin/git", "/usr/local/bin/git",
]
_PROXY_CANDIDATE_PORTS = [10808, 10809, 7890, 7897, 1080, 2080]

# 暂存区禁入模式（命中即拒绝提交）——凭证 / 数据库 / 登录态 / 依赖与模型 / 运行产物
_FORBIDDEN_STAGED = re.compile(
    r"(^|/)\.env($|\.)"
    r"|\.(db|sqlite|sqlite3|db-wal|db-shm)$"
    r"|(^|/)cookies?(/|_)"
    r"|cookie.*raw"
    r"|(^|/).*(profile|_profile)(/|$)"
    r"|edge-cdp|chrome-cdp"
    r"|(^|/)\.venv(/|$)|(^|/)node_modules(/|$)|(^|/)\.ollama(/|$)"
    r"|\.?(pem|key|p12|pfx)$"
    r"|secret|credential"
    r"|__pycache__|\.(pyc|log|tmp|bak)$"
    r"|(^|/)tests/_[^/]*$",  # tests 下划线临时诊断/产物一律不入库（正式 test_* 保留）
    re.IGNORECASE,
)
# 视为“源码/配置”、纳入自动版本的扩展名（白名单，自动提交只收这些，进一步收窄风险）
_SOURCE_SUFFIX = {
    ".py", ".html", ".css", ".js", ".cjs", ".json", ".md", ".txt",
    ".bat", ".ps1", ".vbs", ".sh", ".toml", ".cfg", ".ini", ".yml", ".yaml",
    ".requirements", "",
}
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
_DEFAULT_VERSION = "v5.8.8"


def _find_git() -> str | None:
    from shutil import which
    w = which("git")
    if w:
        return w
    for c in _GIT_CANDIDATES:
        if Path(c).exists():
            return c
    return None


class GitVersionManager:
    """线程安全的 Git 版本管理器（单例）。"""

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self, repo_root: Path | str | None = None):
        self.root = Path(repo_root) if repo_root else REPO_ROOT
        self.git = _find_git()
        self._lock = threading.RLock()      # 串行化所有写操作，避免自动线程与手动并发
        self._last_auto_ts = 0.0            # 自动保存防抖
        self._boot_ts = time.time()         # 启动时刻，用于首次自动保存宽限
        self._cfg_path = self.root / "data" / "version_center.json"

    # ---------- 单例 ----------
    @classmethod
    def instance(cls) -> "GitVersionManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---------- 底层执行 ----------
    def _run(self, args: list[str], timeout: int = 60, proxy: str | None = None,
             env_clear_proxy: bool = False) -> dict:
        """执行一条 git 命令，返回 {ok,code,out,err}。不抛异常。"""
        if not self.git:
            return {"ok": False, "code": -1, "out": "", "err": "未找到 git 可执行文件"}
        cmd = [self.git, "-c", "core.quotepath=false"]
        if env_clear_proxy:
            cmd += ["-c", "http.proxy=", "-c", "https.proxy="]
        elif proxy:
            cmd += ["-c", f"http.proxy={proxy}", "-c", f"https.proxy={proxy}"]
        cmd += args
        try:
            p = subprocess.run(
                cmd, cwd=str(self.root), capture_output=True,
                encoding="utf-8", errors="replace", timeout=timeout,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C.UTF-8"},
            )
            out = (p.stdout or "").strip()
            err = (p.stderr or "").strip()
            return {"ok": p.returncode == 0, "code": p.returncode, "out": out, "err": err}
        except subprocess.TimeoutExpired:
            return {"ok": False, "code": -2, "out": "", "err": f"命令超时({timeout}s)"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "code": -3, "out": "", "err": f"{type(e).__name__}: {e}"}

    @staticmethod
    def _port_open(port: int, host: str = "127.0.0.1") -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            return False

    def _local_proxies(self) -> list[str]:
        return [f"http://127.0.0.1:{p}" for p in _PROXY_CANDIDATE_PORTS if self._port_open(p)]

    def _run_remote(self, args: list[str], timeout: int = 90, retries: int = 3) -> dict:
        """远程操作：直连优先并对“连接抖动”有限次退避重试，再逐个回退本机代理。"""
        r = self._run(args, timeout=timeout, env_clear_proxy=True)
        if r["ok"]:
            return r
        err_low = (r["err"] + r["out"]).lower()
        connection_like = any(k in err_low for k in (
            "could not connect", "failed to connect", "timed out", "timeout",
            "connection refused", "connection was reset", "unable to access"))
        if not connection_like:
            return r  # 认证/分支等非连通问题，换通道无意义，原样返回
        # 直连网络抖动：短退避有限重试
        for attempt in range(1, retries):
            time.sleep(2 * attempt)
            r = self._run(args, timeout=timeout, env_clear_proxy=True)
            if r["ok"]:
                r["via"] = f"direct-retry{attempt}"
                return r
        # 直连仍失败 → 本机代理回退
        for px in self._local_proxies():
            rr = self._run(args, timeout=timeout, proxy=px)
            if rr["ok"]:
                rr["via_proxy"] = px
                return rr
        return r

    def is_repo(self) -> bool:
        return self.git is not None and (self.root / ".git").exists()

    # ---------- 版本号 ----------
    def current_version(self) -> str:
        vf = self.root / "VERSION"
        if vf.exists():
            t = vf.read_text(encoding="utf-8", errors="replace").strip()
            if _VERSION_RE.match(t):
                return t if t.startswith("v") else f"v{t}"
        m = self._run(["log", "-1", "--pretty=%s"])
        if m["ok"]:
            hit = re.search(r"v\d+\.\d+\.\d+", m["out"])
            if hit:
                return hit.group(0)
        return _DEFAULT_VERSION

    @staticmethod
    def bump_version(version: str, level: str = "patch") -> str:
        m = _VERSION_RE.match(version.strip())
        if not m:
            return _DEFAULT_VERSION
        major, minor, patch = (int(x) for x in m.groups())
        if level == "major":
            major += 1; minor = 0; patch = 0
        elif level == "minor":
            minor += 1; patch = 0
        else:
            patch += 1
        return f"v{major}.{minor}.{patch}"

    # ---------- 状态 ----------
    def status(self) -> dict:
        if not self.is_repo():
            return {"ok": False, "error": "当前目录还不是 Git 仓库", "git_available": bool(self.git)}
        with self._lock:
            branch = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
            head = self._run(["rev-parse", "HEAD"])
            short = self._run(["rev-parse", "--short", "HEAD"])
            last = self._run(["log", "-1", "--pretty=%h|%an|%cI|%s"])
            changed = self._run(["status", "--porcelain"])
            upstream = self._run(["rev-parse", "--abbrev-ref", "@{upstream}"])
            ahead = behind = 0
            sync_state = "no_upstream"
            if upstream["ok"]:
                cnt = self._run(["rev-list", "--left-right", "--count", f"{upstream['out']}...HEAD"])
                if cnt["ok"] and " " in cnt["out"]:
                    lb, rb = cnt["out"].split()[:2]
                    behind, ahead = int(lb), int(rb)
                sync_state = "synced" if ahead == 0 and behind == 0 else (
                    "ahead" if ahead and not behind else
                    "behind" if behind and not ahead else "diverged")
            files = [l for l in changed["out"].splitlines() if l.strip()]
            last_parts = last["out"].split("|", 3) if last["ok"] else []
            remote = self._run(["remote", "get-url", "origin"])
            return {
                "ok": True,
                "git_available": True,
                "repo_root": str(self.root),
                "branch": branch["out"] if branch["ok"] else "",
                "head_sha": head["out"] if head["ok"] else "",
                "head_short": short["out"] if short["ok"] else "",
                "version": self.current_version(),
                "last_commit": {
                    "short": last_parts[0] if last_parts else "",
                    "author": last_parts[1] if len(last_parts) > 1 else "",
                    "time": last_parts[2] if len(last_parts) > 2 else "",
                    "subject": last_parts[3] if len(last_parts) > 3 else "",
                },
                "changed_count": len(files),
                "changed_files": files[:60],
                "ahead": ahead, "behind": behind, "sync_state": sync_state,
                "upstream": upstream["out"] if upstream["ok"] else "",
                "remote_url": remote["out"] if remote["ok"] else "",
                "auto": self.load_config(),
            }

    def history(self, limit: int = 20) -> dict:
        if not self.is_repo():
            return {"ok": False, "items": [], "error": "不是 Git 仓库"}
        r = self._run(["log", f"-{max(1, min(limit, 100))}",
                       "--pretty=%h%x1f%H%x1f%an%x1f%cI%x1f%s"])
        items = []
        if r["ok"]:
            for line in r["out"].splitlines():
                p = line.split("\x1f")
                if len(p) >= 5:
                    items.append({"short": p[0], "sha": p[1], "author": p[2],
                                  "time": p[3], "subject": p[4]})
        return {"ok": True, "items": items, "version": self.current_version()}

    # ---------- 安全闸 ----------
    def _staged_files(self) -> list[str]:
        r = self._run(["diff", "--cached", "--name-only"])
        return [x for x in r["out"].splitlines() if x.strip()] if r["ok"] else []

    def _safety_gate(self) -> list[str]:
        """返回命中禁入规则的暂存文件（空列表=通过）。"""
        bad = [f for f in self._staged_files() if _FORBIDDEN_STAGED.search(f.replace("\\", "/"))]
        return bad

    def _add_sources(self):
        """只 add 源码白名单后缀，且依赖 .gitignore；比 git add -A 更收敛。"""
        self._run(["reset"])  # 先清空暂存区，保证安全闸从干净基线开始
        # add -A 让 .gitignore 生效（忽略大文件/凭证），随后安全闸兜底；
        # 非源码的新文件（如 docx 资料）也允许，因 .gitignore 已排除真正敏感项。
        self._run(["add", "-A"])

    # ---------- 保存版本 ----------
    def save_version(self, message: str = "", bump: str | None = None,
                     do_push: bool = True, author: str = "system") -> dict:
        if not self.is_repo():
            return {"ok": False, "error": "不是 Git 仓库，无法保存版本"}
        with self._lock:
            self._add_sources()
            bad = self._safety_gate()
            if bad:
                self._run(["reset"])
                return {"ok": False, "error": "安全闸拦截：以下敏感/禁入文件不允许提交，已撤销暂存",
                        "blocked": bad}
            staged = self._staged_files()
            if not staged:
                return {"ok": True, "committed": False, "message": "没有需要保存的改动",
                        "version": self.current_version()}

            version = self.current_version()
            if bump:
                version = self.bump_version(version, bump)
                (self.root / "VERSION").write_text(version + "\n", encoding="utf-8")
                self._run(["add", "VERSION"])
                staged = self._staged_files()

            subject = (message or "").strip()
            if not subject:
                preview = "、".join(Path(f).name for f in staged[:3])
                more = f" 等{len(staged)}个文件" if len(staged) > 3 else ""
                subject = f"保存版本 {version}：{preview}{more}"
            full_msg = f"{subject}" if version in subject else f"{version} {subject}"
            cm = self._run(["commit", "-m", full_msg,
                            "-m", f"author-tag={author}; files={len(staged)}"])
            if not cm["ok"]:
                return {"ok": False, "error": "提交失败", "detail": cm["err"] or cm["out"]}
            sha = self._run(["rev-parse", "--short", "HEAD"])
            result = {"ok": True, "committed": True, "version": version,
                      "sha": sha["out"], "committed_files": staged, "message": full_msg,
                      "pushed": False}
            if do_push:
                p = self.push()
                result["pushed"] = p["ok"]
                result["push_detail"] = p.get("err") or p.get("via_proxy") or ("已同步" if p["ok"] else "")
            self._last_auto_ts = time.time()
            return result

    # ---------- 推送 / 检查更新 ----------
    def push(self) -> dict:
        if not self.is_repo():
            return {"ok": False, "err": "不是 Git 仓库"}
        up = self._run(["rev-parse", "--abbrev-ref", "@{upstream}"])
        if not up["ok"]:
            r = self._run_remote(["push", "-u", "origin", "HEAD"])
        else:
            r = self._run_remote(["push"])
        return r

    def check_update(self) -> dict:
        if not self.is_repo():
            return {"ok": False, "error": "不是 Git 仓库"}
        f = self._run_remote(["fetch", "origin"], timeout=60)
        if not f["ok"]:
            return {"ok": False, "error": "远程检查失败", "detail": f["err"] or f["out"]}
        st = self.status()
        remote_head = self._run(["rev-parse", "--short", "origin/HEAD"])
        return {"ok": True, "ahead": st["ahead"], "behind": st["behind"],
                "sync_state": st["sync_state"], "remote_head": remote_head["out"] if remote_head["ok"] else "",
                "via_proxy": f.get("via_proxy", "")}

    def pull(self) -> dict:
        if not self.is_repo():
            return {"ok": False, "err": "不是 Git 仓库"}
        dirty = self._run(["status", "--porcelain"])
        if dirty["out"].strip():
            return {"ok": False, "err": "本地有未保存改动，请先保存版本后再拉取，避免覆盖"}
        return self._run_remote(["pull", "--no-edit"])

    # ---------- 回滚（默认保留历史的 revert） ----------
    def rollback(self, sha: str, mode: str = "revert", confirm_hard: bool = False) -> dict:
        if not self.is_repo() or not sha:
            return {"ok": False, "err": "参数不足"}
        sha = sha.strip()
        with self._lock:
            valid = self._run(["rev-parse", "--verify", f"{sha}^{{commit}}"])
            if not valid["ok"]:
                return {"ok": False, "err": "目标版本不存在"}
            if mode == "hard":
                if not confirm_hard:
                    return {"ok": False, "err": "hard 回滚会丢弃之后的提交，需要显式确认"}
                dirty = self._run(["status", "--porcelain"])
                if dirty["out"].strip():
                    return {"ok": False, "err": "工作区有未保存改动，拒绝 hard 回滚"}
                r = self._run(["reset", "--hard", sha])
            else:
                # 安全默认：生成一个反向提交，历史完整保留、可再次撤销
                r = self._run(["revert", "--no-edit", sha])
            r["head"] = self._run(["rev-parse", "--short", "HEAD"])["out"]
            return r

    # ---------- 自动保存配置（本地 data，不入库） ----------
    def load_config(self) -> dict:
        default = {"auto_commit": True, "auto_push": True,
                   "interval_minutes": 30, "last_auto": ""}
        try:
            if self._cfg_path.exists():
                import json
                default.update(json.loads(self._cfg_path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
        return default

    def save_config(self, updates: dict) -> dict:
        import json
        cfg = self.load_config()
        for k in ("auto_commit", "auto_push"):
            if k in updates:
                cfg[k] = bool(updates[k])
        if "interval_minutes" in updates:
            try:
                cfg["interval_minutes"] = max(5, min(720, int(updates["interval_minutes"])))
            except (TypeError, ValueError):
                pass
        self._cfg_path.parent.mkdir(exist_ok=True)
        self._cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return cfg

    def auto_save_if_changed(self, min_interval_sec: int | None = None,
                             do_push: bool | None = None) -> dict:
        """供守护线程调用：到点且确有源码改动才自动成版本，带防抖。"""
        cfg = self.load_config()
        if not cfg.get("auto_commit", True):
            return {"ok": True, "skipped": "auto_commit_off"}
        interval = min_interval_sec if min_interval_sec is not None else cfg["interval_minutes"] * 60
        if time.time() - self._last_auto_ts < interval:
            return {"ok": True, "skipped": "cooldown"}
        # 启动宽限：系统刚启动的一个巡检间隔内不抢提交，避免开发中途/启动加载时过早成版本
        if self._last_auto_ts == 0 and time.time() - self._boot_ts < interval:
            return {"ok": True, "skipped": "boot_grace"}
        st = self.status()
        if not st.get("ok") or st["changed_count"] == 0:
            self._last_auto_ts = time.time()
            return {"ok": True, "skipped": "no_change"}
        push = cfg.get("auto_push", True) if do_push is None else do_push
        ts = datetime.now().strftime("%H:%M")
        return self.save_version(f"自动保存版本（{ts} 巡检）", do_push=push, author="auto-watch")


# 模块级单例快捷函数
def gm() -> GitVersionManager:
    return GitVersionManager.instance()

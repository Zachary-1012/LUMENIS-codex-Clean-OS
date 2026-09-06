# -*- coding: utf-8 -*-
"""LUMENIS Repository Registry — 双核仓库注册表 + 跨平台路径解析（P0-01 / P0-03）。

把 OSAI 对 ZBC 的硬编码路径升级为注册表驱动，Windows / macOS / Linux / Cloud / Server 统一：
    环境变量 → 本地探测 → 平台默认值  三级解析。

角色（LUMENIS Dual-Core Architecture）：
    ZBC  = Production Core（生产事实与执行）
    OSAI = Intelligence Core（智能与研发决策）

设计红线：
    - 不合并两个 Git Repository；本注册表只登记事实，不做任何代码合并。
    - 解析出的路径仅作为运行时事实，不覆盖用户显式配置的环境变量。
    - SHA / branch 只读获取，不做写操作。
"""
import os
import shutil
import subprocess

_CORE_ROLES = {"ZBC": "production", "OSAI": "intelligence"}
_CORE_NAMES = {"ZBC": "Z-Brand-Core", "OSAI": "Zachary-OS-AI"}
_CORE_URLS = {
    "ZBC": "https://github.com/Zachary-1012/Z-Brand-Core",
    "OSAI": "https://github.com/Zachary-1012/Zachary-OS-AI",
}


def _default_root(key):
    """平台默认值（保持既有 Windows 行为不变；其他平台探测常见位置）。"""
    if key == "ZBC":
        # 1) 既有硬编码默认值（Windows 生产机）；2) 其他平台常见探测路径
        win_default = r"D:\Taikoo-monitor-new"
        if os.path.isdir(win_default):
            return os.path.normpath(win_default)
        for cand in (
            os.path.expanduser("~/Taikoo-monitor-new"),
            os.path.expanduser("~/z-brand-core"),
            "/workspace/Taikoo-monitor-new",
            "/app/Taikoo-monitor-new",
        ):
            if os.path.isdir(cand):
                return cand
        return os.path.normpath(win_default)
    if key == "OSAI":
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raise KeyError("unknown repository key: %s" % key)


def resolve_path(key):
    """解析仓库根路径：环境变量（{KEY}_ROOT）→ 存在性校验 → 平台默认值。"""
    key = key.upper()
    env = os.environ.get(key + "_ROOT", "").strip().strip('"').strip("'")
    if env and os.path.isdir(env):
        return os.path.normpath(env)
    return os.path.normpath(_default_root(key))


def resolve_python(key="ZBC"):
    """解析 Python 解释器（三级优先，跨平台）：
    1) 显式优先 ZBC .venv（无论 key 是什么）
    2) key 对应仓库自身的 .venv
    3) 系统 python（Windows 跳过 WindowsApps stub，优先 python；Unix 优先 python3）
    """
    def _venv_candidates(root):
        if os.name == "nt":
            return [
                os.path.join(root, ".venv", "Scripts", "python.exe"),
                os.path.join(root, ".venv", "python.exe"),
            ]
        return [
            os.path.join(root, ".venv", "bin", "python3"),
            os.path.join(root, ".venv", "bin", "python"),
        ]

    # 1) ZBC .venv 显式优先
    zbc_root = resolve_path("ZBC")
    for c in _venv_candidates(zbc_root):
        if os.path.exists(c):
            return c
    # 2) key 对应仓库自身 .venv
    root = resolve_path(key)
    for c in _venv_candidates(root):
        if os.path.exists(c):
            return c
    # 3) 系统 python
    if os.name == "nt":
        # Windows：跳过 WindowsApps stub，优先 python 再 python3
        for exe in ("python", "python3"):
            p = shutil.which(exe)
            if p and "WindowsApps" not in p:
                return p
        return "python"
    # Unix：python3 优先
    return shutil.which("python3") or shutil.which("python") or "python3"


def _git(key, args, timeout=30):
    root = resolve_path(key)
    try:
        r = subprocess.run(["git"] + args, cwd=root, capture_output=True,
                           text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def git_sha(key):
    return _git(key, ["rev-parse", "HEAD"]) or "UNKNOWN"


def git_branch(key):
    return _git(key, ["branch", "--show-current"]) or "UNKNOWN"


def git_status(key):
    return _git(key, ["status", "--short"]) or "(clean)"


def get_repo_info(key):
    """仓库事实快照：name / role / root / python / branch / sha / url。"""
    key = key.upper()
    return {
        "name": _CORE_NAMES[key],
        "role": _CORE_ROLES[key],
        "url": _CORE_URLS[key],
        "root": resolve_path(key),
        "python": resolve_python(key),
        "branch": git_branch(key),
        "sha": git_sha(key),
        "git_status": git_status(key),
    }


def registry_snapshot():
    """双核注册表全量快照（可观测）。"""
    return {k: get_repo_info(k) for k in _CORE_ROLES}


if __name__ == "__main__":
    import json
    print(json.dumps(registry_snapshot(), ensure_ascii=False, indent=2))

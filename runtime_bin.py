"""统一解析本地运行时二进制（当前：Node.js）—— Canonical resolver。

背景
----
多个采集模块通过 subprocess 调用 ``['node', script, ...]``，裸命令 ``node``
依赖「运行该进程时的 PATH」。生产常驻进程（Start-Process 隐藏窗口 / 开机自启 /
脱离交互 Shell）继承的 PATH 不一定包含 node，于是 subprocess 抛
``[WinError 2] 系统找不到指定的文件``。topic_campaign_snapshots 曾因此
326 条快照中 310 条 error、浏览/讨论/笔记指标全为 0。

本模块给出确定性解析顺序（结果缓存，进程内只解析一次）：

    1. 显式环境变量 NODE_EXE / ZBC_NODE_PATH（最高优先级，便于运维覆盖）
    2. PATH 中的 node（shutil.which）
    3. 项目内置 ``nodejs/node(.exe)``（随仓库走的确定性兜底，不依赖外部安装）
    4. 操作系统常见安装路径（Program Files / 标准 Unix 路径）

设计约束
--------
- 纯标准库，零新增依赖；
- 只「定位」不「启动」，不改变任何采集脚本、参数与业务逻辑；
- 解析不到返回 None，由调用方产出结构化错误，而不是让 subprocess 抛 WinError 2。
"""
from __future__ import annotations

import functools
import os
import shutil
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_IS_WIN = sys.platform.startswith("win")
_EXE_NAME = "node.exe" if _IS_WIN else "node"


def _candidate_paths():
    """返回按优先级排列的 node 候选路径（不去重、不判存，便于诊断）。"""
    candidates = []

    env_explicit = (os.getenv("NODE_EXE") or os.getenv("ZBC_NODE_PATH") or "").strip()
    if env_explicit:
        candidates.append(env_explicit)

    on_path = shutil.which("node") or shutil.which("node.exe")
    if on_path:
        candidates.append(on_path)

    # 项目内置（仓库自带 nodejs/runtime，确定性兜底）
    candidates.append(os.path.join(_ROOT, "nodejs", _EXE_NAME))

    if _IS_WIN:
        program_files = os.getenv("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)")
        candidates.append(os.path.join(program_files, "nodejs", "node.exe"))
        candidates.append(os.path.join(program_files_x86, "nodejs", "node.exe"))
    else:
        candidates.extend(
            [
                "/usr/local/bin/node",
                "/usr/bin/node",
                "/opt/homebrew/bin/node",
            ]
        )
    return candidates


@functools.lru_cache(maxsize=1)
def resolve_node():
    """返回可用的 node 可执行文件绝对路径；全部不可用则返回 None。

    裸字符串 ``node`` 也视为合法（交由 subprocess 走 PATH，保持向后兼容）。
    """
    for cand in _candidate_paths():
        if not cand:
            continue
        if cand == "node":
            return cand
        if os.path.isfile(cand):
            return cand
    return None


def node_or_raise():
    """同 resolve_node，但解析不到时抛带运维指引的 FileNotFoundError。"""
    node_bin = resolve_node()
    if not node_bin:
        raise FileNotFoundError(
            "未找到 Node.js 运行时：请设置环境变量 NODE_EXE 指向 node 可执行文件，"
            "或将 node 放入项目 nodejs/ 目录，或将 node 加入系统 PATH。"
        )
    return node_bin


def node_diagnostics():
    """返回诊断信息（候选清单 + 命中项），用于健康检查 / Evidence。"""
    candidates = _candidate_paths()
    resolved = resolve_node()
    return {
        "resolved": resolved,
        "candidates": candidates,
        "builtin_exists": os.path.isfile(os.path.join(_ROOT, "nodejs", _EXE_NAME)),
        "platform": sys.platform,
    }

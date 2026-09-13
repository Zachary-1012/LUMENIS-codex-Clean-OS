"""LUMENIS 统一数据库路径解析 / 隔离契约（P0-DBISO-01）。

这是全仓“打开哪一个 SQLite 文件”的唯一事实源（single source of truth）。
解析在**调用时**（call time）进行，而不是 import 时一次性固化，因此测试 /
Staging / 隔离运行只要设置环境变量即可重定向全部写连接，与模块 import 顺序无关。

环境变量优先级（取第一个被设置且非空的值）；未设置任何变量时，默认路径与历史
完全一致，都是 <repo>/data/monitor.db，保证向后兼容、不产生静默路径变更：

    main      : ZBC_DB_PATH
    evidence  : ZBC_EVIDENCE_DB_PATH  -> ZBC_DB_PATH
    guardian  : ZBC_RUNTIME_GUARDIAN_DB -> ZBC_DB_PATH
    token     : ZBC_TOKEN_DB_PATH     -> ZBC_DB_PATH（ark_llm 用量表与主库同库）

本模块只依赖标准库 os，不 import 任何业务模块，因此可以被任意模块安全引用，
不存在循环 import 风险。这里**不做**任何业务语义判断，只负责路径解析。
"""

from __future__ import annotations

import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#: 未设置任何隔离环境变量时的默认生产/开发库（与历史行为一致）。
DEFAULT_DB_PATH: str = os.path.join(_BASE_DIR, "data", "monitor.db")


def _first_env(*names: str) -> str | None:
    """返回第一个被设置且去空白后非空的环境变量的绝对路径；都没有则 None。"""
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip():
            return os.path.abspath(str(value).strip())
    return None


def main_db_path() -> str:
    """主库路径：ZBC_DB_PATH，否则默认 data/monitor.db。"""
    return _first_env("ZBC_DB_PATH") or DEFAULT_DB_PATH


def evidence_db_path() -> str:
    """证据库路径：优先专用 ZBC_EVIDENCE_DB_PATH，回退统一的 ZBC_DB_PATH。

    历史上这里只认 ZBC_EVIDENCE_DB_PATH，导致只设置 ZBC_DB_PATH 的隔离运行仍把
    zbc_evidence 写进真实默认库（P0-DBISO-01 根因）；现在补齐回退层级。
    """
    return _first_env("ZBC_EVIDENCE_DB_PATH", "ZBC_DB_PATH") or DEFAULT_DB_PATH


def guardian_db_path() -> str:
    """运行守护库路径：优先 ZBC_RUNTIME_GUARDIAN_DB，回退 ZBC_DB_PATH。"""
    return _first_env("ZBC_RUNTIME_GUARDIAN_DB", "ZBC_DB_PATH") or DEFAULT_DB_PATH


def token_db_path() -> str:
    """AI token 用量库路径（与主库同库）：优先 ZBC_TOKEN_DB_PATH，回退 ZBC_DB_PATH。"""
    return _first_env("ZBC_TOKEN_DB_PATH", "ZBC_DB_PATH") or DEFAULT_DB_PATH

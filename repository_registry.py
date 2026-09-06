# -*- coding: utf-8 -*-
"""
ZBC Repository Registry — 统一路径注册中心

目标：消除生产代码中的个人电脑绝对路径，建立
    ENV → config → registry → runtime
路径解析链。

核心原则：
- REPO_ROOT 基于 __file__ 自动解析，兼容开发/生产/客户 Release 环境
- 所有关键目录集中注册，支持 ENV 覆盖
- resolve_path() 统一处理相对/绝对路径
- 向后兼容：不破坏 config.py 的 BASE_DIR 用法
- 不写入任何个人路径，不依赖任何外部配置即可 import

使用方法：
    from repository_registry import get_registry, resolve_path

    registry = get_registry()
    db_path = registry.data_dir / 'monitor.db'      # pathlib
    db_path = registry.resolve('data/monitor.db')   # str
    db_path = resolve_path('data/monitor.db')       # 模块级便捷函数
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional


# ── 单例状态 ──────────────────────────────────────────────
_registry: Optional["RepositoryRegistry"] = None


class RepositoryRegistry:
    """统一路径注册中心

    所有路径均以 pathlib.Path 存储，同时提供 str 访问器。
    目录在首次访问时自动创建（exist_ok=True）。
    """

    # 目录键 → ENV 覆盖变量名 → 默认相对路径（相对于 REPO_ROOT）
    _DIR_SPEC: Dict[str, Dict[str, str]] = {
        "core":        {"env": "ZBC_CORE_DIR",        "default": "."},
        "data":        {"env": "ZBC_DATA_DIR",        "default": "data"},
        "runtime":     {"env": "ZBC_RUNTIME_DIR",     "default": "browser_runtime"},
        "backup":      {"env": "ZBC_BACKUP_DIR",      "default": "backups"},
        "export":      {"env": "ZBC_EXPORT_DIR",      "default": "report_export"},
        "temp":        {"env": "ZBC_TEMP_DIR",        "default": "staging"},
        "ai_runtime":  {"env": "ZBC_AI_RUNTIME_DIR",  "default": ".ollama"},
        "collector":   {"env": "ZBC_COLLECTOR_DIR",   "default": "collector_v2"},
        "log":         {"env": "ZBC_LOG_DIR",         "default": "logs"},
        "config":      {"env": "ZBC_CONFIG_DIR",      "default": "config"},
    }

    def __init__(self, repo_root: Optional[str] = None):
        """初始化注册中心

        Args:
            repo_root: 显式指定仓库根目录（测试用）。
                       为 None 时优先读 ZBC_REPO_ROOT，其次基于 __file__ 解析。
        """
        # 1. 显式参数 > 2. ENV > 3. __file__ 自动解析
        if repo_root is not None:
            self._repo_root = Path(repo_root).resolve()
        else:
            env_root = os.environ.get("ZBC_REPO_ROOT")
            if env_root:
                self._repo_root = Path(env_root).resolve()
            else:
                # 本文件位于仓库根目录，dirname 即为 REPO_ROOT
                self._repo_root = Path(__file__).resolve().parent

        # 解析各目录
        self._dirs: Dict[str, Path] = {}
        for key, spec in self._DIR_SPEC.items():
            env_val = os.environ.get(spec["env"])
            if env_val:
                p = Path(env_val)
                # 相对路径基于 REPO_ROOT 解析
                if not p.is_absolute():
                    p = self._repo_root / p
                self._dirs[key] = p.resolve()
            else:
                self._dirs[key] = (self._repo_root / spec["default"]).resolve()

        # 缓存已创建的目录，避免重复 makedirs
        self._ensured: set = set()

    # ── 属性访问器 ──────────────────────────────────────────

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @property
    def core_dir(self) -> Path:
        return self._dirs["core"]

    @property
    def data_dir(self) -> Path:
        return self._dirs["data"]

    @property
    def runtime_dir(self) -> Path:
        return self._dirs["runtime"]

    @property
    def backup_dir(self) -> Path:
        return self._dirs["backup"]

    @property
    def export_dir(self) -> Path:
        return self._dirs["export"]

    @property
    def temp_dir(self) -> Path:
        return self._dirs["temp"]

    @property
    def ai_runtime_dir(self) -> Path:
        return self._dirs["ai_runtime"]

    @property
    def collector_dir(self) -> Path:
        return self._dirs["collector"]

    @property
    def log_dir(self) -> Path:
        return self._dirs["log"]

    @property
    def config_dir(self) -> Path:
        return self._dirs["config"]

    # ── 核心方法 ────────────────────────────────────────────

    def resolve(self, relative_path: str, ensure_dir: bool = False) -> str:
        """将相对路径解析为基于 REPO_ROOT 的绝对路径（str）

        - 若输入已是绝对路径，原样返回（规范化分隔符）
        - 若输入为相对路径，拼接 REPO_ROOT

        Args:
            relative_path: 相对或绝对路径
            ensure_dir: 若为 True，确保路径的父目录存在

        Returns:
            绝对路径字符串
        """
        p = Path(relative_path)
        if not p.is_absolute():
            p = self._repo_root / p
        result = str(p.resolve())

        if ensure_dir:
            parent = p.parent
            if str(parent) not in self._ensured:
                parent.mkdir(parents=True, exist_ok=True)
                self._ensured.add(str(parent))

        return result

    def resolve_path(self, relative_path: str, ensure_dir: bool = False) -> Path:
        """resolve() 的 pathlib.Path 版本"""
        return Path(self.resolve(relative_path, ensure_dir=ensure_dir))

    def ensure_dir(self, dir_key: str) -> Path:
        """确保指定目录存在并返回 Path

        Args:
            dir_key: 目录键（core/data/runtime/backup/export/temp/ai_runtime/collector/log/config）

        Returns:
            目录 Path
        """
        if dir_key not in self._dirs:
            raise KeyError(f"未知目录键: {dir_key}, 可用: {list(self._dirs.keys())}")
        d = self._dirs[dir_key]
        if str(d) not in self._ensured:
            d.mkdir(parents=True, exist_ok=True)
            self._ensured.add(str(d))
        return d

    def all_dirs(self) -> Dict[str, Path]:
        """返回所有已注册目录的副本"""
        return dict(self._dirs)

    def to_dict(self) -> Dict[str, str]:
        """序列化为字典（str 路径），用于调试/日志"""
        return {
            "repo_root": str(self._repo_root),
            **{k: str(v) for k, v in self._dirs.items()},
        }

    def __repr__(self) -> str:
        return f"RepositoryRegistry(repo_root={self._repo_root!r})"


# ── 模块级便捷函数 ─────────────────────────────────────────

def get_registry(force_reload: bool = False) -> RepositoryRegistry:
    """获取 RepositoryRegistry 单例

    Args:
        force_reload: 强制重新初始化（测试/ENV 变更后用）

    Returns:
        RepositoryRegistry 实例
    """
    global _registry
    if _registry is None or force_reload:
        _registry = RepositoryRegistry()
    return _registry


def resolve_path(relative_path: str, ensure_dir: bool = False) -> str:
    """模块级便捷函数：解析相对路径为绝对路径（str）

    等价于 get_registry().resolve(relative_path, ensure_dir)
    """
    return get_registry().resolve(relative_path, ensure_dir=ensure_dir)


# ── 向后兼容别名 ───────────────────────────────────────────
# 保持与 config.py BASE_DIR 模式的语义一致，便于渐进迁移
BASE_DIR = str(Path(__file__).resolve().parent)


if __name__ == "__main__":
    reg = get_registry()
    print("=" * 60)
    print("ZBC Repository Registry")
    print("=" * 60)
    for k, v in reg.to_dict().items():
        print(f"  {k:15s} = {v}")
    print()
    print(f"  resolve('data/monitor.db') = {reg.resolve('data/monitor.db')}")
    print(f"  resolve('.env')             = {reg.resolve('.env')}")

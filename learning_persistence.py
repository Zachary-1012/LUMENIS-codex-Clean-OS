# -*- coding: utf-8 -*-
"""
learning_persistence.py — ZBC 学习数据持久化管理器
=====================================================
语义对齐 OSAI components/Development-Command-Console/server/persistence.js (V0.4.1 P3)，
为 ZBC 生产侧提供独立的 JSON 文件持久化能力，用于沉淀 AI/开发执行学习数据。

集合（10）：
  cases / patterns / lessons / failures / shadow_analyses / bundles /
  evidences / knowledge / knowledge_lineage / learning_runs

设计：
  - 零依赖 JSON 文件持久化（标准库 only）
  - 原子写入（.tmp + os.replace）
  - 自动备份（backup_count 轮换），主文件损坏时从备份自愈
  - data_dir 内自动生成 .gitignore（学习数据不入库）
  - StorageAdapter 接口预留（后续可迁移 SQLite）
  - 安全边界：仅本地存储、不存任何凭证/密钥
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

DEFAULT_DATA_DIR = Path("data/learning")
DEFAULT_BACKUP_COUNT = 5

# 集合定义：name -> 描述（文件名为 <name>.json）
COLLECTIONS = {
    "cases": "失败/修复案例",
    "patterns": "成功模式",
    "lessons": "经验教训",
    "failures": "失败记录",
    "shadow_analyses": "影子分析",
    "bundles": "证据包",
    "evidences": "证据",
    "knowledge": "知识条目",
    "knowledge_lineage": "知识溯源",
    "learning_runs": "学习运行记录",
}

# StorageAdapter 契约（预留 SQLite 迁移）
STORAGE_ADAPTER = {
    "version": "1.0",
    "methods": ["init", "save", "load", "delete", "query", "get_status"],
}


class LearningPersistence:
    """ZBC 学习数据持久化管理器（单例语义）。"""

    def __init__(self):
        self._data_dir: Path | None = None
        self._enabled = False
        self._initialized = False
        self._backup_count = DEFAULT_BACKUP_COUNT
        self._auto_save = False
        self._pretty_print = False

    # ---------- 初始化 ----------
    def init(self, data_dir=None, enabled=True, backup_count=None,
             auto_save=True, auto_save_debounce_ms=100, pretty_print=False):
        """初始化持久化管理器。enabled=False 时仅记录配置不写盘（降级回退）。"""
        if data_dir is None:
            data_dir = DEFAULT_DATA_DIR
        self._data_dir = Path(data_dir)
        self._backup_count = max(1, backup_count if backup_count is not None else DEFAULT_BACKUP_COUNT)
        self._auto_save = bool(auto_save)
        self._pretty_print = bool(pretty_print)
        self._enabled = bool(enabled)
        self._initialized = True

        if self._enabled:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._ensure_gitignore()
        return {"ok": True, "enabled": self._enabled, "data_dir": str(self._data_dir)}

    def _ensure_gitignore(self):
        """学习数据不入库（默认忽略全部）。"""
        gi = self._data_dir / ".gitignore"
        if not gi.exists():
            gi.write_text("*\n", encoding="utf-8")

    def is_initialized(self) -> bool:
        return self._initialized

    def is_enabled(self) -> bool:
        return self._initialized and self._enabled

    # ---------- 内部路径 ----------
    def _path(self, name: str) -> Path:
        return self._data_dir / f"{name}.json"

    def _backup_path(self, name: str, ts: str) -> Path:
        return self._data_dir / f"{name}.backup.{ts}.json"

    # ---------- 保存 ----------
    def save_collection(self, name, data, immediate=True):
        """保存集合。返回 {ok, skipped?}；未知集合返回 UNKNOWN_COLLECTION。"""
        if name not in COLLECTIONS:
            return {"ok": False, "error": "UNKNOWN_COLLECTION"}
        if not self._initialized:
            return {"ok": False, "error": "NOT_INITIALIZED"}
        if not self._enabled:
            return {"ok": True, "skipped": True}

        path = self._path(name)
        # 备份旧文件
        if path.exists():
            ts = time.strftime("%Y%m%dT%H%M%S", time.localtime())
            self._rotate_backups(name, ts)
            backup = self._backup_path(name, ts)
            try:
                # 只备份合法 JSON（坏文件不备份，避免污染备份链）
                json.loads(path.read_text(encoding="utf-8"))
                os.replace(path, backup)
            except (json.JSONDecodeError, OSError):
                pass

        # 原子写入
        tmp = self._data_dir / f"{name}.json.tmp"
        content = json.dumps(data, ensure_ascii=False, indent=2 if self._pretty_print else None)
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
        return {"ok": True, "collection": name}

    def _rotate_backups(self, name, ts):
        """按 backup_count 轮换备份，超限删除最旧。"""
        backups = sorted(
            self._data_dir.glob(f"{name}.backup.*.json"),
            key=lambda p: p.name, reverse=True,
        )
        for old in backups[self._backup_count - 1:]:
            try:
                old.unlink()
            except OSError:
                pass

    # ---------- 加载 ----------
    def load_collection(self, name):
        """加载集合；文件不存在返回 None；损坏时从备份恢复。"""
        if name not in COLLECTIONS or not self._initialized:
            return None
        path = self._path(name)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return self.load_from_backup(name)

    def load_from_backup(self, name):
        """从最近备份恢复；无备份返回 None。"""
        backups = sorted(
            self._data_dir.glob(f"{name}.backup.*.json"),
            key=lambda p: p.name, reverse=True,
        )
        for backup in backups:
            try:
                return json.loads(backup.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
        return None

    # ---------- 导入/导出 ----------
    def export_collection(self, name):
        """导出集合（json 格式标记）。"""
        if name not in COLLECTIONS:
            return {"ok": False, "error": "UNKNOWN_COLLECTION"}
        return {"ok": True, "collection": name, "format": "json"}

    def import_collection(self, name, data):
        """导入集合数据并落盘。"""
        if name not in COLLECTIONS:
            return {"ok": False, "error": "UNKNOWN_COLLECTION"}
        if not self._initialized:
            return {"ok": False, "error": "NOT_INITIALIZED"}
        if not self._enabled:
            return {"ok": True, "skipped": True}
        return self.save_collection(name, data, immediate=True)

    # ---------- 状态 ----------
    def get_status(self):
        """返回存储配置与集合清单。"""
        return {
            "initialized": self._initialized,
            "enabled": self._enabled,
            "data_dir": str(self._data_dir) if self._data_dir else None,
            "storage_type": "json-file",
            "collections": list(COLLECTIONS.keys()),
            "backup_count": self._backup_count,
            "auto_save": self._auto_save,
            "storage_adapter": STORAGE_ADAPTER["version"],
        }

    def get_collection_names(self):
        return list(COLLECTIONS.keys())

    # ---------- 测试钩子 ----------
    def _reset_for_testing(self):
        """重置单例状态（测试隔离用）。"""
        self._data_dir = None
        self._enabled = False
        self._initialized = False
        self._backup_count = DEFAULT_BACKUP_COUNT
        self._auto_save = False
        self._pretty_print = False


# 模块级单例
_persistence = LearningPersistence()


def init(**kwargs):
    return _persistence.init(**kwargs)


def is_initialized():
    return _persistence.is_initialized()


def is_enabled():
    return _persistence.is_enabled()


def save_collection(name, data, immediate=True):
    return _persistence.save_collection(name, data, immediate)


def load_collection(name):
    return _persistence.load_collection(name)


def load_from_backup(name):
    return _persistence.load_from_backup(name)


def export_collection(name):
    return _persistence.export_collection(name)


def import_collection(name, data):
    return _persistence.import_collection(name, data)


def get_status():
    return _persistence.get_status()


def get_collection_names():
    return _persistence.get_collection_names()


def _reset_for_testing():
    _persistence._reset_for_testing()


# 暴露契约常量（供测试/调用方引用）
COLLECTION_NAMES = list(COLLECTIONS.keys())

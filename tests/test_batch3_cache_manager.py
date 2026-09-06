# -*- coding: utf-8 -*-
"""Batch3 单元测试：cache_manager 本地缓存降级模块。

验证维度：
- 入口/参数：函数签名、默认值
- 核心逻辑：快照创建、过期清理、快照列表、删除
- DB操作：使用临时数据库，不触碰生产data/monitor.db
- 返回值：返回类型一致性
- 异常处理：数据库不存在、缓存不存在等边界
"""
import sys
import json
import time
import sqlite3
import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import cache_manager
from cache_manager import (
    create_snapshot, get_latest_cache, get_cache_status,
    get_cached_data, list_snapshots, delete_snapshot,
    _load_meta, _save_meta, _ensure_dirs,
)


@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
    """将cache_manager的CACHE_DIR重定向到临时目录。"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(cache_manager, 'CACHE_DIR', cache_dir)
    monkeypatch.setattr(cache_manager, 'CACHE_META', cache_dir / "cache_meta.json")
    return cache_dir


@pytest.fixture
def temp_db(tmp_path):
    """创建一个临时测试数据库。"""
    db_path = tmp_path / "test_monitor.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, author TEXT, likes INTEGER DEFAULT 0, collects INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, sentiment TEXT, risk_level TEXT, created_at TEXT, url TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, title TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, level TEXT, created_at TEXT)")
    conn.execute("INSERT INTO notes (title, author, sentiment, created_at) VALUES ('测试笔记1', '用户A', 'positive', '2026-01-01 10:00:00')")
    conn.execute("INSERT INTO notes (title, author, sentiment, created_at) VALUES ('测试笔记2', '用户B', 'negative', '2026-01-02 11:00:00')")
    conn.execute("INSERT INTO alerts (level, created_at) VALUES ('high', '2026-01-02 12:00:00')")
    conn.commit()
    conn.close()
    return str(db_path)


class TestEnsureDirs:
    """测试目录确保功能。"""

    def test_ensure_dirs_creates_dir(self, temp_cache):
        """_ensure_dirs应创建缓存目录。"""
        # 删除目录后重新创建
        import shutil
        shutil.rmtree(str(temp_cache))
        assert not temp_cache.exists()
        _ensure_dirs()
        assert temp_cache.exists()


class TestLoadSaveMeta:
    """测试元数据加载与保存。"""

    def test_load_meta_empty(self, temp_cache):
        """无元数据文件时应返回默认结构。"""
        meta = _load_meta()
        assert "snapshots" in meta
        assert "current" in meta
        assert meta["snapshots"] == []
        assert meta["current"] is None

    def test_save_and_load_meta(self, temp_cache):
        """保存后应能正确加载。"""
        meta = {"snapshots": [{"id": "test1"}], "current": "test1"}
        _save_meta(meta)
        loaded = _load_meta()
        assert loaded["current"] == "test1"
        assert len(loaded["snapshots"]) == 1

    def test_load_meta_corrupted(self, temp_cache):
        """损坏的元数据文件应返回默认结构。"""
        (temp_cache / "cache_meta.json").write_text("not valid json{{{", encoding="utf-8")
        meta = _load_meta()
        assert meta["snapshots"] == []


class TestCreateSnapshot:
    """测试快照创建功能。"""

    def test_create_snapshot_success(self, temp_cache, temp_db):
        """成功创建快照应返回success=True。"""
        result = create_snapshot(db_path=temp_db)
        assert result["success"] is True
        assert "snapshot" in result
        assert "id" in result["snapshot"]
        assert "created_at" in result["snapshot"]

    def test_create_snapshot_db_not_exist(self, temp_cache):
        """数据库不存在时应返回错误。"""
        result = create_snapshot(db_path="/nonexistent/path.db")
        assert result["success"] is False
        assert "error" in result

    def test_create_snapshot_updates_meta(self, temp_cache, temp_db):
        """创建快照后元数据应更新。"""
        create_snapshot(db_path=temp_db)
        meta = _load_meta()
        assert len(meta["snapshots"]) == 1
        assert meta["current"] is not None

    def test_create_multiple_snapshots(self, temp_cache, temp_db):
        """创建多个快照应都保存在元数据中。"""
        for _ in range(3):
            time.sleep(1.1)  # 快照ID精度到秒
            create_snapshot(db_path=temp_db)
        meta = _load_meta()
        assert len(meta["snapshots"]) == 3

    def test_snapshot_max_limit(self, temp_cache, temp_db, monkeypatch):
        """超过MAX_SNAPSHOTS时应清理旧快照。"""
        monkeypatch.setattr(cache_manager, 'MAX_SNAPSHOTS', 2)
        for i in range(4):
            time.sleep(1.1)
            create_snapshot(db_path=temp_db)
        meta = _load_meta()
        assert len(meta["snapshots"]) <= 2


class TestGetLatestCache:
    """测试获取最新缓存。"""

    def test_no_cache_returns_none(self, temp_cache):
        """无缓存时应返回None。"""
        assert get_latest_cache() is None

    def test_with_cache_returns_latest(self, temp_cache, temp_db):
        """有缓存时应返回最新的快照。"""
        create_snapshot(db_path=temp_db)
        time.sleep(1.1)
        create_snapshot(db_path=temp_db)
        latest = get_latest_cache()
        assert latest is not None
        meta = _load_meta()
        assert latest["id"] == meta["snapshots"][-1]["id"]


class TestGetCacheStatus:
    """测试获取缓存状态。"""

    def test_no_cache_status(self, temp_cache):
        """无缓存时的状态应正确。"""
        status = get_cache_status()
        assert status["has_cache"] is False
        assert status["cache_count"] == 0
        assert status["latest_snapshot"] is None
        assert status["should_use_cache"] is False

    def test_with_cache_status(self, temp_cache, temp_db):
        """有缓存时的状态应正确。"""
        create_snapshot(db_path=temp_db)
        status = get_cache_status()
        assert status["has_cache"] is True
        assert status["cache_count"] == 1
        assert status["latest_snapshot"] is not None
        assert status["is_expired"] is False
        assert status["should_use_cache"] is True

    def test_expired_cache_status(self, temp_cache, temp_db, monkeypatch):
        """过期缓存的状态应正确。"""
        create_snapshot(db_path=temp_db)
        # 手动修改created_ts为很久以前
        meta = _load_meta()
        meta["snapshots"][0]["created_ts"] = time.time() - 100 * 3600  # 100小时前
        _save_meta(meta)
        status = get_cache_status()
        assert status["is_expired"] is True
        assert status["should_use_cache"] is False


class TestGetCachedData:
    """测试从缓存获取数据。"""

    def test_no_cache(self, temp_cache):
        """无缓存时应返回has_cache=False。"""
        result = get_cached_data()
        assert result["has_cache"] is False
        assert result["data"] is None

    def test_stats_query(self, temp_cache, temp_db):
        """stats查询应返回统计数据。"""
        create_snapshot(db_path=temp_db)
        result = get_cached_data(query_type="stats")
        assert result["has_cache"] is True
        assert "data" in result
        assert "total" in result["data"]
        assert result["data"]["total"] == 2
        assert result["data"]["negative"] == 1
        assert result["data"]["positive"] == 1
        assert result["data"]["high_risk"] == 1

    def test_notes_query(self, temp_cache, temp_db):
        """notes查询应返回笔记列表。"""
        create_snapshot(db_path=temp_db)
        result = get_cached_data(query_type="notes", limit=10)
        assert result["has_cache"] is True
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 2

    def test_notes_query_with_limit(self, temp_cache, temp_db):
        """limit参数应生效。"""
        create_snapshot(db_path=temp_db)
        result = get_cached_data(query_type="notes", limit=1)
        assert len(result["data"]) == 1

    def test_cached_data_has_warning(self, temp_cache, temp_db):
        """缓存数据应包含警告信息。"""
        create_snapshot(db_path=temp_db)
        result = get_cached_data(query_type="stats")
        assert "warning" in result
        assert "缓存" in result["warning"]


class TestListSnapshots:
    """测试列出快照。"""

    def test_empty_list(self, temp_cache):
        assert list_snapshots() == []

    def test_list_after_create(self, temp_cache, temp_db):
        create_snapshot(db_path=temp_db)
        snaps = list_snapshots()
        assert len(snaps) == 1


class TestDeleteSnapshot:
    """测试删除快照。"""

    def test_delete_existing(self, temp_cache, temp_db):
        """删除存在的快照应成功。"""
        create_snapshot(db_path=temp_db)
        snaps = list_snapshots()
        snap_id = snaps[0]["id"]
        result = delete_snapshot(snap_id)
        assert result["success"] is True
        assert result["deleted"] == snap_id
        assert len(list_snapshots()) == 0

    def test_delete_nonexistent(self, temp_cache):
        """删除不存在的快照不应报错。"""
        result = delete_snapshot("nonexistent_id")
        assert result["success"] is True

    def test_delete_updates_current(self, temp_cache, temp_db):
        """删除当前快照后current应更新。"""
        # 快照ID精度到秒，需间隔1秒以上确保ID不同
        create_snapshot(db_path=temp_db)
        time.sleep(1.1)
        create_snapshot(db_path=temp_db)
        meta = _load_meta()
        assert len(meta["snapshots"]) == 2  # 确认两个不同ID
        current_id = meta["current"]
        delete_snapshot(current_id)
        meta = _load_meta()
        assert meta["current"] != current_id
        assert meta["current"] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

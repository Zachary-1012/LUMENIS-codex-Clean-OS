# -*- coding: utf-8 -*-
"""
tests/test_learning_persistence.py — ZBC 学习数据持久化模块测试
覆盖：初始化 / 禁用回退 / 保存加载 / 备份恢复 / 集合校验 / 状态查询 / StorageAdapter 契约
"""

import json
import os
import tempfile

import pytest

import learning_persistence as lp


@pytest.fixture(autouse=True)
def reset():
    """每个测试前重置单例，隔离状态。"""
    lp._reset_for_testing()
    yield
    lp._reset_for_testing()


@pytest.fixture()
def data_dir(tmp_path):
    return str(tmp_path / "learning")


class TestInit:
    def test_enabled_mode_creates_dir(self, data_dir):
        r = lp.init(data_dir=data_dir, enabled=True)
        assert r["ok"] is True
        assert r["enabled"] is True
        assert os.path.isdir(data_dir)
        assert lp.is_initialized() is True
        assert lp.is_enabled() is True

    def test_disabled_mode_no_dir(self, data_dir):
        r = lp.init(data_dir=data_dir, enabled=False)
        assert r["ok"] is True
        assert r["enabled"] is False
        assert not os.path.exists(os.path.join(data_dir, "cases.json"))
        assert lp.is_initialized() is True
        assert lp.is_enabled() is False

    def test_reinit_idempotent(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        r2 = lp.init(data_dir=data_dir, enabled=True)
        assert r2["ok"] is True

    def test_creates_gitignore(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        gi = os.path.join(data_dir, ".gitignore")
        assert os.path.exists(gi)
        with open(gi, encoding="utf-8") as f:
            assert "*" in f.read()


class TestSaveLoad:
    def test_round_trip(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        data = {"case1": {"id": 1, "lesson": "测试持久化"}}
        r = lp.save_collection("cases", data, immediate=True)
        assert r["ok"] is True
        assert lp.load_collection("cases") == data

    def test_immediate_write_file(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        lp.save_collection("lessons", {"l1": {"text": "lesson"}}, immediate=True)
        assert os.path.exists(os.path.join(data_dir, "lessons.json"))

    def test_unknown_collection(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        r = lp.save_collection("nope", {}, immediate=True)
        assert r["ok"] is False
        assert r["error"] == "UNKNOWN_COLLECTION"

    def test_load_missing_returns_none(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        assert lp.load_collection("patterns") is None

    def test_disabled_save_skipped(self):
        lp.init(enabled=False)
        r = lp.save_collection("cases", {}, immediate=True)
        assert r["ok"] is True
        assert r.get("skipped") is True


class TestBackup:
    def test_auto_backup_old_file(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        lp.save_collection("cases", {"v1": True}, immediate=True)
        lp.save_collection("cases", {"v2": True}, immediate=True)
        backups = [f for f in os.listdir(data_dir) if f.startswith("cases.backup.") and f.endswith(".json")]
        assert len(backups) >= 1

    def test_recover_from_corruption(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        lp.save_collection("cases", {"valid": "data"}, immediate=True)
        lp.save_collection("cases", {"valid": "data-v2"}, immediate=True)
        # 写坏主文件
        with open(os.path.join(data_dir, "cases.json"), "w", encoding="utf-8") as f:
            f.write("{invalid json")
        loaded = lp.load_collection("cases")
        assert loaded is not None
        # 两次保存仅 1 个备份（第一次无旧文件），恢复出第一次内容
        assert loaded == {"valid": "data"}

    def test_backup_count_limit(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True, backup_count=2)
        for i in range(5):
            lp.save_collection("cases", {"v": i}, immediate=True)
        backups = [f for f in os.listdir(data_dir) if f.startswith("cases.backup.") and f.endswith(".json")]
        assert len(backups) <= 2


class TestStatusImportExport:
    def test_get_status(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        s = lp.get_status()
        assert s["initialized"] is True
        assert s["enabled"] is True
        assert s["storage_type"] == "json-file"
        assert "cases" in s["collections"]
        assert "bundles" in s["collections"]

    def test_export_format(self):
        r = lp.export_collection("cases")
        assert r["ok"] is True
        assert r["format"] == "json"

    def test_import_write(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        r = lp.import_collection("patterns", {"p1": {"name": "pattern"}})
        assert r["ok"] is True
        assert lp.load_collection("patterns") == {"p1": {"name": "pattern"}}

    def test_import_unknown(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        r = lp.import_collection("nope", {})
        assert r["ok"] is False


class TestCollectionsAdapter:
    def test_get_collection_names(self):
        names = lp.get_collection_names()
        for expected in ["cases", "lessons", "shadow_analyses", "evidences", "knowledge"]:
            assert expected in names

    def test_storage_adapter_contract(self):
        # 从模块暴露的契约校验
        for m in ["init", "save", "load", "delete", "query", "get_status"]:
            assert m in lp.STORAGE_ADAPTER["methods"]

    def test_reset_for_testing(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        assert lp.is_initialized() is True
        lp._reset_for_testing()
        assert lp.is_initialized() is False

    def test_json_content_valid(self, data_dir):
        lp.init(data_dir=data_dir, enabled=True)
        lp.save_collection("knowledge", {"k1": {"title": "知识"}}, immediate=True)
        with open(os.path.join(data_dir, "knowledge.json"), encoding="utf-8") as f:
            parsed = json.load(f)
        assert parsed == {"k1": {"title": "知识"}}

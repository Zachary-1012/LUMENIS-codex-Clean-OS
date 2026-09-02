# -*- coding: utf-8 -*-
"""
T-P1-3 Alembic 可回滚 DB 迁移 —— 回归测试
在隔离的自建 mini 库上验证 stamp baseline / upgrade / downgrade 全链路。
迁移脚本写入仓库 alembic/versions/（与真实使用一致），测试结束清理，绝不残留。
关键隔离点：清除其他测试（如 test_workspace_keys 模块级设置）泄漏的 ZBC_DB_PATH，
避免 alembic env.py 误连到别的库。不触碰生产库 data/monitor.db。
"""
import os
import sqlite3
import pytest

from alembic.config import Config
from alembic import command

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)
INI = os.path.join(REPO_DIR, "alembic.ini")
VERSIONS_DIR = os.path.join(REPO_DIR, "alembic", "versions")
BASELINE_REV = "e4278c4d1d79"
_MIG_FILE = "zz_test_rollback.py"


def _make_mini_db(db_path: str) -> str:
    if os.path.exists(db_path):
        os.remove(db_path)
    c = sqlite3.connect(db_path)
    c.executescript(
        """
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT,
            title TEXT,
            content TEXT,
            captured_at TEXT,
            publish_datetime TEXT
        );
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_key TEXT,
            title TEXT
        );
        INSERT INTO notes (note_id, title) VALUES ('n1', 't1'), ('n2', 't2');
        """
    )
    c.commit()
    c.close()
    return db_path


def _cfg(db_path: str) -> Config:
    # 隔离：全量加载时其他测试可能设置 ZBC_DB_PATH（模块级、未清理），必须清除，
    # 否则 alembic/env.py 会用它覆盖 sqlalchemy.url 误连到别的库。
    os.environ.pop("ZBC_DB_PATH", None)
    os.chdir(REPO_DIR)
    cfg = Config(INI)
    cfg.set_main_option(
        "sqlalchemy.url",
        "sqlite:///" + os.path.abspath(db_path).replace("\\", "/"),
    )
    return cfg


def _tables(db_path: str):
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    c.close()
    return rows


def _version(db_path: str):
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = [r[0] for r in c.execute("SELECT version_num FROM alembic_version")]
    except Exception:
        rows = []
    c.close()
    return rows


def _cleanup_zz():
    p = os.path.join(VERSIONS_DIR, _MIG_FILE)
    if os.path.exists(p):
        os.remove(p)


def test_stamp_baseline_writes_version(tmp_path):
    _cleanup_zz()
    db = _make_mini_db(str(tmp_path / "t.db"))
    cfg = _cfg(db)
    command.stamp(cfg, BASELINE_REV)
    ver = _version(db)
    assert ver == [BASELINE_REV], (
        "stamp 后 alembic_version 应记录 baseline（曾因 reflection 配置失败）")
    tables = _tables(db)
    assert "notes" in tables and "events" in tables
    assert "alembic_version" in tables


def test_upgrade_then_downgrade_rollback(tmp_path):
    _cleanup_zz()
    db = _make_mini_db(str(tmp_path / "t2.db"))
    cfg = _cfg(db)
    command.stamp(cfg, BASELINE_REV)
    before = sqlite3.connect(f"file:{db}?mode=ro", uri=True).execute(
        "SELECT count(*) FROM notes").fetchone()[0]
    assert before == 2

    mig_path = os.path.join(VERSIONS_DIR, _MIG_FILE)
    mig_src = (
        '"""zz test rollback"""\n'
        "from alembic import op\n"
        "import sqlalchemy as sa\n"
        "revision = 'zztest0001'\n"
        "down_revision = '" + BASELINE_REV + "'\n"
        "branch_labels = None\n"
        "depends_on = None\n"
        "def upgrade() -> None:\n"
        "    op.add_column('notes', sa.Column('zz_test_col', sa.String(length=32), nullable=True))\n"
        "def downgrade() -> None:\n"
        "    op.drop_column('notes', 'zz_test_col')\n"
    )
    with open(mig_path, "w", encoding="utf-8") as fh:
        fh.write(mig_src)
    try:
        command.upgrade(cfg, "head")
        cols = [r[1] for r in sqlite3.connect(
            f"file:{db}?mode=ro", uri=True).execute("PRAGMA table_info(notes)")]
        assert "zz_test_col" in cols
        assert _version(db) == ["zztest0001"]

        command.downgrade(cfg, "-1")
        cols = [r[1] for r in sqlite3.connect(
            f"file:{db}?mode=ro", uri=True).execute("PRAGMA table_info(notes)")]
        assert "zz_test_col" not in cols
        assert _version(db) == [BASELINE_REV]
    finally:
        _cleanup_zz()

    after = sqlite3.connect(f"file:{db}?mode=ro", uri=True).execute(
        "SELECT count(*) FROM notes").fetchone()[0]
    assert before == after, "回滚后数据行数必须不变"

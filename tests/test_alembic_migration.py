# -*- coding: utf-8 -*-
"""
T-P1-3 Alembic 可回滚 DB 迁移 —— 回归测试
在隔离的自建 mini 库上验证 stamp baseline / upgrade / downgrade 全链路。
迁移脚本写入仓库 alembic/versions/（与真实使用一致），测试结束清理，绝不残留。
关键隔离点：清除其他测试（如 test_workspace_keys 模块级设置）泄漏的 ZBC_DB_PATH，
避免 alembic env.py 误连到别的库。不触碰生产库 data/monitor.db。
"""
import os
import shutil
import sqlite3
from contextlib import closing
import pytest

from alembic.config import Config
from alembic import command

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)
INI = os.path.join(REPO_DIR, "alembic.ini")
BASELINE_REV = "e4278c4d1d79"
_MIG_FILE = "zz_test_rollback.py"


@pytest.fixture(autouse=True)
def _restore_cwd():
    """_cfg() 内 os.chdir(REPO_DIR) 改变进程 CWD 且不还原，会污染后续测试的相对路径解析；
    每个用例后强制还原。"""
    _old_cwd = os.getcwd()
    _old_db_path = os.environ.get("ZBC_DB_PATH")
    try:
        yield
    finally:
        os.chdir(_old_cwd)
        if _old_db_path is None:
            os.environ.pop("ZBC_DB_PATH", None)
        else:
            os.environ["ZBC_DB_PATH"] = _old_db_path


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


def _cfg(db_path: str, script_location: str) -> Config:
    # Alembic env.py honors the canonical DB environment first. Point it at the
    # same disposable mini DB; deleting the variable would silently fall back to
    # the repository database and create test artifacts there.
    os.environ["ZBC_DB_PATH"] = os.path.abspath(db_path)
    os.chdir(REPO_DIR)
    cfg = Config(INI)
    # Every test gets its own Alembic script directory. Writing temporary
    # revisions into the repository's shared versions/ directory races with
    # parallel pytest workers and can leave a duplicate revision behind after
    # interruption, making the whole suite fail with multiple Alembic heads.
    cfg.set_main_option("script_location", os.path.abspath(script_location))
    cfg.set_main_option(
        "sqlalchemy.url",
        "sqlite:///" + os.path.abspath(db_path).replace("\\", "/"),
    )
    return cfg


def _copy_migrations(destination: str) -> str:
    """Copy the real Alembic environment/history into an isolated test tree."""
    source = os.path.join(REPO_DIR, "alembic")
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return destination


def _tables(db_path: str):
    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
        return [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]


def _version(db_path: str):
    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
        try:
            return [r[0] for r in conn.execute(
                "SELECT version_num FROM alembic_version")]
        except sqlite3.OperationalError:
            return []


def _columns(db_path: str, table: str):
    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def test_stamp_baseline_writes_version(tmp_path):
    db = _make_mini_db(str(tmp_path / "t.db"))
    script_location = _copy_migrations(str(tmp_path / "alembic"))
    cfg = _cfg(db, script_location)
    command.stamp(cfg, BASELINE_REV)
    ver = _version(db)
    assert ver == [BASELINE_REV], (
        "stamp 后 alembic_version 应记录 baseline（曾因 reflection 配置失败）")
    tables = _tables(db)
    assert "notes" in tables and "events" in tables
    assert "alembic_version" in tables


def test_upgrade_then_downgrade_rollback(tmp_path):
    db = _make_mini_db(str(tmp_path / "t2.db"))
    script_location = _copy_migrations(str(tmp_path / "alembic"))
    cfg = _cfg(db, script_location)
    command.stamp(cfg, BASELINE_REV)
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
        before = conn.execute("SELECT count(*) FROM notes").fetchone()[0]
    assert before == 2

    mig_path = os.path.join(script_location, "versions", _MIG_FILE)
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
    command.upgrade(cfg, "head")
    cols = _columns(db, "notes")
    assert "zz_test_col" in cols
    assert _version(db) == ["zztest0001"]

    command.downgrade(cfg, "-1")
    cols = _columns(db, "notes")
    assert "zz_test_col" not in cols
    assert _version(db) == [BASELINE_REV]

    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
        after = conn.execute("SELECT count(*) FROM notes").fetchone()[0]
    assert before == after, "回滚后数据行数必须不变"

# -*- coding: utf-8 -*-
"""T-P0A-2 scripts/backup_db.py 备份完整性校验规范单测。

- backup API 在线一致性备份 + quick_check 校验
- 校验失败时删除不可用备份（不产生假备份）
- 锁定类异常才 fallback 文件拷贝（WAL 下拷贝可能不一致）
"""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import backup_db  # noqa: E402


def _make_db(path, tables=None):
    """建一个含核心表的测试库。"""
    con = sqlite3.connect(path)
    for tbl in (tables or ['notes', 'events', 'daily_reports', 'collection_logs', 'metric_snapshots']):
        con.execute(f'CREATE TABLE {tbl} (id INTEGER PRIMARY KEY, v TEXT)')
    con.commit()
    con.close()


def test_verify_backup_ok(tmp_path):
    src = str(tmp_path / 'src.db')
    _make_db(src)
    dst = str(tmp_path / 'dst.db')
    s = sqlite3.connect(src)
    d = sqlite3.connect(dst)
    s.backup(d)
    s.close()
    d.close()
    v = backup_db.verify_backup(dst)
    assert v['ok'] is True
    assert v['tables'] == 5
    assert v['missing'] == []


def test_verify_backup_missing_table(tmp_path):
    src = str(tmp_path / 'src.db')
    _make_db(src, tables=['notes'])  # 缺核心表
    dst = str(tmp_path / 'dst.db')
    s = sqlite3.connect(src)
    d = sqlite3.connect(dst)
    s.backup(d)
    s.close()
    d.close()
    v = backup_db.verify_backup(dst)
    assert v['ok'] is False
    assert 'metric_snapshots' in v['missing']


def test_verify_backup_missing_file(tmp_path):
    v = backup_db.verify_backup(str(tmp_path / 'nope.db'))
    assert v['ok'] is False
    assert 'error' in v


def test_backup_database_produces_verified_backup(tmp_path, monkeypatch):
    """备份后应存在一份校验通过的真实备份。"""
    src = str(tmp_path / 'monitor.db')
    _make_db(src)
    monkeypatch.setattr(backup_db, 'DB_PATH', src)
    monkeypatch.setattr(backup_db, 'BACKUP_DIR', str(tmp_path / 'backups'))
    out = backup_db.backup_database('t1.db')
    assert out is not None
    assert os.path.exists(out)
    v = backup_db.verify_backup(out)
    assert v['ok'] is True


def test_backup_corrupt_source_no_fake_backup(tmp_path, monkeypatch):
    """源库损坏（无法读取）时，不得留下假备份。"""
    src = str(tmp_path / 'monitor.db')
    with open(src, 'w', encoding='utf-8') as f:
        f.write('not a real sqlite db at all ..........')
    monkeypatch.setattr(backup_db, 'DB_PATH', src)
    monkeypatch.setattr(backup_db, 'BACKUP_DIR', str(tmp_path / 'backups'))
    out = backup_db.backup_database('t2.db')
    # 可能返回 None 或产生一个校验失败的备份被删除
    if out is not None:
        assert not os.path.exists(out), '校验失败的备份应被删除'
    else:
        assert True

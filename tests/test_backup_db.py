# -*- coding: utf-8 -*-
"""Isolated contracts for the backup CLI adapter and business validation."""
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
    monkeypatch.setenv('ZBC_DB_PATH', src)
    out = backup_db.backup_database('t1.db')
    assert out is not None
    assert out == str(tmp_path / 'backups' / 't1.db')
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
    monkeypatch.setenv('ZBC_DB_PATH', src)
    out = backup_db.backup_database('t2.db')
    assert out is None
    assert not (tmp_path / 'backups' / 't2.db').exists()


def test_backup_uses_call_time_db_path(tmp_path, monkeypatch):
    stale = str(tmp_path / 'stale.db')
    current = str(tmp_path / 'current.db')
    with open(stale, 'w', encoding='utf-8') as f:
        f.write('not the current database')
    _make_db(current)

    # The compatibility constants remain for the untouched legacy restore
    # function, but backup source and destination come from the current owner.
    monkeypatch.setattr(backup_db, 'DB_PATH', stale)
    monkeypatch.setattr(backup_db, 'BACKUP_DIR', str(tmp_path / 'stale-backups'))
    monkeypatch.setenv('ZBC_DB_PATH', current)

    out = backup_db.backup_database('call-time.db')

    assert out == str(tmp_path / 'backups' / 'call-time.db')
    assert backup_db.verify_backup(out)['ok'] is True
    assert not (tmp_path / 'stale-backups' / 'call-time.db').exists()


def test_locked_backup_api_failure_never_falls_back_to_raw_copy(tmp_path, monkeypatch):
    src = str(tmp_path / 'monitor.db')
    _make_db(src)
    backup_dir = tmp_path / 'backups'
    monkeypatch.setattr(backup_db, 'DB_PATH', src)
    monkeypatch.setattr(backup_db, 'BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('ZBC_DB_PATH', src)

    def fail_locked(_backup_name=None):
        raise sqlite3.OperationalError('database is locked')

    monkeypatch.setattr(backup_db.migrations, 'backup_database', fail_locked)

    assert backup_db.backup_database('locked.db') is None
    assert not (backup_dir / 'locked.db').exists()

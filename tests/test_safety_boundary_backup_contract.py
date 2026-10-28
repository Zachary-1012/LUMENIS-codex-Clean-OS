"""Synthetic-only regression for the retained safety-boundary backup caller."""
import ast
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

import pytest


@pytest.fixture
def engine(tmp_path, monkeypatch):
    # Load the real class without constructing the module's process singleton.
    source = Path(__file__).resolve().parents[1] / 'safety_boundary.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    tree.body = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.ClassDef))]
    namespace = {'__file__': str(tmp_path / 'safety_boundary.py')}
    exec(compile(tree, str(source), 'exec'), namespace)
    instance = namespace['BoundaryControlEngine']()
    instance.test_operation_type = namespace['OperationType']
    monkeypatch.setenv('ZBC_DB_PATH', str(tmp_path / 'nondefault' / 'truth.sqlite'))
    return instance


@pytest.fixture
def wal_database(engine):
    from lumenis.shared.database.paths import main_db_path
    path = Path(main_db_path())
    path.parent.mkdir()
    source = sqlite3.connect(path)
    source.execute('PRAGMA journal_mode=WAL')
    source.execute('PRAGMA wal_autocheckpoint=0')
    source.execute('CREATE TABLE synthetic_evidence (value TEXT)')
    source.execute("INSERT INTO synthetic_evidence VALUES ('committed')")
    source.commit()
    yield source
    source.close()


def backup(engine):
    return engine.backup_before_operation(engine.test_operation_type.RESTART, 'synthetic restart')


def expire(path):
    info_path = Path(path) / 'backup_info.json'
    info = json.loads(info_path.read_text(encoding='utf-8'))
    info['created_at'] = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    info_path.write_text(json.dumps(info), encoding='utf-8')


def test_wal_nondefault_database_independent_readback(engine, wal_database):
    path = backup(engine)
    assert path
    with sqlite3.connect(Path(path) / 'monitor.db') as restored:
        assert restored.execute('SELECT value FROM synthetic_evidence').fetchall() == [('committed',)]
        assert restored.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    info = json.loads((Path(path) / 'backup_info.json').read_text(encoding='utf-8'))
    assert Path(info['source_db']).parts[-2:] == ('nondefault', 'truth.sqlite')
    assert info['operation_type'] == 'restart'
    assert info['restore_readback'] == 'verified'
    assert len(info['database_sha256']) == 64
    expected_companions = {
        name: engine.calculate_file_hash(Path(path) / name)
        for name in ('monitor.db.signing-manifest.json',
                     'monitor.db.evidence-signing.dpapi' if os.name == 'nt' else 'monitor.db.evidence-signing.json')
        if (Path(path) / name).is_file()
    }
    assert info['owned_companions'] == expected_companions
    assert 'monitor.db.signing-manifest.json' in expected_companions


def test_backup_destinations_unique(engine, wal_database):
    assert backup(engine) != backup(engine)


@pytest.mark.parametrize('failure', ['missing', 'io', 'disabled'])
def test_required_backup_failure_never_calls_operation(engine, monkeypatch, failure):
    from lumenis.shared.database import migrations
    if failure == 'io':
        def denied(*args):
            raise OSError('synthetic disk failure')
        monkeypatch.setattr(migrations, 'backup_database_to_path', denied)
    if failure == 'disabled':
        engine.backup_before_auto_fix = False
    calls = []
    result = engine.execute_with_boundary('restart', lambda: calls.append(1), 'synthetic')
    assert result['status'] == 'backup_failed'
    assert result['operation_executed'] is False
    assert calls == []


def test_safe_read_does_not_require_database(engine):
    assert engine.execute_with_boundary('read', lambda: 7, 'read')['result'] == 7


def test_successful_required_backup_then_operation(engine, wal_database):
    result = engine.execute_with_boundary('restart', lambda: 7, 'synthetic')
    assert result['status'] == 'success'
    assert result['result'] == 7
    assert Path(result['backup_path'], 'monitor.db').is_file()


def test_corrupt_owner_output_cannot_pass_readback(engine, monkeypatch):
    from lumenis.shared.database import migrations
    def corrupt(destination):
        Path(destination).write_bytes(b'not sqlite')
    monkeypatch.setattr(migrations, 'backup_database_to_path', corrupt)
    calls = []
    result = engine.execute_with_boundary('restart', lambda: calls.append(1), 'synthetic')
    assert result['status'] == 'backup_failed'
    assert not calls


def test_retention_removes_only_expired_owned_backup(engine, wal_database):
    old = backup(engine)
    expire(old)
    fresh = backup(engine)
    # Backup itself must never initiate cleanup.
    assert Path(old).exists()
    result = engine._cleanup_old_backups(str(Path(old).parent))
    assert result['status'] == 'ok'
    assert not Path(old).exists()
    assert Path(fresh).exists()
    assert result['removed'] == [Path(old).name]


@pytest.mark.parametrize('kind', ['owner', 'path', 'legacy', 'foreign_file', 'hash', 'symlink_file',
                                  'signing_companion', 'unrecorded_signing_companion'])
def test_retention_preserves_unowned_or_changed_material(engine, wal_database, kind):
    path = Path(backup(engine))
    expire(path)
    info_path = path / 'backup_info.json'
    info = json.loads(info_path.read_text(encoding='utf-8'))
    if kind == 'owner':
        info['owner'] = 'another_owner'
    elif kind == 'path':
        info['backup_path'] = str(path.parent / 'other')
    elif kind == 'legacy':
        info.pop('owner')
    elif kind == 'hash':
        info['database_sha256'] = 'wrong'
    elif kind == 'foreign_file':
        (path / 'user-document.txt').write_text('preserve')
    elif kind == 'symlink_file':
        (path / '.env').symlink_to(path / 'monitor.db')
    elif kind == 'signing_companion':
        (path / 'monitor.db.signing-manifest.json').write_text('changed', encoding='utf-8')
    elif kind == 'unrecorded_signing_companion':
        info.pop('owned_companions')
    info_path.write_text(json.dumps(info), encoding='utf-8')
    result = engine._cleanup_old_backups(str(path.parent))
    assert path.exists()
    assert not result['removed']


def test_bad_metadata_reports_failure_but_does_not_hide_other_cleanup(engine, wal_database):
    bad = Path(backup(engine))
    (bad / 'backup_info.json').write_text('{')
    old = Path(backup(engine))
    expire(old)
    result = engine._cleanup_old_backups(str(old.parent))
    assert result['status'] == 'partial_failure'
    assert result['errors'][0]['entry'] == bad.name
    assert bad.exists() and not old.exists()


def test_symlink_directory_and_metadata_preserved(engine, wal_database, tmp_path):
    path = Path(backup(engine))
    expire(path)
    outside = tmp_path / 'outside'
    path.rename(outside)
    path.symlink_to(outside, target_is_directory=True)
    assert engine._cleanup_old_backups(str(path.parent))['removed'] == []
    assert outside.is_dir()
    path.unlink()
    outside.rename(path)
    metadata = path / 'backup_info.json'
    moved = tmp_path / 'metadata.json'
    metadata.rename(moved)
    metadata.symlink_to(moved)
    assert engine._cleanup_old_backups(str(path.parent))['removed'] == []
    assert path.is_dir()


def test_cleanup_unowned_root_rejected(engine, tmp_path):
    result = engine._cleanup_old_backups(str(tmp_path / 'other'))
    assert result['status'] == 'failed'


def test_cleanup_io_failure_reported(engine, wal_database, monkeypatch):
    path = Path(backup(engine))
    expire(path)
    def fail(*args):
        raise OSError('synthetic denied deletion')
    monkeypatch.setattr(engine._cleanup_old_backups.__globals__['shutil'], 'rmtree', fail)
    result = engine._cleanup_old_backups(str(path.parent))
    assert result['status'] == 'partial_failure'
    assert path.exists()


def test_symlink_backup_root_rejected(engine, wal_database, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / 'data' / 'backups').symlink_to(outside, target_is_directory=True)
    assert backup(engine) is None
    assert list(outside.iterdir()) == []


def test_existing_confirmation_boundary_unchanged(engine):
    calls = []
    result = engine.execute_with_boundary('data_delete', lambda: calls.append(1), 'synthetic')
    assert result['status'] == 'need_confirmation'
    assert calls == []


def test_invalid_timestamp_is_reported_not_removed(engine, wal_database):
    path = Path(backup(engine))
    info_path = path / 'backup_info.json'
    info = json.loads(info_path.read_text(encoding='utf-8'))
    info['created_at'] = 'invalid'
    info_path.write_text(json.dumps(info), encoding='utf-8')
    result = engine._cleanup_old_backups(str(path.parent))
    assert result['status'] == 'partial_failure'
    assert path.exists()


def test_config_copy_failure_blocks_operation(engine, wal_database, monkeypatch):
    (Path(engine.root_dir) / '.env').write_text('SYNTHETIC_TEST_SETTING=true\n')
    def denied(*args):
        raise OSError('synthetic config copy failure')
    monkeypatch.setattr(engine.backup_before_operation.__globals__['shutil'], 'copy2', denied)
    calls = []
    result = engine.execute_with_boundary('restart', lambda: calls.append(1), 'synthetic')
    assert result['status'] == 'backup_failed'
    assert not calls


def test_negative_retention_rejected(engine, wal_database):
    path = Path(backup(engine))
    engine.backup_retention_days = -1
    assert engine._cleanup_old_backups(str(path.parent))['status'] == 'failed'
    assert path.exists()


def test_config_copy_preserves_synthetic_contents(engine, wal_database):
    config = 'SYNTHETIC_TEST_SETTING=true\n'
    (Path(engine.root_dir) / '.env').write_text(config)
    path = backup(engine)
    assert path
    assert (Path(path) / '.env').read_text(encoding='utf-8') == config


def test_config_symlink_rejected(engine, wal_database, tmp_path):
    outside = tmp_path / 'synthetic-config'
    outside.write_text('SYNTHETIC_TEST_SETTING=true\n')
    (Path(engine.root_dir) / '.env').symlink_to(outside)
    calls = []
    result = engine.execute_with_boundary('restart', lambda: calls.append(1), 'synthetic')
    assert result['status'] == 'backup_failed'
    assert not calls


def test_snapshot_readback_uses_shared_connection_without_sidecars(engine, wal_database, monkeypatch):
    from lumenis.shared.database import connection
    real_connect = connection.connect_sqlite
    calls = []
    def tracked(*args, **kwargs):
        calls.append((args, kwargs))
        return real_connect(*args, **kwargs)
    monkeypatch.setattr(connection, 'connect_sqlite', tracked)
    path = backup(engine)
    assert path
    assert calls[0][0] == (str(Path(path) / 'monitor.db'),)
    assert calls[0][1]['read_only'] is True
    assert calls[0][1]['immutable'] is True
    assert not Path(path, 'monitor.db-wal').exists()
    assert not Path(path, 'monitor.db-shm').exists()


@pytest.mark.parametrize('kind', ['writable', 'implicit', 'canonical', 'canonical_link', 'sidecar'])
def test_shared_connection_rejects_unsafe_immutable_usage(engine, wal_database, tmp_path, kind):
    from lumenis.shared.database.connection import connect_sqlite
    from lumenis.shared.database.paths import main_db_path
    target = tmp_path / 'snapshot.sqlite'
    read_only = True
    if kind == 'writable':
        read_only = False
    elif kind == 'implicit':
        target = None
    elif kind == 'canonical':
        target = main_db_path()
    elif kind == 'canonical_link':
        target.symlink_to(main_db_path())
    elif kind == 'sidecar':
        Path(str(target) + '-wal').write_bytes(b'synthetic')
    with pytest.raises(ValueError):
        connect_sqlite(target, read_only=read_only, immutable=True)


@pytest.mark.parametrize('kind', ['symlink', 'parent_symlink', 'hardlink'])
def test_immutable_rejects_noncanonical_live_wal_alias(engine, wal_database, tmp_path, kind):
    import os
    from lumenis.shared.database.connection import connect_sqlite
    live_dir = tmp_path / 'operational'
    live_dir.mkdir()
    live = live_dir / 'live.sqlite'
    writer = sqlite3.connect(live)
    try:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('CREATE TABLE synthetic_live (value)')
        writer.execute('INSERT INTO synthetic_live VALUES (1)')
        writer.commit()
        alias = tmp_path / 'alias.sqlite'
        if kind == 'symlink':
            alias.symlink_to(live)
        elif kind == 'parent_symlink':
            alias_dir = tmp_path / 'alias-directory'
            alias_dir.symlink_to(live_dir, target_is_directory=True)
            alias = alias_dir / 'live.sqlite'
        else:
            os.link(live, alias)
        with pytest.raises(ValueError):
            connect_sqlite(alias, read_only=True, immutable=True)
        assert writer.execute('SELECT * FROM synthetic_live').fetchall() == [(1,)]
    finally:
        writer.close()

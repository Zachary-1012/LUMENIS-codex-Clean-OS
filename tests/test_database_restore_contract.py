"""Isolated restore operations preserve original signatures and existing targets."""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from lumenis.shared.database import migrations
from lumenis.shared.evidence import signing_config
from scripts import backup_db
from tests import test_database_backup_signing_contract as fixtures

signed_workspace = fixtures.signed_workspace
keyless_workspace = fixtures.keyless_workspace


def _backup(ws):
    ws['destination'] = ws['root'] / 'backups' / 'snapshot.db'
    migrations.backup_database_to_path(ws['destination'])
    return Path(str(ws['destination']) + '.signing-manifest.json')


def test_cli_restores_call_time_backup_into_new_directory_without_touching_live_source(signed_workspace, tmp_path, monkeypatch, capsys):
    ws = signed_workspace
    _backup(ws)
    before, environment = ws['db'].read_bytes(), {name: os.environ[name] for name in ws['loaded']}
    monkeypatch.setattr(backup_db, 'DB_PATH', str(tmp_path / 'wrong-production.db'))
    monkeypatch.setattr(backup_db, 'BACKUP_DIR', str(tmp_path / 'wrong-backups'))
    destination = tmp_path / 'verified-restoration'
    assert backup_db.main(['restore', 'snapshot.db', '--target-directory', str(destination)]) == 0
    assert (destination / 'monitor.db').read_bytes() == ws['destination'].read_bytes()
    assert (destination / 'restore-verification.json').is_file()
    assert ws['db'].read_bytes() == before
    assert environment == {name: os.environ[name] for name in ws['loaded']}
    assert not (tmp_path / 'wrong-production.db').exists()
    output = capsys.readouterr().out
    for secret in json.loads(ws['loaded']['LUMENIS_EVIDENCE_HMAC_KEY_RING']).values():
        assert secret not in output


def test_cli_online_restore_is_rejected_without_creating_before_restore_or_writing_source(signed_workspace, capsys):
    ws = signed_workspace
    _backup(ws)
    before = ws['db'].read_bytes()
    assert backup_db.main(['restore', 'snapshot.db']) == 1
    assert 'RESTORE_ONLINE_OVERWRITE_DENIED' in capsys.readouterr().out
    assert ws['db'].read_bytes() == before
    assert not (ws['root'] / 'backups' / 'before_restore.db').exists()


def test_direct_cli_process_completes_isolated_native_restoration(signed_workspace, tmp_path):
    ws = signed_workspace
    _backup(ws)
    before = ws['db'].read_bytes()
    env = os.environ.copy()
    for name in ws['loaded']:
        env.pop(name, None)
    destination = tmp_path / 'restored-by-cli-process'
    result = subprocess.run([sys.executable, 'scripts/backup_db.py', 'restore', 'snapshot.db',
        '--target-directory', str(destination)], env=env, check=True, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0
    assert (destination / 'monitor.db').read_bytes() == ws['destination'].read_bytes()
    assert ws['db'].read_bytes() == before
    assert json.loads((destination / 'restore-verification.json').read_text())['signed_evidence_rows'] == 1


@pytest.mark.parametrize('name', ['../outside.db', '..\\outside.db', '/absolute.db', 'nested/name.db'])
def test_cli_does_not_escape_call_time_backup_directory(signed_workspace, tmp_path, name):
    assert backup_db.restore_database(name, target_directory=tmp_path / 'restored') is False
    assert not (tmp_path / 'restored').exists()


@pytest.mark.parametrize('kind', ['empty_directory', 'file', 'contents', 'wal'])
def test_existing_restore_target_remains_byte_exact(signed_workspace, tmp_path, kind):
    ws = signed_workspace
    _backup(ws)
    destination = tmp_path / 'existing-target'
    if kind == 'file':
        destination.write_bytes(b'existing-user-file')
    else:
        destination.mkdir()
        if kind != 'empty_directory':
            (destination / ('monitor.db-wal' if kind == 'wal' else 'user-original.docx')).write_bytes(b'preserve-user-work')
    before = {path.name: path.read_bytes() for path in destination.iterdir()} if destination.is_dir() else destination.read_bytes()
    with pytest.raises(FileExistsError):
        migrations.restore_database_to_directory(ws['destination'], destination)
    after = {path.name: path.read_bytes() for path in destination.iterdir()} if destination.is_dir() else destination.read_bytes()
    assert after == before


@pytest.mark.parametrize('mutation', ['database_hash', 'blob_hash', 'relative_path', 'reserved_path', 'active_id', 'required_ids', 'row_count', 'duplicate_key'])
def test_restore_manifest_mismatch_never_publishes(signed_workspace, tmp_path, mutation):
    ws = signed_workspace
    path = _backup(ws)
    value = json.loads(path.read_text())
    if mutation == 'database_hash':
        value['database']['sha256'] = '0' * 64
    elif mutation == 'blob_hash':
        value['signing']['sha256'] = '0' * 64
    elif mutation == 'relative_path':
        value['database']['restore_relative_path'] = '../outside.db'
    elif mutation == 'reserved_path':
        value['database']['restore_relative_path'] = 'NUL.db'
    elif mutation == 'active_id':
        value['signing']['active_key_id'] = 'other-key'
    elif mutation == 'required_ids':
        value['signing']['required_key_ids'] = []
    elif mutation == 'row_count':
        value['verification']['signed_evidence_rows'] += 1
    path.write_text(json.dumps(value))
    if mutation == 'duplicate_key':
        path.write_text(path.read_text().replace('"schema":', '"schema":"duplicate", "schema":'))
    with pytest.raises(ValueError):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()
    assert not list(tmp_path.glob('.restored.restore-*'))
    assert not (tmp_path / 'outside.db').exists()


@pytest.mark.parametrize('mutation', ['evidence', 'same_id_wrong_key', 'protected_blob'])
def test_self_consistent_hashes_cannot_replace_real_signature_validation(signed_workspace, tmp_path, mutation):
    ws = signed_workspace
    path = _backup(ws)
    manifest = json.loads(path.read_text())
    blob = ws['destination'].parent / manifest['signing']['name']
    keys = json.loads(ws['loaded']['LUMENIS_EVIDENCE_HMAC_KEY_RING'])
    if mutation == 'evidence':
        with closing(sqlite3.connect(ws['destination'])) as con:
            con.execute("UPDATE app_evidence_records SET source='tampered-restore-source'")
            con.commit()
        manifest['database']['sha256'] = hashlib.sha256(ws['destination'].read_bytes()).hexdigest()
    else:
        raw = blob.read_bytes()
        if mutation == 'same_id_wrong_key':
            value = json.loads(signing_config._dpapi(raw, decrypt=True) if os.name == 'nt' else raw)
            value['keys'][value['active_id']] = 'x' * 48
            keys = value['keys']
            raw = json.dumps(value).encode()
            raw = signing_config._dpapi(raw, decrypt=False) if os.name == 'nt' else raw
        else:
            raw = b'corrupted-protection-test'
        blob.write_bytes(raw)
        manifest['signing']['sha256'] = hashlib.sha256(raw).hexdigest()
    manifest['integrity']['digest'] = migrations._backup_manifest_digest(manifest, keys[manifest['signing']['active_key_id']])
    path.write_text(json.dumps(manifest))
    expected = 'SIGNATURE_INVALID' if mutation in {'evidence', 'same_id_wrong_key'} else 'KEY_UNREADABLE'
    with pytest.raises(ValueError, match=expected):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()


def test_deleted_evidence_and_rewritten_public_hashes_cannot_downgrade_signed_backup(signed_workspace, tmp_path):
    ws = signed_workspace
    path = _backup(ws)
    value = json.loads(path.read_text())
    with closing(sqlite3.connect(ws['destination'])) as con:
        con.execute('DELETE FROM app_evidence_records')
        con.commit()
    value['database']['sha256'] = hashlib.sha256(ws['destination'].read_bytes()).hexdigest()
    value['signing']['required_key_ids'] = []
    value['verification'].update(signed_evidence_rows=0, evidence_signatures='NO_SIGNED_EVIDENCE_ROWS')
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='MANIFEST_AUTHENTICATION_FAILED'):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()


@pytest.mark.parametrize('sidecar', ['-wal', '-shm', '-journal'])
def test_live_source_backup_sidecars_are_refused(signed_workspace, tmp_path, sidecar):
    ws = signed_workspace
    _backup(ws)
    extra = Path(str(ws['destination']) + sidecar)
    extra.write_bytes(b'active-or-unknown-sqlite-state')
    with pytest.raises(ValueError):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored')
    assert extra.read_bytes() == b'active-or-unknown-sqlite-state'
    assert not (tmp_path / 'restored').exists()


def test_new_directory_publication_preserves_concurrent_empty_directory(signed_workspace, tmp_path, monkeypatch):
    ws = signed_workspace
    _backup(ws)
    destination = tmp_path / 'restored'
    original = migrations._publish_restore_directory
    winner = []
    def publish(staging, target):
        target.mkdir()
        winner.append(target.stat().st_ino)
        original(staging, target)
    monkeypatch.setattr(migrations, '_publish_restore_directory', publish)
    with pytest.raises(FileExistsError):
        migrations.restore_database_to_directory(ws['destination'], destination)
    assert destination.stat().st_ino == winner[0]
    assert list(destination.iterdir()) == []
    assert not list(tmp_path.glob('.restored.restore-*'))


def test_failed_publication_never_leaves_partial_target(signed_workspace, tmp_path, monkeypatch):
    ws = signed_workspace
    _backup(ws)
    def denied(*args):
        raise OSError('isolated publication failure')
    monkeypatch.setattr(migrations, '_publish_restore_directory', denied)
    with pytest.raises(OSError):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()
    assert not list(tmp_path.glob('.restored.restore-*'))


@pytest.mark.parametrize('signed_workspace', ['nested/custom.sqlite3'], indirect=True)
def test_restore_retains_original_nested_database_binding(signed_workspace, tmp_path):
    ws = signed_workspace
    _backup(ws)
    result = migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored')
    assert result['database_path'] == str(tmp_path / 'restored' / 'nested' / 'custom.sqlite3')
    assert Path(result['database_path']).read_bytes() == ws['destination'].read_bytes()


def test_missing_manifest_is_an_unverified_backup_not_an_unsigned_restore_fallback(signed_workspace, tmp_path):
    ws = signed_workspace
    manifest = _backup(ws)
    manifest.unlink()
    with pytest.raises(ValueError, match='MANIFEST_INVALID_OR_MISSING'):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()


@pytest.mark.parametrize('keyless_workspace', ['no_evidence_table', 'empty_evidence', 'unsigned_evidence'], indirect=True)
def test_keyless_backup_restore_reads_exact_work_without_signer_or_environment_changes(keyless_workspace, tmp_path, monkeypatch):
    ws = keyless_workspace
    before = ws['db'].read_bytes()
    environment = {name: value for name, value in os.environ.items() if name.startswith('LUMENIS_EVIDENCE_HMAC_')}
    monkeypatch.setattr(signing_config, 'activate_workspace_signing', lambda *a, **k: pytest.fail('Keyless restore cannot activate a signer'))
    migrations.backup_database_to_path(ws['destination'])
    restored = tmp_path / 'restored-keyless'
    result = migrations.restore_database_to_directory(ws['destination'], restored)
    database = Path(result['database_path'])
    assert database.read_bytes() == ws['destination'].read_bytes()
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute('SELECT value FROM ordinary_work').fetchall() == [('retained user work',)]
    assert result['signing_mode'] == 'KEYLESS_NO_SIGNED_EVIDENCE'
    assert result['manifest_authentication'] == 'UNAVAILABLE_UNSIGNED_BACKUP'
    assert result['active_key_id'] is None and result['signing_sha256'] is None
    assert result['required_key_ids'] == [] and result['signed_evidence_rows'] == 0
    assert result['canonical_database_changed'] is False and result['service_started'] is False
    assert json.loads((restored / 'restore-verification.json').read_text()) == result
    assert not (restored / 'security').exists() and not (ws['root'] / 'security').exists()
    assert ws['db'].read_bytes() == before
    assert environment == {name: value for name, value in os.environ.items() if name.startswith('LUMENIS_EVIDENCE_HMAC_')}
    with pytest.raises(FileExistsError):
        migrations.restore_database_to_directory(ws['destination'], restored)
    assert database.read_bytes() == ws['destination'].read_bytes()


@pytest.mark.parametrize('mutation', ['database', 'manifest', 'claimed_key', 'signed_count'])
def test_keyless_hash_and_identity_tampering_never_publishes(keyless_workspace, tmp_path, mutation):
    ws = keyless_workspace
    migrations.backup_database_to_path(ws['destination'])
    path = Path(str(ws['destination']) + '.signing-manifest.json')
    value = json.loads(path.read_text())
    if mutation == 'database':
        with closing(sqlite3.connect(ws['destination'])) as connection:
            connection.execute("UPDATE ordinary_work SET value='changed-after-backup'")
            connection.commit()
    elif mutation == 'manifest':
        value['database']['restore_relative_path'] = 'nested/changed.db'
    elif mutation == 'claimed_key':
        value['signing']['active_key_id'] = 'pretend-key'
    else:
        value['verification'].update(signed_evidence_rows=1, evidence_signatures='VERIFIED')
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored-keyless')
    assert not (tmp_path / 'restored-keyless').exists()
    assert not list(tmp_path.glob('.restored-keyless.restore-*'))
    assert not (ws['root'] / 'security').exists()


@pytest.mark.parametrize('marker', ['integrity_version', 'integrity_algorithm', 'integrity_key_id', 'integrity_digest'])
def test_keyless_manifest_cannot_admit_signature_markers_even_with_matching_public_hashes(keyless_workspace, tmp_path, marker):
    ws = keyless_workspace
    migrations.backup_database_to_path(ws['destination'])
    path = Path(str(ws['destination']) + '.signing-manifest.json')
    value = json.loads(path.read_text())
    with closing(sqlite3.connect(ws['destination'])) as connection:
        connection.execute('CREATE TABLE app_evidence_records(id INTEGER PRIMARY KEY, '
            'integrity_version INTEGER, integrity_algorithm TEXT, integrity_key_id TEXT, integrity_digest TEXT)')
        connection.execute(f'INSERT INTO app_evidence_records({marker}) VALUES(?)', (1 if marker == 'integrity_version' else 'pretend-signature',))
        connection.commit()
    value['database']['sha256'] = hashlib.sha256(ws['destination'].read_bytes()).hexdigest()
    value['integrity']['digest'] = migrations._backup_manifest_digest(value, None)
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='KEYLESS_SIGNED_EVIDENCE_FORBIDDEN'):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'restored-keyless')
    assert not (tmp_path / 'restored-keyless').exists()
    assert not list(tmp_path.glob('.restored-keyless.restore-*'))


def test_signed_backup_cannot_be_relabelled_keyless_to_skip_signature_verification(signed_workspace, tmp_path):
    ws = signed_workspace
    path = _backup(ws)
    value = json.loads(path.read_text())
    blob = ws['destination'].parent / value['signing']['name']
    value['schema'] = 'lumenis.database-backup-keyless/v1'
    value['signing'] = {'name': None, 'sha256': None, 'restore_relative_path': None,
        'active_key_id': None, 'required_key_ids': [], 'state': 'NOT_REQUIRED_NO_SIGNED_EVIDENCE'}
    value['verification'].update(signed_evidence_rows=0, evidence_signatures='NO_SIGNED_EVIDENCE_ROWS')
    value['recovery'] = {'protection': 'NO_SIGNING_CONFIGURATION', 'requires_original_windows_user_profile': False}
    value['integrity'] = {'algorithm': 'sha256', 'key_id': None, 'digest': migrations._backup_manifest_digest(value, None)}
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='KEYLESS_SIGNING_COMPANION_CONFLICT'):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'downgraded')
    blob.unlink()
    with pytest.raises(ValueError, match='KEYLESS_SIGNED_EVIDENCE_FORBIDDEN'):
        migrations.restore_database_to_directory(ws['destination'], tmp_path / 'downgraded')
    assert not (tmp_path / 'downgraded').exists()


def test_legacy_bare_unsigned_database_still_requires_an_explicit_verified_manifest(keyless_workspace, tmp_path):
    bare = tmp_path / 'legacy-bare.db'
    bare.write_bytes(keyless_workspace['db'].read_bytes())
    with pytest.raises(ValueError, match='MANIFEST_INVALID_OR_MISSING'):
        migrations.restore_database_to_directory(bare, tmp_path / 'bare-restored')
    assert not (tmp_path / 'bare-restored').exists()

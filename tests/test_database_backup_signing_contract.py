"""Real signatures and native local protection, confined to disposable workspaces."""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from lumenis.shared.database import DatabaseRepository, migrations
from lumenis.shared.evidence import signing_config, store


@pytest.fixture
def signed_workspace(tmp_path, monkeypatch, request):
    root = tmp_path / 'source'
    root.mkdir()
    database = root / getattr(request, 'param', 'monitor.db')
    database.parent.mkdir(parents=True, exist_ok=True)
    loaded = {}
    file = signing_config.activate_workspace_signing(str(root), str(database), loaded)
    monkeypatch.setenv('ZBC_DB_PATH', str(database))
    monkeypatch.setenv('ZBC_DATA_DIR', str(root))
    for name, value in loaded.items():
        monkeypatch.setenv(name, value)
    repository = DatabaseRepository(str(database))
    monkeypatch.setattr(store, 'get_repository', lambda: repository)
    store.init_evidence_store(str(database))
    with repository.transaction() as connection:
        store.ensure_evidence_schema(connection)
    record_id = store.record_evidence(source='isolated-backup-regression', product='CTH',
        domain_id='cth', subject_id='SUBJ-BACKUP', inputs={'source_id': 'isolated-backup-source'})
    assert record_id > 0
    return {'root': root, 'db': database, 'file': file, 'record_id': record_id, 'loaded': loaded,
            'destination': tmp_path / 'backups' / 'snapshot.db'}


def _companions(ws):
    destination = ws['destination']
    return Path(str(destination) + '.' + ws['file'].name), Path(str(destination) + '.signing-manifest.json')


def test_explicit_existing_signer_import_keeps_history_and_restores_backup(signed_workspace, tmp_path):
    ws = signed_workspace
    before = ws['db'].read_bytes()
    ws['file'].unlink()
    loaded = dict(ws['loaded'])
    path = signing_config.import_existing_workspace_signing(str(ws['root']), str(ws['db']), loaded)
    assert path == ws['file'] and loaded == ws['loaded']
    assert ws['db'].read_bytes() == before
    activated = {}
    signing_config.activate_workspace_signing(str(ws['root']), str(ws['db']), activated)
    assert activated == loaded
    migrations.backup_database_to_path(ws['destination'])
    restored = tmp_path / 'restored-legacy-signer'
    migrations.restore_database_to_directory(ws['destination'], restored)
    recovered = {}
    signing_config.activate_workspace_signing(str(restored), str(restored / 'monitor.db'), recovered)
    assert recovered == loaded


def test_activation_imports_registered_environment_signer_without_changing_evidence(signed_workspace):
    ws = signed_workspace
    before = ws['db'].read_bytes()
    ws['file'].unlink()
    loaded = dict(ws['loaded'])

    path = signing_config.activate_workspace_signing(str(ws['root']), str(ws['db']), loaded)

    assert path == ws['file'] and path.is_file()
    assert loaded == ws['loaded']
    assert ws['db'].read_bytes() == before


@pytest.mark.parametrize('failure', ['missing_ring', 'missing_active', 'wrong_key'])
def test_activation_refuses_unverified_environment_signer_without_writing(signed_workspace, failure):
    ws = signed_workspace
    before = ws['db'].read_bytes()
    ws['file'].unlink()
    loaded = dict(ws['loaded'])
    if failure == 'missing_ring':
        loaded.pop('LUMENIS_EVIDENCE_HMAC_KEY_RING')
    elif failure == 'missing_active':
        loaded.pop('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID')
    else:
        active = loaded['LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID']
        loaded['LUMENIS_EVIDENCE_HMAC_KEY_RING'] = json.dumps({active: 'x' * 48})

    with pytest.raises(signing_config.WorkspaceSigningError):
        signing_config.activate_workspace_signing(str(ws['root']), str(ws['db']), loaded)

    assert not ws['file'].exists()
    assert ws['db'].read_bytes() == before


@pytest.mark.parametrize('failure', ['no_key', 'wrong_key', 'missing_id', 'short_key', 'tampered_record'])
def test_explicit_signer_import_refuses_unverified_material(signed_workspace, failure):
    ws = signed_workspace
    ws['file'].unlink()
    loaded = dict(ws['loaded'])
    active = loaded['LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID']
    if failure == 'no_key':
        loaded.clear()
    elif failure == 'wrong_key':
        loaded['LUMENIS_EVIDENCE_HMAC_KEY_RING'] = json.dumps({active: 'x' * 48})
    elif failure == 'missing_id':
        loaded['LUMENIS_EVIDENCE_HMAC_KEY_RING'] = json.dumps({'other-key': 'x' * 48})
        loaded['LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID'] = 'other-key'
    elif failure == 'short_key':
        loaded['LUMENIS_EVIDENCE_HMAC_KEY_RING'] = json.dumps({active: 'short'})
    else:
        with sqlite3.connect(ws['db']) as connection:
            connection.execute("UPDATE app_evidence_records SET source='tampered-test-source'")
    before = ws['db'].read_bytes()
    with pytest.raises(signing_config.WorkspaceSigningError):
        signing_config.import_existing_workspace_signing(str(ws['root']), str(ws['db']), loaded)
    assert not ws['file'].exists()
    assert ws['db'].read_bytes() == before


def test_explicit_signer_import_never_replaces_existing_configuration(signed_workspace):
    ws = signed_workspace
    before = ws['file'].read_bytes()
    with pytest.raises(signing_config.WorkspaceSigningError, match='ALREADY_EXISTS'):
        signing_config.import_existing_workspace_signing(str(ws['root']), str(ws['db']), ws['loaded'])
    assert ws['file'].read_bytes() == before


@pytest.fixture
def keyless_workspace(tmp_path, monkeypatch, request):
    root = tmp_path / 'unsigned-source'
    root.mkdir()
    database = root / 'monitor.db'
    kind = getattr(request, 'param', 'no_evidence_table')
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE ordinary_work(value TEXT)')
        connection.execute('INSERT INTO ordinary_work VALUES(?)', ('retained user work',))
        if kind != 'no_evidence_table':
            connection.execute('CREATE TABLE app_evidence_records(id INTEGER PRIMARY KEY, source TEXT, '
                'integrity_version INTEGER, integrity_algorithm TEXT, integrity_key_id TEXT, integrity_digest TEXT)')
            if kind == 'unsigned_evidence':
                connection.execute("INSERT INTO app_evidence_records(source) VALUES('historical-unsigned-input')")
    monkeypatch.setenv('ZBC_DB_PATH', str(database))
    monkeypatch.setenv('ZBC_DATA_DIR', str(root))
    return {'root': root, 'db': database, 'destination': root / 'backups' / 'unsigned.db'}


@pytest.mark.parametrize('keyless_workspace', ['no_evidence_table', 'empty_evidence', 'unsigned_evidence'], indirect=True)
def test_keyless_backup_has_explicit_integrity_manifest_and_never_creates_a_signer(keyless_workspace, monkeypatch):
    ws = keyless_workspace
    before = ws['db'].read_bytes()
    environment = {name: value for name, value in os.environ.items() if name.startswith('LUMENIS_EVIDENCE_HMAC_')}
    monkeypatch.setattr(signing_config, 'activate_workspace_signing', lambda *a, **k: pytest.fail('Keyless backup cannot initialize a signer'))
    migrations.backup_database_to_path(ws['destination'])
    manifest = json.loads(Path(str(ws['destination']) + '.signing-manifest.json').read_text())
    assert manifest['schema'] == 'lumenis.database-backup-keyless/v1'
    assert manifest['signing'] == {'name': None, 'sha256': None, 'restore_relative_path': None,
        'active_key_id': None, 'required_key_ids': [], 'state': 'NOT_REQUIRED_NO_SIGNED_EVIDENCE'}
    assert manifest['verification'] == {'sqlite_integrity': 'VERIFIED', 'signed_evidence_rows': 0,
                                      'evidence_signatures': 'NO_SIGNED_EVIDENCE_ROWS'}
    assert manifest['integrity']['algorithm'] == 'sha256' and manifest['integrity']['key_id'] is None
    assert manifest['integrity']['digest'] == migrations._backup_manifest_digest(manifest, None)
    assert manifest['database']['sha256'] == hashlib.sha256(ws['destination'].read_bytes()).hexdigest()
    assert not (ws['root'] / 'security').exists()
    assert not list(ws['destination'].parent.glob('*.evidence-signing.*'))
    assert ws['db'].read_bytes() == before
    assert environment == {name: value for name, value in os.environ.items() if name.startswith('LUMENIS_EVIDENCE_HMAC_')}


@pytest.mark.parametrize('marker', ['integrity_version', 'integrity_algorithm', 'integrity_key_id', 'integrity_digest'])
def test_keyless_backup_refuses_any_partial_or_complete_signature_marker(keyless_workspace, marker):
    ws = keyless_workspace
    with sqlite3.connect(ws['db']) as connection:
        connection.execute('CREATE TABLE app_evidence_records(id INTEGER PRIMARY KEY, '
            'integrity_version INTEGER, integrity_algorithm TEXT, integrity_key_id TEXT, integrity_digest TEXT)')
        connection.execute(f'INSERT INTO app_evidence_records({marker}) VALUES(?)', (1 if marker == 'integrity_version' else 'present',))
    with pytest.raises(signing_config.WorkspaceSigningError, match='KEY_RECOVERY_REQUIRED'):
        migrations.backup_database_to_path(ws['destination'])
    assert not ws['destination'].exists()
    assert not Path(str(ws['destination']) + '.signing-manifest.json').exists()
    assert not (ws['root'] / 'security').exists()


def test_keyless_backup_does_not_publish_beside_existing_signer_companion(keyless_workspace):
    ws = keyless_workspace
    ws['destination'].parent.mkdir()
    existing = Path(str(ws['destination']) + '.evidence-signing.dpapi')
    existing.write_bytes(b'existing-owned-companion')
    with pytest.raises(FileExistsError, match='KEYLESS_SIGNING_COMPANION_CONFLICT'):
        migrations.backup_database_to_path(ws['destination'])
    assert existing.read_bytes() == b'existing-owned-companion'
    assert not ws['destination'].exists()


@pytest.mark.parametrize('entry', ['absolute', 'named'])
def test_backup_preserves_exact_protected_signer_and_nonsecret_identity_manifest(signed_workspace, entry):
    ws = signed_workspace
    source_before, blob_before = ws['db'].read_bytes(), ws['file'].read_bytes()
    environment_before = {name: os.environ[name] for name in ws['loaded']}
    if entry == 'absolute':
        result = migrations.backup_database_to_path(ws['destination'])
    else:
        ws['destination'] = ws['root'] / 'backups' / 'named.db'
        result = migrations.backup_database('named.db')
    assert result == str(ws['destination'])
    blob, manifest_path = _companions(ws)
    assert blob.read_bytes() == blob_before and ws['file'].read_bytes() == blob_before
    assert ws['db'].read_bytes() == source_before
    assert environment_before == {name: os.environ[name] for name in ws['loaded']}
    manifest = json.loads(manifest_path.read_text())
    key_id = ws['loaded']['LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID']
    assert manifest['database']['sha256'] == hashlib.sha256(ws['destination'].read_bytes()).hexdigest()
    assert manifest['database']['restore_relative_path'] == 'monitor.db'
    assert manifest['signing']['sha256'] == hashlib.sha256(blob_before).hexdigest()
    assert manifest['signing']['required_key_ids'] == [key_id]
    assert manifest['signing']['active_key_id'] == key_id
    assert manifest['verification']['signed_evidence_rows'] == 1
    assert manifest['verification']['evidence_signatures'] == 'VERIFIED'
    for secret in json.loads(ws['loaded']['LUMENIS_EVIDENCE_HMAC_KEY_RING']).values():
        assert secret not in manifest_path.read_text()
        if os.name == 'nt':
            assert secret.encode() not in blob.read_bytes()
    if os.name != 'nt':
        assert blob.stat().st_mode & 0o777 == 0o600


def test_backup_bundle_reopens_original_evidence_signature_in_independent_restored_workspace(signed_workspace, tmp_path):
    ws = signed_workspace
    migrations.backup_database_to_path(ws['destination'])
    blob, manifest_path = _companions(ws)
    manifest = json.loads(manifest_path.read_text())
    restored = tmp_path / 'restored'
    result = migrations.restore_database_to_directory(ws['destination'], restored)
    assert result['status'] == 'RESTORED_TO_NEW_DIRECTORY'
    assert result['canonical_database_changed'] is False and result['service_started'] is False
    restored_db = restored / manifest['database']['restore_relative_path']
    restored_key = restored / manifest['signing']['restore_relative_path']
    assert restored_key.read_bytes() == blob.read_bytes()
    assert restored_db.read_bytes() == ws['destination'].read_bytes()
    assert not list(restored.rglob('*-wal')) and not list(restored.rglob('*-shm'))
    env = os.environ.copy()
    for name in ws['loaded']:
        env.pop(name, None)
    env['ZBC_DB_PATH'], env['ZBC_DATA_DIR'] = str(restored_db), str(restored)
    code = (
        'import json,sys; from lumenis.shared.evidence.signing_config import activate_workspace_signing; '
        'activate_workspace_signing(sys.argv[1],sys.argv[2]); '
        'from lumenis.shared.database import DatabaseRepository; '
        'from lumenis.shared.evidence.store import verify_evidence_record_integrity; '
        'con=DatabaseRepository(sys.argv[2]).connect(read_only=True); '
        'row=con.execute("SELECT * FROM app_evidence_records WHERE id=?",(int(sys.argv[3]),)).fetchone(); '
        'assert verify_evidence_record_integrity(dict(row)); '
        'print(json.dumps({"verified":True,"key_id":row["integrity_key_id"]})); con.close()'
    )
    result = subprocess.run([sys.executable, '-c', code, str(restored), str(restored_db), str(ws['record_id'])],
                            env=env, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == {'verified': True, 'key_id': manifest['signing']['active_key_id']}


@pytest.mark.parametrize('failure', ['missing', 'corrupt', 'missing_id', 'wrong_same_id_key', 'tampered_evidence'])
def test_invalid_signing_recovery_never_publishes_a_complete_backup(signed_workspace, failure):
    ws = signed_workspace
    if failure == 'missing':
        ws['file'].unlink()
    elif failure == 'corrupt':
        ws['file'].write_bytes(b'corrupted-test-configuration')
    elif failure in {'missing_id', 'wrong_same_id_key'}:
        raw = ws['file'].read_bytes()
        payload = json.loads(signing_config._dpapi(raw, decrypt=True) if os.name == 'nt' else raw)
        if failure == 'missing_id':
            payload['active_id'], payload['keys'] = 'other-test-key', {'other-test-key': 'x' * 48}
        else:
            payload['keys'][payload['active_id']] = 'x' * 48
        raw = json.dumps(payload).encode()
        ws['file'].write_bytes(signing_config._dpapi(raw, decrypt=False) if os.name == 'nt' else raw)
    else:
        with sqlite3.connect(ws['db']) as con:
            con.execute("UPDATE app_evidence_records SET source='tampered-test-source'")
    before = ws['file'].read_bytes() if ws['file'].exists() else None
    with pytest.raises(signing_config.WorkspaceSigningError):
        migrations.backup_database_to_path(ws['destination'])
    assert not ws['destination'].exists()
    assert all(not path.exists() for path in _companions(ws))
    assert (ws['file'].read_bytes() if ws['file'].exists() else None) == before


@pytest.mark.parametrize('companion', [0, 1])
def test_existing_signing_backup_is_never_overwritten_or_deleted(signed_workspace, companion):
    ws = signed_workspace
    old = _companions(ws)[companion]
    old.parent.mkdir()
    old.write_bytes(b'existing-owned-backup')
    with pytest.raises(FileExistsError):
        migrations.backup_database_to_path(ws['destination'])
    assert old.read_bytes() == b'existing-owned-backup'
    assert not ws['destination'].exists()


@pytest.mark.parametrize('companion', [0, 1])
def test_companion_publish_failure_cleans_only_this_attempt_and_preserves_race_winner(signed_workspace, monkeypatch, companion):
    ws = signed_workspace
    failed = _companions(ws)[companion]
    original = migrations.os.link
    def publish(source, destination):
        if str(destination) == str(failed):
            if companion:
                failed.write_bytes(b'concurrent-backup-owner')
                raise FileExistsError('concurrent backup owner')
            raise OSError('isolated companion publication failure')
        return original(source, destination)
    monkeypatch.setattr(migrations.os, 'link', publish)
    with pytest.raises(OSError):
        migrations.backup_database_to_path(ws['destination'])
    assert not ws['destination'].exists()
    if companion:
        assert failed.read_bytes() == b'concurrent-backup-owner'
    else:
        assert not failed.exists()
    assert not list(ws['destination'].parent.glob('.snapshot.db.*.tmp'))
    assert ws['file'].is_file()


def test_configuration_changed_during_snapshot_is_not_reported_as_complete(signed_workspace, monkeypatch):
    ws = signed_workspace
    original = signing_config.activate_workspace_signing
    def changed(*args, **kwargs):
        path = original(*args, **kwargs)
        path.write_bytes(path.read_bytes() + b'changed-by-concurrent-test-owner')
        return path
    monkeypatch.setattr(signing_config, 'activate_workspace_signing', changed)
    with pytest.raises(signing_config.WorkspaceSigningError, match='CONFIGURATION_CHANGED'):
        migrations.backup_database_to_path(ws['destination'])
    assert not ws['destination'].exists()


def test_backup_never_initializes_a_missing_or_raced_away_signer(tmp_path, monkeypatch):
    database = tmp_path / 'monitor.db'
    with sqlite3.connect(database) as con:
        con.execute('CREATE TABLE ordinary_work(value TEXT)')
    monkeypatch.setenv('ZBC_DB_PATH', str(database))
    monkeypatch.setenv('ZBC_DATA_DIR', str(tmp_path))
    migrations.backup_database_to_path(tmp_path / 'legacy.db')
    assert not (tmp_path / 'security').exists()
    file = signing_config.activate_workspace_signing(str(tmp_path), str(database), {})
    original = signing_config.activate_workspace_signing
    def removed(*args, **kwargs):
        file.unlink()
        return original(*args, **kwargs)
    monkeypatch.setattr(signing_config, 'activate_workspace_signing', removed)
    with pytest.raises(signing_config.WorkspaceSigningError, match='KEY_IMPORT_REQUIRED'):
        migrations.backup_database_to_path(tmp_path / 'raced.db')
    assert not file.exists() and not (tmp_path / 'raced.db').exists()

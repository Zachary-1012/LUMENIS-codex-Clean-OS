import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from lumenis.shared.evidence.signing_config import (
    WorkspaceSigningError,
    activate_workspace_signing,
)


def signed_database(database, key_id):
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE app_evidence_records (integrity_key_id TEXT, integrity_digest TEXT)")
        conn.execute("INSERT INTO app_evidence_records VALUES (?, 'signed')", (key_id,))


def test_new_workspace_key_reloads_in_independent_process(tmp_path, monkeypatch):
    from lumenis.shared.database import DatabaseRepository
    from lumenis.shared.evidence import store

    env = {}
    path = activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), env)
    before = path.read_bytes()
    key_id = env['LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID']
    monkeypatch.setenv('ZBC_DB_PATH', str(tmp_path / 'monitor.db'))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    repository = DatabaseRepository(str(tmp_path / 'monitor.db'))
    monkeypatch.setattr(store, 'get_repository', lambda: repository)
    store.init_evidence_store(str(tmp_path / 'monitor.db'))
    with repository.transaction() as connection:
        store.ensure_evidence_schema(connection)
    record_id = store.record_evidence(source='isolated-verification', product='CTH',
                                     domain_id='cth', subject_id='SUBJ-SIGNER-REGRESSION',
                                     inputs={'source_id': 'isolated-document'})
    assert record_id > 0
    clean_env = os.environ.copy()
    clean_env.pop('LUMENIS_EVIDENCE_HMAC_KEY_RING', None)
    clean_env.pop('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', None)
    code = (
        'import hashlib,sys; from lumenis.shared.evidence.signing_config import activate_workspace_signing; '
        'import os; activate_workspace_signing(sys.argv[1],sys.argv[2]); '
        'from lumenis.shared.database import DatabaseRepository; '
        'from lumenis.shared.evidence.store import verify_evidence_record_integrity; '
        'conn=DatabaseRepository(sys.argv[2]).connect(read_only=True); '
        'row=conn.execute("SELECT * FROM app_evidence_records WHERE id=?",(int(sys.argv[3]),)).fetchone(); '
        'assert verify_evidence_record_integrity(dict(row)); conn.close(); '
        'print(hashlib.sha256(os.environ["LUMENIS_EVIDENCE_HMAC_KEY_RING"].encode()).hexdigest())'
    )
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path), str(tmp_path / 'monitor.db'), str(record_id)],
                            capture_output=True, text=True, env=clean_env, check=True)
    assert result.stdout.strip() == hashlib.sha256(env['LUMENIS_EVIDENCE_HMAC_KEY_RING'].encode()).hexdigest()
    assert path.read_bytes() == before
    assert key_id in json.loads(env['LUMENIS_EVIDENCE_HMAC_KEY_RING'])
    if os.name == 'nt':
        assert env['LUMENIS_EVIDENCE_HMAC_KEY_RING'].encode() not in before


def test_signed_history_without_key_cannot_initialize(tmp_path):
    signed_database(tmp_path / 'monitor.db', 'previous-key')
    with pytest.raises(WorkspaceSigningError, match='KEY_RECOVERY_REQUIRED'):
        activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), {})
    assert not (tmp_path / 'security').exists()


def test_corrupted_key_never_replaced(tmp_path):
    path = activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), {})
    path.write_bytes(b'corrupted-key')
    with pytest.raises(WorkspaceSigningError, match='KEY_UNREADABLE'):
        activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), {})
    assert path.read_bytes() == b'corrupted-key'


def test_key_does_not_cover_historical_identity(tmp_path):
    path = activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), {})
    before = path.read_bytes()
    signed_database(tmp_path / 'monitor.db', 'other-workspace-key')
    with pytest.raises(WorkspaceSigningError, match='KEY_RECOVERY_REQUIRED'):
        activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), {})
    assert path.read_bytes() == before


def test_inherited_key_requires_explicit_migration(tmp_path):
    with pytest.raises(WorkspaceSigningError, match='KEY_IMPORT_REQUIRED'):
        activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'),
                                   {'LUMENIS_EVIDENCE_HMAC_KEY_RING': '{"unrelated":"secret"}'})
    assert not (tmp_path / 'security').exists()


def test_other_database_not_silently_attached(tmp_path):
    activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), {})
    with pytest.raises(WorkspaceSigningError, match='KEY_UNREADABLE'):
        activate_workspace_signing(str(tmp_path), str(tmp_path / 'other.db'), {})


def test_outside_data_root_rejected(tmp_path):
    with pytest.raises(WorkspaceSigningError, match='OUTSIDE_ROOT'):
        activate_workspace_signing(str(tmp_path), str(tmp_path / '..' / 'outside.db'), {})


def test_unreadable_database_does_not_initialize(tmp_path):
    (tmp_path / 'monitor.db').write_bytes(b'not a database')
    with pytest.raises(WorkspaceSigningError, match='DATABASE_UNREADABLE'):
        activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), {})
    assert not (tmp_path / 'security').exists()


def test_partial_signature_schema_refuses_generation(tmp_path):
    with sqlite3.connect(tmp_path / 'monitor.db') as conn:
        conn.execute('CREATE TABLE app_evidence_records (integrity_key_id TEXT)')
    with pytest.raises(WorkspaceSigningError, match='SCHEMA_RECOVERY_REQUIRED'):
        activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), {})


def test_atomic_publish_preserves_existing_race_winner(tmp_path, monkeypatch):
    import lumenis.shared.evidence.signing_config as config

    original = os.link
    winner = tmp_path / 'winner'
    winner.mkdir()
    winner_env = {}
    winner_path = activate_workspace_signing(str(winner), str(winner / 'monitor.db'), winner_env)

    def other_writer_wins(source, destination):
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output:
            output.write(winner_path.read_bytes())
        original(source, destination)

    monkeypatch.setattr(config.os, 'link', other_writer_wins)
    env = {}
    activate_workspace_signing(str(tmp_path), str(tmp_path / 'monitor.db'), env)
    assert env == winner_env
    assert not list((tmp_path / 'security').glob('.evidence-signing-*'))

"""The boundary audit requires the current owner, not the removed root module."""
from scripts.audit_tools import boundary_check


def test_canonical_permission_owner_satisfies_existence_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, "PROJECT_ROOT", tmp_path)
    owner = tmp_path / "lumenis/system/security/permission.py"
    owner.parent.mkdir(parents=True)
    owner.write_text("# Owner fixture; this test is not execution authorization.\n")
    assert boundary_check.check_permission_gate([]) == []


def test_legacy_root_file_cannot_substitute_missing_canonical_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, "PROJECT_ROOT", tmp_path)
    (tmp_path / "permission_gate.py").write_text("# Legacy fixture\n")
    violations = boundary_check.check_permission_gate([])
    assert len(violations) == 1
    assert violations[0].severity == boundary_check.SEVERITY_HIGH
    assert violations[0].file == "lumenis/system/security/permission.py"


def _source(tmp_path, name, text):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_comment_cannot_authorize_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'lumenis/system/security/permission.py', '# fixture')
    path = _source(tmp_path, 'agent_unsafe.py', '# permission_gate check_permission\ndef execute():\n    return send()\n')
    assert boundary_check.check_permission_gate([path])[0].severity == 'HIGH'


def test_registered_gate_call_not_comment_is_recognized(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'lumenis/system/security/permission.py', '# fixture')
    path = _source(tmp_path, 'agent_safe.py', 'def execute():\n    if not check_permission():\n        return False\n    return send()\n')
    assert boundary_check.check_permission_gate([path]) == []


def test_reviewed_delegate_byte_change_requires_new_review(tmp_path, monkeypatch):
    import hashlib
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'lumenis/system/security/permission.py', '# fixture')
    path = _source(tmp_path, 'agent_delegate.py', 'def execute():\n    return owner()\n')
    source_hash = hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    monkeypatch.setattr(boundary_check, '_REVIEWED_BOUNDARIES', {'agent_delegate.py': {'sha256': source_hash}})
    assert boundary_check.check_permission_gate([path]) == []
    path.write_text('def execute():\n    return unsafe()\n')
    assert boundary_check.check_permission_gate([path])[0].severity == 'HIGH'


def test_catalog_status_comment_does_not_authorize_source_use(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    path = _source(tmp_path, 'consumer.py', '# knowledge_status admission_status\ndef read(db):\n    return db.execute("SELECT * FROM intelligence_assets").fetchall()\n')
    result = boundary_check.check_pending_assets_production_ref([path])
    assert result and result[0].severity == 'HIGH'


def test_no_implicit_database_connection(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    def denied(*args, **kwargs):
        raise AssertionError('Source checker must not access a database')
    monkeypatch.setattr(boundary_check.sqlite3, 'connect', denied)
    assert boundary_check.get_production_tables() == set()
    assert boundary_check.check_pending_assets_production_ref([]) == []


def test_inventory_prunes_root_work_but_not_owner_work(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'work/private.py', 'not valid python!')
    _source(tmp_path, 'tests/fixture.py', 'not valid python!')
    included = _source(tmp_path, 'owner/work/real.py', 'x = 1')
    assert boundary_check.get_production_py_files() == [included]
    included.write_text('not valid python!')
    import pytest
    with pytest.raises(SyntaxError):
        boundary_check.get_production_py_files()


def test_comments_do_not_invent_cross_repo_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'contracts/example.py', 'x=1')
    path = _source(tmp_path, 'adapter.py', '# subprocess.run osai\nx = "subprocess.run osai"\n')
    assert boundary_check.check_contract_artifact_usage([path]) == []


def test_reviewed_source_dependency_change_blocks(tmp_path, monkeypatch):
    import hashlib
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    path = _source(tmp_path, 'agent_reader.py', 'def read(db):\n    return db.execute("SELECT * FROM intelligence_assets").fetchall()\n')
    owner = _source(tmp_path, 'owner.py', 'def admit(): return True\n')
    source_hash = hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    owner_hash = hashlib.sha256(owner.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    monkeypatch.setattr(boundary_check, '_REVIEWED_BOUNDARIES', {'agent_reader.py': {
        'sha256': source_hash,
        'dependencies': {'owner.py': owner_hash}}})
    assert boundary_check.check_pending_assets_production_ref([path]) == []
    owner.write_text('def admit(): return False\n')
    assert boundary_check.check_pending_assets_production_ref([path])[0].severity == 'HIGH'


def test_unrelated_gate_function_does_not_authorize_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'lumenis/system/security/permission.py', '# fixture')
    path = _source(tmp_path, 'agent_unsafe.py', 'def unrelated():\n    return check_permission()\ndef execute_task(effect):\n    return effect()\n')
    assert boundary_check.check_permission_gate([path])[0].severity == 'HIGH'


def test_getter_alone_is_not_authorization(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'lumenis/system/security/permission.py', '# fixture')
    path = _source(tmp_path, 'agent_unsafe.py', 'def execute_task(effect):\n    gate = get_permission_gate()\n    return effect()\n')
    assert boundary_check.check_permission_gate([path])[0].severity == 'HIGH'


def test_uncalled_nested_gate_does_not_authorize_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'lumenis/system/security/permission.py', '# fixture')
    path = _source(tmp_path, 'agent_unsafe.py', 'def execute_task(effect):\n    def unused():\n        check_permission()\n    return effect()\n')
    assert boundary_check.check_permission_gate([path])[0].severity == 'HIGH'


def test_explicit_local_delegate_reaches_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    _source(tmp_path, 'lumenis/system/security/permission.py', '# fixture')
    path = _source(tmp_path, 'agent_safe.py', 'def admitted():\n    if not check_permission():\n        return False\n    return send()\ndef execute_task():\n    return admitted()\n')
    assert boundary_check.check_permission_gate([path]) == []


def test_included_symlink_directory_is_not_silently_omitted(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    target = tmp_path / 'owner'
    target.mkdir()
    (tmp_path / 'linked_owner').symlink_to(target, target_is_directory=True)
    with pytest.raises(OSError, match='symlink'):
        boundary_check.get_production_py_files()


def test_credential_diagnostic_never_echoes_matched_value(tmp_path, monkeypatch):
    monkeypatch.setattr(boundary_check, 'PROJECT_ROOT', tmp_path)
    synthetic = 'NOT_A_REAL_SECRET_FIXTURE'
    path = _source(tmp_path, 'worker.py', 'password = "' + synthetic + '"\n')
    records = boundary_check.check_credential_safety([path])
    assert records and records[0].severity == 'HIGH'
    assert synthetic not in str([r.to_dict() for r in records])

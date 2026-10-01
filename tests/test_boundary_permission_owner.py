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

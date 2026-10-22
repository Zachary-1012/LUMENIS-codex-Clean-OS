import hashlib

import pytest

from scripts.audit_tools import boundary_check


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_review_checks_source_and_delegate_on_each_checkout(tmp_path, monkeypatch, newline):
    source = b"def execute():\n    return delegate()\n"
    dependency = b"def delegate():\n    raise PermissionError('denied')\n"
    entry = tmp_path / "entry.py"
    delegate = tmp_path / "delegate.py"
    entry.write_bytes(source.replace(b"\n", newline))
    delegate.write_bytes(dependency.replace(b"\n", newline))
    monkeypatch.setattr(boundary_check, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(boundary_check, "_REVIEWED_BOUNDARIES", {
        "entry.py": {"sha256": hashlib.sha256(source).hexdigest(), "dependencies": {
            "delegate.py": hashlib.sha256(dependency).hexdigest(),
        }},
    })
    assert boundary_check._review_status("entry.py", entry) is True
    delegate.write_bytes(b"def delegate():\n    return True\n")
    assert boundary_check._review_status("entry.py", entry) is False
    delegate.write_bytes(dependency)
    entry.write_bytes(source + b"execute()\n")
    assert boundary_check._review_status("entry.py", entry) is False
    entry.write_bytes(source)
    delegate.unlink()
    assert boundary_check._review_status("entry.py", entry) is False


def test_review_rejects_encoding_or_whitespace_drift(tmp_path, monkeypatch):
    source = b"value = 1\n"
    entry = tmp_path / "entry.py"
    monkeypatch.setattr(boundary_check, "_REVIEWED_BOUNDARIES", {
        "entry.py": {"sha256": hashlib.sha256(source).hexdigest()},
    })
    for changed in (b"\xef\xbb\xbf" + source, b"value  = 1\n", b"value = 1\r"):
        entry.write_bytes(changed)
        assert boundary_check._review_status("entry.py", entry) is False

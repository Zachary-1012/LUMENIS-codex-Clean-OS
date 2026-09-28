"""Existing Artifact registry integrity in disposable canonical-repository DBs."""
from pathlib import Path
import os

import pytest


@pytest.fixture
def registered(tmp_path, monkeypatch):
    db_path = tmp_path / "isolated-registry.db"
    root = tmp_path / "artifacts"
    root.mkdir()
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(root))
    import shared_artifacts as artifacts
    from lumenis.shared.database import main_db_path
    assert Path(main_db_path()).resolve() == db_path.resolve()
    path = root / "registered.mp4"
    path.write_bytes(b"isolated artifact bytes; not user media")
    record = artifacts._register_artifact(
        artifact_id="ART-integrity-case", kind="video_shotcraft_render",
        product_id="CTH", domain_id="cth", source_execution_id="isolated-case",
        evidence_id="", note_id="", path=path, media_type="video/mp4",
    )
    return artifacts, path, record


def test_existing_registered_file_can_be_reopened_without_record_changes(registered):
    artifacts, path, record = registered
    assert artifacts.artifact_file_path(record["artifact_id"]) == path
    assert artifacts.get_artifact(record["artifact_id"]) == record


@pytest.mark.parametrize("mutation", ["same-size", "size", "empty"])
def test_changed_artifact_is_rejected_and_original_record_is_preserved(registered, mutation):
    artifacts, path, record = registered
    original = path.read_bytes()
    changed = b"X" * len(original) if mutation == "same-size" else (b"short" if mutation == "size" else b"")
    path.write_bytes(changed)
    with pytest.raises(artifacts.LocalArtifactError, match="ARTIFACT_INTEGRITY_FAILED"):
        artifacts.artifact_file_path(record["artifact_id"])
    assert path.read_bytes() == changed
    assert artifacts.get_artifact(record["artifact_id"]) == record
    path.write_bytes(original)
    assert artifacts.artifact_file_path(record["artifact_id"]) == path


@pytest.mark.parametrize("digest", ["", "not-a-digest", "0" * 63])
def test_unknown_registry_digest_cannot_certify_a_file(registered, digest):
    artifacts, path, record = registered
    conn = artifacts._db_connect()
    try:
        conn.execute("UPDATE lumenis_shared_artifacts SET sha256=? WHERE artifact_id=?", (digest, record["artifact_id"]))
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(artifacts.LocalArtifactError, match="ARTIFACT_INTEGRITY_UNVERIFIED"):
        artifacts.artifact_file_path(record["artifact_id"])
    assert path.exists()


def test_missing_and_outside_root_files_remain_unavailable(registered, tmp_path):
    artifacts, path, record = registered
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(path.read_bytes())
    conn = artifacts._db_connect()
    try:
        conn.execute("UPDATE lumenis_shared_artifacts SET relative_path=? WHERE artifact_id=?", ("../outside.mp4", record["artifact_id"]))
        conn.commit()
    finally:
        conn.close()
    assert artifacts.artifact_file_path(record["artifact_id"]) is None
    assert outside.exists()


def test_missing_file_does_not_remove_its_registry_record(registered):
    artifacts, path, record = registered
    path.unlink()
    assert artifacts.artifact_file_path(record["artifact_id"]) is None
    assert artifacts.get_artifact(record["artifact_id"]) == record


def test_change_during_hashing_is_rejected_even_if_hash_helper_returns_old_hash(registered, monkeypatch):
    artifacts, path, record = registered
    before = path.stat()
    def race(candidate):
        candidate.write_bytes(b"X" * before.st_size)
        os.utime(candidate, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
        return record["sha256"]
    monkeypatch.setattr(artifacts, "_hash_file", race)
    with pytest.raises(artifacts.LocalArtifactError, match="ARTIFACT_INTEGRITY_FAILED"):
        artifacts.artifact_file_path(record["artifact_id"])
    assert artifacts.get_artifact(record["artifact_id"]) == record


def test_failed_file_read_is_explicit_and_does_not_alter_registration(registered, monkeypatch):
    artifacts, path, record = registered
    def fail(_path):
        raise OSError("private path must not appear in error")
    monkeypatch.setattr(artifacts, "_hash_file", fail)
    with pytest.raises(artifacts.LocalArtifactError, match="ARTIFACT_READ_UNAVAILABLE") as exc:
        artifacts.artifact_file_path(record["artifact_id"])
    assert "private path" not in str(exc.value)
    assert artifacts.get_artifact(record["artifact_id"]) == record

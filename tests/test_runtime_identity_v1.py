# -*- coding: utf-8 -*-
import json
import sqlite3

import runtime_identity as ri


def _make_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO evidence(value) VALUES ('first')")


def test_database_identity_is_read_only_and_hides_path(tmp_path):
    db_path = tmp_path / "runtime.db"
    _make_db(db_path)
    before = db_path.read_bytes()
    identity = ri._database_identity(str(db_path))
    after = db_path.read_bytes()

    assert before == after
    assert identity["exists"] is True
    assert identity["schema_digest"]
    assert str(db_path) not in json.dumps(identity)


def test_schema_digest_does_not_change_for_row_update(tmp_path):
    db_path = tmp_path / "runtime.db"
    _make_db(db_path)
    first = ri._database_identity(str(db_path))
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO evidence(value) VALUES ('second')")
    second = ri._database_identity(str(db_path))

    assert first["schema_digest"] == second["schema_digest"]
    assert first["identity_digest"] == second["identity_digest"]


def test_public_identity_is_minimal_and_cached(monkeypatch, tmp_path):
    db_path = tmp_path / "runtime.db"
    _make_db(db_path)
    calls = {"count": 0}
    original = ri.build_runtime_identity

    def counted_build_runtime_identity(*, db_path=None):
        calls["count"] += 1
        return original(db_path=str(db_path or db_path_for_test))

    db_path_for_test = db_path
    monkeypatch.setattr(ri, "build_runtime_identity", counted_build_runtime_identity)
    ri.reset_runtime_identity_cache()
    first = ri.get_runtime_identity(public=True)
    second = ri.get_runtime_identity(public=True)

    assert first == second
    assert calls["count"] == 1
    assert "database" not in first
    assert "source_branch" not in first
    assert "source_dirty" not in first
    assert first["identity_schema"] == "lumenis.runtime-identity.v1"


def test_manifest_is_not_verified_by_presence_only(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "release_manifest.json").write_text(
        json.dumps({
            "schema_version": "lumenis.release-manifest.v1",
            "release_id": "fake",
            "core_commit": "wrong",
            "source_tree_digest": "wrong",
            "product_mode": "CUSTOMER_RELEASE",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(ri, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(ri, "_git", lambda *args: "actual")

    identity = ri.build_runtime_identity(db_path=str(tmp_path / "missing.db"))
    assert identity["release_state"] == "DECLARED_UNVERIFIED"
    assert identity["release_manifest"]["verified"] is False
    assert identity["release_manifest"]["reason"] == "source_mismatch"


def test_manifest_verified_only_when_commit_and_tree_match(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "release_manifest.json").write_text(
        json.dumps({
            "schema_version": "lumenis.release-manifest.v1",
            "release_id": "release-test",
            "core_commit": "commit-test",
            "source_tree_digest": "tree-test",
            "product_mode": "ZBRAND_PLATFORM",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(ri, "ROOT_DIR", tmp_path)

    def fake_git(*args):
        return "tree-test" if args[-1] == "HEAD^{tree}" else "commit-test"

    monkeypatch.setattr(ri, "_git", fake_git)
    identity = ri.build_runtime_identity(db_path=str(tmp_path / "missing.db"))
    assert identity["release_state"] == "MANIFEST_VERIFIED"
    assert identity["release_manifest"]["verified"] is True

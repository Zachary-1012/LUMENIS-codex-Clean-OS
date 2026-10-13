"""Seed import reuses subject_registry.add_subject on a disposable SQLite DB."""
from __future__ import annotations

import collections
import sqlite3

import pytest

from scripts import import_subject_registry_seed as seed


@pytest.fixture
def seed_db(tmp_path, monkeypatch):
    path = tmp_path / "seed.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    return path


def test_seed_matches_manifest_and_is_verified():
    rows = seed.load_seed()
    assert rows
    assert all(r["verification_status"] == "VERIFIED_ONLINE" and r["verified_at"] for r in rows)
    assert all(r["source_url"].startswith("http") for r in rows)


def test_seed_has_no_registry_duplicates_and_valid_domains():
    import subject_registry as registry

    rows = seed.load_seed()
    keys = collections.Counter(
        (r["domain_id"], r["subject_type"], registry._canonical_name(r["name_en"]),
         registry._canonical_name(r["name_zh"]))
        for r in rows
    )
    assert max(keys.values()) == 1
    same_en = collections.Counter((r["domain_id"], registry._canonical_name(r["name_en"])) for r in rows)
    assert max(same_en.values()) == 1, "one identity per domain/name_en (aliases go to keywords)"
    for r in rows:
        assert (r["domain_id"], r["subject_type"]) in {("CTH", "company"), ("BMP", "brand")}


def test_dry_run_does_not_write(seed_db):
    report = seed.import_seed(seed.load_seed())
    assert report["would_import"] == report["total"]
    assert not seed_db.exists() or sqlite3.connect(seed_db).execute(
        "SELECT name FROM sqlite_master WHERE name='lumenis_subject_registry'").fetchone() is None


def test_apply_requires_exact_human_approval(seed_db, monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    from lumenis.system.security import permission

    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False, raising=False)
    permission.reset_permission_gate()
    with pytest.raises(seed.SeedApprovalRequired):
        seed.import_seed(seed.load_seed(), apply=True)
    assert not seed_db.exists() or sqlite3.connect(seed_db).execute(
        "SELECT name FROM sqlite_master WHERE name='lumenis_subject_registry'").fetchone() is None


def test_apply_is_idempotent_and_deterministic(seed_db, monkeypatch):
    # Stand-in for an exact human approval; the gate itself is exercised above.
    monkeypatch.setattr(seed, "require_apply_approval", lambda gate=None: None)
    rows = seed.load_seed()
    first = seed.import_seed(rows, apply=True)
    assert first["created"] == len(rows) and first["existing"] == 0
    second = seed.import_seed(rows, apply=True)
    assert second["created"] == 0 and second["existing"] == len(rows)
    assert first["subject_ids"] == second["subject_ids"]
    with sqlite3.connect(seed_db) as conn:
        count, = conn.execute("SELECT COUNT(*) FROM lumenis_subject_registry").fetchone()
        statuses = {s for (s,) in conn.execute("SELECT DISTINCT status FROM lumenis_subject_registry")}
        bmp_without_focus, = conn.execute(
            "SELECT COUNT(*) FROM lumenis_subject_registry WHERE domain_id='BMP' AND brand_focus_id IS NULL"
        ).fetchone()
    assert count == len(rows) and statuses == {"configured"} and bmp_without_focus == 0

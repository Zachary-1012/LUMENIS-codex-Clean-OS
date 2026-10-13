"""record_official_name stores only official names with official-site evidence."""
from __future__ import annotations

import pytest


@pytest.fixture
def reg(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "r.sqlite3"))
    import subject_registry as registry
    return registry


def _add(registry):
    row, _ = registry.add_subject({"domain_id": "BMP", "subject_type": "brand",
                                   "name_en": "Sephora", "name_zh": "Sephora", "keywords": []})
    return row["subject_id"]


def test_records_official_name_and_alias_keeps_id(reg):
    sid = _add(reg)
    out = reg.record_official_name("BMP", sid, source_url="https://www.sephora.cn/",
                                   name_zh="丝芙兰", keywords=["SEPHORA"])
    assert out["changed"] and out["after"]["subject_id"] == sid
    assert out["after"]["name_zh"] == "丝芙兰" and "SEPHORA" in out["after"]["keywords"]
    again = reg.record_official_name("BMP", sid, source_url="https://www.sephora.cn/", name_zh="丝芙兰")
    assert again["changed"] is False


@pytest.mark.parametrize("url", ["", "www.sephora.cn", "ftp://x"])
def test_requires_official_source_url(reg, url):
    sid = _add(reg)
    with pytest.raises(reg.SubjectValidationError):
        reg.record_official_name("BMP", sid, source_url=url, name_zh="丝芙兰")


def test_import_official_names_apply_needs_approval(reg, monkeypatch):
    from scripts import import_subject_registry_seed as seed
    from lumenis.system.security import permission
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False, raising=False)
    permission.reset_permission_gate()
    sid = _add(reg)
    rows = [{"domain_id": "BMP", "subject_id": sid, "name_zh": "丝芙兰", "source_url": "https://www.sephora.cn/"}]
    assert seed.import_official_names(rows)["mode"] == "dry_run"
    with pytest.raises(seed.SeedApprovalRequired):
        seed.import_official_names(rows, apply=True)
    with pytest.raises(seed.SeedIntegrityError):
        seed.import_official_names([{**rows[0], "source_url": ""}])

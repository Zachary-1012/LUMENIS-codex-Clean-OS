from __future__ import annotations

import pytest

from lumenis.system.collector.runtime import run_profile
from lumenis.system.collector.runtime import run_xhs_live


def test_xhs_collection_entrypoint_delegates_to_canonical_engine(monkeypatch):
    calls = []

    def fake_run_live(keyword, **kwargs):
        calls.append((keyword, kwargs))
        return {"ok": True, "notes": [], "stats": {"fetched": 0}}

    def fake_persist(data, subject_hit, **scope):
        assert callable(subject_hit)
        assert scope["domain_id"] == "cth"
        assert scope["subject_id"] == "GUANGZHOU_TAIKOO_HUI"
        return {"ok": True, "status": "success", "accepted": 0}

    monkeypatch.setattr(run_xhs_live, "run_live", fake_run_live)
    monkeypatch.setattr(run_xhs_live, "persist_live", fake_persist)

    result = run_xhs_live.run_keywords(
        ["  香港品牌  ", "", "商业运营"], account="XHS_RETINAUT",
        subject_hit=lambda _text: True, domain_id="cth", product_id="CTH",
        subject_id="GUANGZHOU_TAIKOO_HUI",
    )

    assert result["ok"] is True
    assert [item[0] for item in calls] == ["香港品牌", "商业运营"]
    assert all(item[1]["account"] == "XHS_RETINAUT" for item in calls)


def test_xhs_collection_entrypoint_does_not_collect_without_scope(monkeypatch):
    called = []
    monkeypatch.setattr(run_xhs_live, "run_live", lambda *_args, **_kwargs: called.append(True))
    result = run_xhs_live.run_keywords(["brand"], subject_hit=lambda _text: True)
    assert result["ok"] is False
    assert result["status"] == "scope_unavailable"
    assert called == []


def test_profile_cli_requires_explicit_brand_even_for_preview(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_profile", "--dry-run"])

    with pytest.raises(SystemExit) as exc:
        run_profile.main()

    assert exc.value.code == 2

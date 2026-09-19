from __future__ import annotations

from lumenis.system.collector.runtime import run_xhs_live


def test_xhs_collection_entrypoint_delegates_to_canonical_engine(monkeypatch):
    calls = []

    def fake_run_live(keyword, **kwargs):
        calls.append((keyword, kwargs))
        return {"ok": True, "notes": [], "stats": {"fetched": 0}}

    def fake_persist(data, subject_hit):
        assert callable(subject_hit)
        return {"ok": True, "status": "success", "accepted": 0}

    monkeypatch.setattr(run_xhs_live, "run_live", fake_run_live)
    monkeypatch.setattr(run_xhs_live, "persist_live", fake_persist)

    result = run_xhs_live.run_keywords(["  香港品牌  ", "", "商业运营"], account="XHS_RETINAUT")

    assert result["ok"] is True
    assert [item[0] for item in calls] == ["香港品牌", "商业运营"]
    assert all(item[1]["account"] == "XHS_RETINAUT" for item in calls)

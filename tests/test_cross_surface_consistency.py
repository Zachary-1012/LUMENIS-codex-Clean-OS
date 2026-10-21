"""Real loopback HTTP parity using current scope, Evidence and metric owners."""

from tests import http_consistency_fixture as fixtures

env = fixtures.env
http_scope = fixtures.http_scope


def test_canonical_api_sentiment_matches_db_same_window(http_scope, monkeypatch):
    ws = http_scope
    with ws["repository"].transaction() as con:
        con.execute(
            "UPDATE notes SET ai_filter_status='rejected' WHERE note_id='udip-positive'"
        )
    source = ws["daily"].db.get_scoped_event_source_rows(
        ws["scope"],
        source_types=("note", "web_mention"),
        date_start=ws["date"],
        date_end=ws["date"],
    )
    assert not source["truncated"] and source["rejected_count"] == 0
    effective = [
        row
        for row in source["sources"]
        if row["relevance_status"] in {"relevant", "accepted"}
    ]
    want = ws["cm"].sentiment_count(effective)
    status, got = ws["get"]("/api/metrics/canonical?date=" + ws["date"])
    assert status == 200 and got["ok"] is True
    assert got["context"]["positive_count"] == want["positive"] == 1
    assert got["context"]["neutral_count"] == want["neutral"] == 1
    assert got["context"]["effective_count"] == len(effective) == 4
    # A live request without scope is rejected, not silently assigned a scope.
    status, denied = ws["get"](
        "/api/metrics/canonical?date=" + ws["date"], context=False
    )
    assert status == 409 and denied["code"] == "DOMAIN_REQUIRED"
    with monkeypatch.context() as context:
        context.setitem(ws["app"].config, "LUMENIS_OPEN_WORKSPACE", False)
        status, denied = ws["get"]("/api/metrics/canonical?date=" + ws["date"])
        assert status == 403 and denied["code"] == "AUTH_REQUIRED"


def test_risk_index_present_in_canonical_api(http_scope):
    ws = http_scope
    status, got = ws["get"]("/api/metrics/canonical?date=" + ws["date"])
    assert status == 200 and got["ok"]
    for key, owner, name in [
        ("MET-RISK-01", "FUNC-RISK-01", "risk_index"),
        ("MET-RISK-02", "FUNC-RISK-02", "brand_health_score"),
    ]:
        assert got["metrics"][key]["function"] == owner
        assert got["metrics"][key]["name"] == name
        assert got["metrics"][key]["value"] is None  # unknown input is not zero
    with ws["repository"].transaction() as con:
        con.execute("UPDATE notes SET is_official=0")
        con.execute(
            "UPDATE notes SET sentiment='positive',risk_level='low' WHERE note_id='udip-unknown'"
        )
    expected = ws["daily"].generate_today_summary(ws["date"], scope=ws["scope"])
    status, got = ws["get"]("/api/metrics/canonical?date=" + ws["date"])
    assert status == 200
    for key, name in [
        ("MET-RISK-01", "risk_index"),
        ("MET-RISK-02", "brand_health_score"),
    ]:
        assert got["metrics"][key]["value"] == expected[name]
        assert 0.0 <= got["metrics"][key]["value"] <= 100.0


def test_empty_window_returns_zero_not_error(http_scope):
    status, got = http_scope["get"]("/api/metrics/canonical?date=1999-01-01")
    assert status == 200 and got["ok"] is True
    assert got["context"]["total_found"] == got["context"]["effective_count"] == 0
    assert got["context"]["events_count"] == 0
    # Empty classification/risk is unknown; measured count zero remains zero.
    assert got["context"]["positive_count"] is None
    assert got["context"]["neutral_count"] is None
    assert got["context"]["risk_count"] is None
    assert got["metrics"]["MET-RISK-01"]["value"] is None
    assert got["metrics"]["MET-RISK-02"]["value"] is None

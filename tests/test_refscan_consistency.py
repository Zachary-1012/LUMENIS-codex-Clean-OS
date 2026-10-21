"""Reference-scan HTTP counters agree with the same synthetic SQL snapshot."""

from tests import http_consistency_fixture as fixtures

env = fixtures.env
http_scope = fixtures.http_scope


def _canonical_brand_counts(repository):
    with repository.connection(read_only=True, wal=False) as con:
        return {
            "total": con.execute(
                "SELECT COUNT(*) FROM brand_industry_monitor"
            ).fetchone()[0],
            "negative": con.execute(
                "SELECT COUNT(*) FROM brand_industry_monitor WHERE negative_count>0"
            ).fetchone()[0],
            "positive": con.execute(
                "SELECT COUNT(*) FROM brand_industry_monitor WHERE positive_count>0"
            ).fetchone()[0],
        }


def test_brand_industry_stats_matches_canonical(http_scope):
    canon = _canonical_brand_counts(http_scope["repository"])
    status, got = http_scope["get"]("/api/brand-industry/stats")
    assert status == 200 and got["ok"] is True
    assert (
        {key: got[key] for key in canon}
        == canon
        == {"total": 4, "negative": 2, "positive": 2}
    )


def test_brand_industry_stats_consistent_across_views(http_scope):
    status, got = http_scope["get"]("/api/brand-industry/stats")
    assert status == 200 and got["ok"] is True
    assert got["total"] == got["total_brands"] == 4
    assert got["negative"] == got["negative_brands"] == 2
    assert got["positive"] == got["positive_brands"] == 2
    assert len(got["industries"]) == got["categories"] == 2
    assert sum(row["cnt"] for row in got["industries"]) == got["total"]

    with http_scope["repository"].transaction() as con:
        con.execute("DELETE FROM brand_industry_monitor")
    status, empty = http_scope["get"]("/api/brand-industry/stats")
    assert status == 200 and empty["ok"] is True
    assert (
        empty["total"]
        == empty["negative"]
        == empty["positive"]
        == empty["categories"]
        == 0
    )
    assert empty["industries"] == []
    with http_scope["repository"].transaction() as con:
        con.execute("DROP TABLE brand_industry_monitor")
    status, failed = http_scope["get"]("/api/brand-industry/stats")
    assert status == 500 and failed["ok"] is False
    assert failed["code"] == "BRAND_INDUSTRY_STATS_ERROR"

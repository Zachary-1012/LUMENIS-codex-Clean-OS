# -*- coding: utf-8 -*-
"""Shared Evidence Store 单元测试（使用临时数据库，不碰生产库）。"""
import sys, os, tempfile, json
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用临时数据库
from lumenis.shared.evidence import store as evidence_store
_tmp_db = tempfile.mktemp(suffix=".db")


@pytest.fixture(autouse=True)
def _clean_evidence_table_each_test(monkeypatch):
    """每个用例使用 Shared Database 当前路径契约指向独立临时库。"""
    monkeypatch.setenv("ZBC_DB_PATH", _tmp_db)
    evidence_store.init_evidence_store(_tmp_db)
    import sqlite3

    _c = sqlite3.connect(_tmp_db)
    try:
        _c.execute("DELETE FROM app_evidence_records")
        _c.commit()
    finally:
        _c.close()
    yield



def test_record_generic_evidence():
    eid = evidence_store.record_evidence(
        source="test", project="ZBC", product="CTH",
        feature_id="TEST_FEATURE", level="L4", test_name="test_generic",
        result="PASS", inputs={"a": 1}, outputs={"b": 2},
        actual="test passed", account="XHS_CN_PRIMARY", duration_ms=100,
    )
    assert eid > 0
    rows = evidence_store.query_evidence(feature_id="TEST_FEATURE")
    assert len(rows) == 1
    assert rows[0]["result"] == "PASS"
    assert rows[0]["account"] == "XHS_CN_PRIMARY"
    assert rows[0]["evidence_hash"] is not None
    print("PASS test_record_generic_evidence")


def test_record_collection_evidence_pass():
    eid = evidence_store.record_collection_evidence(
        account="XHS_CN_PRIMARY", platform="xhs",
        notes_collected=50, notes_filtered=10, notes_inserted=40, notes_updated=5,
        duration_ms=3500, result="PASS", session_state="logged_in",
        keywords=["太古汇", "奢侈品"],
    )
    assert eid > 0
    rows = evidence_store.query_evidence(feature_id="XHS_COLLECT", account="XHS_CN_PRIMARY")
    assert len(rows) >= 1
    row = rows[0]
    assert row["result"] == "PASS"
    assert row["level"] == "L8"
    assert "collected=50" in row["actual"]
    assert "session=logged_in" in row["actual"]
    print("PASS test_record_collection_evidence_pass")


def test_record_collection_evidence_fail():
    """采集异常必须落 FAIL，禁止以 0 条充当结果。"""
    eid = evidence_store.record_collection_evidence(
        account="XHS_RETINAUT", platform="xhs",
        notes_collected=0, notes_filtered=0, notes_inserted=0, notes_updated=0,
        duration_ms=1200, result="FAIL",
        error_type="CAPTCHA", error_message="需要验证码",
        session_state="needs_login",
    )
    assert eid > 0
    rows = evidence_store.query_evidence(feature_id="XHS_COLLECT", account="XHS_RETINAUT", result="FAIL")
    assert len(rows) >= 1
    row = rows[0]
    assert row["result"] == "FAIL"
    assert "error_type=CAPTCHA" in row["actual"]
    assert "collected=0" in row["actual"]  # 0条也要记录真实状态
    print("PASS test_record_collection_evidence_fail")


def test_collection_evidence_keeps_provider_source_and_collected_at(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        evidence_store,
        "record_evidence",
        lambda **kwargs: captured.update(kwargs) or 42,
    )

    result = evidence_store.record_collection_evidence(
        account="CTH_WEB_RSS_RUNTIME",
        platform="web_rss",
        result="PASS",
        feature_id="CTH_WEB_RSS_COLLECT",
        provider="google_news_rss",
        source="news.google.com/rss/search",
        collected_at="2026-09-15 12:00:00",
        collection_metadata={"api_key": "must-not-persist", "healthcheck_scope": "public"},
    )

    assert result == 42
    assert captured["feature_id"] == "CTH_WEB_RSS_COLLECT"
    assert captured["provider"] == "google_news_rss"
    assert captured["collection_metadata"]["source"] == "news.google.com/rss/search"
    assert captured["collection_metadata"]["collected_at"] == "2026-09-15 12:00:00"
    assert "api_key" not in captured["collection_metadata"]


def test_record_health_evidence():
    eid = evidence_store.record_health_evidence(
        account="XHS_CN_PRIMARY", level="L3", port=9222,
        port_alive=True, cdp_ws_ok=True, login_state="logged_in",
        cookie_count=70, result="PASS", detail="三层检查全部通过",
    )
    assert eid > 0
    rows = evidence_store.query_evidence(feature_id="RESIDENT_HEALTH", account="XHS_CN_PRIMARY")
    assert len(rows) >= 1
    row = rows[0]
    assert row["result"] == "PASS"
    assert "port=9222" in row["actual"]
    assert "cookies=70" in row["actual"]
    print("PASS test_record_health_evidence")


def test_record_health_evidence_needs_login():
    eid = evidence_store.record_health_evidence(
        account="XHS_RETINAUT", level="L3", port=9223,
        port_alive=True, cdp_ws_ok=True, login_state="needs_login",
        cookie_count=0, result="FAIL", detail="登录态失效，需要扫码",
    )
    assert eid > 0
    rows = evidence_store.query_evidence(feature_id="RESIDENT_HEALTH", result="FAIL")
    assert len(rows) >= 1
    print("PASS test_record_health_evidence_needs_login")


def test_query_filters():
    # 先确保有数据
    evidence_store.record_evidence(source="test", feature_id="FILTER_TEST", level="L4", result="PASS", account="XHS_CN_PRIMARY")
    evidence_store.record_evidence(source="test", feature_id="FILTER_TEST", level="L4", result="FAIL", account="XHS_RETINAUT", actual="test fail")
    # 按 result 过滤
    pass_rows = evidence_store.query_evidence(result="PASS", limit=100)
    fail_rows = evidence_store.query_evidence(result="FAIL", limit=100)
    assert len(pass_rows) > 0
    assert len(fail_rows) > 0
    assert all(r["result"] == "PASS" for r in pass_rows)
    assert all(r["result"] == "FAIL" for r in fail_rows)

    # 按 account 过滤
    primary_rows = evidence_store.query_evidence(account="XHS_CN_PRIMARY", limit=100)
    assert len(primary_rows) > 0
    assert all(r["account"] == "XHS_CN_PRIMARY" for r in primary_rows)
    print("PASS test_query_filters")


def test_get_stats():
    # 先确保有数据
    evidence_store.record_evidence(source="test", feature_id="STATS_TEST", level="L4", result="PASS", account="XHS_CN_PRIMARY")
    evidence_store.record_evidence(source="test", feature_id="STATS_TEST", level="L4", result="FAIL", account="XHS_RETINAUT", actual="stats fail test")
    stats = evidence_store.get_stats()
    assert stats["total"] > 0
    assert "PASS" in stats["by_result"]
    assert "FAIL" in stats["by_result"]
    assert "XHS_CN_PRIMARY" in stats["by_account"]
    assert len(stats["recent"]) > 0
    print(f"PASS test_get_stats (total={stats['total']})")


def test_evidence_hash_dedup():
    """相同内容生成相同哈希，可用于去重。"""
    eid1 = evidence_store.record_evidence(
        source="test", feature_id="DEDUP_TEST", level="L4",
        result="PASS", account="XHS_CN_PRIMARY",
    )
    eid2 = evidence_store.record_evidence(
        source="test", feature_id="DEDUP_TEST", level="L4",
        result="PASS", account="XHS_CN_PRIMARY",
    )
    rows1 = evidence_store.query_evidence(feature_id="DEDUP_TEST", limit=10)
    hashes = {r["evidence_hash"] for r in rows1}
    assert len(hashes) == 1  # 相同内容哈希相同
    print("PASS test_evidence_hash_dedup")


def test_safe_identifier():
    """验证 _safe_identifier 拒绝非法标识符，接受合法表名/列名。"""
    from lumenis.shared.evidence import store as es
    # 合法标识符
    assert es._safe_identifier("notes") == "notes"
    assert es._safe_identifier("app_evidence_records") == "app_evidence_records"
    assert es._safe_identifier("col_1") == "col_1"
    assert es._safe_identifier("_private") == "_private"
    # 非法标识符（含注入字符）
    import pytest
    with pytest.raises(ValueError):
        es._safe_identifier("notes; DROP TABLE users;--")
    with pytest.raises(ValueError):
        es._safe_identifier("notes WHERE 1=1")
    with pytest.raises(ValueError):
        es._safe_identifier("")
    with pytest.raises(ValueError):
        es._safe_identifier(None)
    with pytest.raises(ValueError):
        es._safe_identifier("1bad")
    print("PASS test_safe_identifier")

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print("\n" + "=" * 50)
    print(f"Total: {len(tests)}, Passed: {passed}, Failed: {failed}")
    try:
        os.unlink(_tmp_db)
    except Exception:
        pass
    sys.exit(1 if failed else 0)

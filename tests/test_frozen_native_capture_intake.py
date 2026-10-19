import hashlib
import json
from copy import deepcopy
from pathlib import Path
import pytest
from lumenis.system.collector.adapters import secondary_collection as entry

SOURCE = Path(__file__).parent / "fixtures/collector/native_public_captures_20261004.json"
def observed(platform):
    raw=SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=="09ca00b375db2367e359c62844b811f5fdfe0abb67f2faba1a8bab61f82d5c85"
    return next(r for r in json.loads(raw)["records"] if r["platform"]==platform)
def capture(record):
    raw=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return entry.NativePublicCapture(record["platform"],raw,hashlib.sha256(raw).hexdigest())

def test_actual_originals_preserve_body_time_native_ids_and_missing_metrics():
    ig=observed("instagram");item=entry._native_capture_collection(capture(ig)).items[0]
    assert item["content"]==ig["body"] and item["platform_content_id"]=="3950357121996910485"
    assert item["raw"]["_native_original"]["original_capture_time"]=="2026-10-03T19:26:01.058401+00:00"
    assert item["likes"]==3853 and item["views"] is None and item["collects"] is None
    hk=observed("xiaohongshu");item=entry._native_capture_collection(capture(hk)).items[0]
    assert item["content"]==hk["body"] and "#深圳万象城" in item["content"]
    assert item["author_id"]=="59412fe982ec39155a11c3db" and item["publish_datetime"] is None

def test_actual_X_metrics_keep_native_zero_and_bookmark_repost_meaning():
    item=entry._native_capture_collection(capture(observed("x"))).items[0]
    assert item["content"].startswith("新入荷")
    assert item["raw"]["reply_count"]==0 and item["raw"]["bookmark_count"]==0
    assert item["raw"]["retweet_count"]==1 and item["raw"]["view_count"]==947
    assert item["collects"] is None and item["raw"]["bookmark_native_metric_name"]=="bookmark_count"

def test_actual_douyin_detail_metrics_bind_their_own_capture_and_keep_old_stats():
    item=entry._native_capture_collection(capture(observed("douyin"))).items[0]
    assert item["likes"]==97 and item["raw"]["digg_count"]==97
    assert item["raw"]["statistics"]["digg_count"]==96
    assert item["raw"]["_native_original"]["original_capture_time"]=="2026-10-03T21:45:51.179812+00:00"

@pytest.mark.parametrize("platform",["facebook","wechat"])
def test_preview_and_unrecorded_capture_are_not_silently_completed(platform,monkeypatch):
    cap=capture(observed(platform))
    monkeypatch.setattr(entry,"_manual_collection_guard",lambda *a,**kw:pytest.fail("invalid source reached admission"))
    result=entry.collect_search(platform,observed(platform)["source_url"],native_capture=cap)
    expected="NATIVE_BODY_UNAVAILABLE" if platform=="facebook" else "SOURCE_CAPTURE_TIME_UNAVAILABLE"
    assert result["status"]==expected and result["persistence_attempted"] is False

def test_digest_approval_changes_when_original_body_changes():
    original=observed("x");first=capture(original)
    changed=deepcopy(original);changed["body"]+=" changed"
    changed["body_sha256"]=hashlib.sha256(changed["body"].encode()).hexdigest()
    second=capture(changed)
    assert entry.native_capture_permission_keyword(first)!=entry.native_capture_permission_keyword(second)

def test_frozen_intake_requires_real_guard_and_never_contacts_adapter_before_approval(monkeypatch):
    record=observed("x");cap=capture(record);seen=[]
    def denied(actor,scope,platform,keyword,limit, *, max_scroll=None):
        assert max_scroll is None
        seen.append((platform,keyword))
        return None,{"ok":False,"status":"AUTH_REQUIRED"}
    monkeypatch.setattr(entry,"_manual_collection_guard",denied)
    monkeypatch.setattr(entry,"_adapter_health",lambda *a,**kw:pytest.fail("frozen source contacted browser"))
    monkeypatch.setattr(entry,"_get_runtime_adapter",lambda *a,**kw:pytest.fail("frozen source contacted browser"))
    result=entry.collect_search("x",record["source_url"],native_capture=cap)
    assert result["status"]=="AUTH_REQUIRED"
    assert seen==[("x",entry.native_capture_permission_keyword(cap))]

def test_bytes_and_platform_mismatch_rejected_before_permission(monkeypatch):
    record=observed("x");good=capture(record)
    cap=entry.NativePublicCapture("x",good.content+b" ","0"*64)
    monkeypatch.setattr(entry,"_manual_collection_guard",lambda *a,**kw:pytest.fail("tampered input reached permission"))
    assert entry.collect_search("x",record["source_url"],native_capture=cap)["status"]=="INVALID_NATIVE_CAPTURE"

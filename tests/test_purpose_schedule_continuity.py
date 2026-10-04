import hashlib
import hmac
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from lumenis.system.collector.acquisition_plan import build_acquisition_plan
from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
    PublicBaselinePlan, PURPOSE_POLICY, BaselineConfigError, _canonical_config,
    load_prelaunch_baseline_config, maintenance_authorization,
    run_due_prelaunch_baseline, round_robin_due,
)
from lumenis.system.collector.adapters.scheduling.store import ScheduleDecisionStore

NOW = datetime(2026, 10, 4, tzinfo=timezone.utc)
KEY = "DISPOSABLE_UNIT_ONLY_NEVER_OWNER_ADMISSION"
def query(platform, term="新品"):
    rows = [{"subject_id":"SUBJ-NIKE","subject_type":"brand","domain_id":"BMP",
             "brand_focus_id":"BRAND-NIKE","name_en":"Nike","status":"active"}]
    request = {"domain_id":"BMP","scope_key":"BRAND-NIKE","aliases":["Nike"],
               "purpose":"中国产品内容核读","dimension":"market_activity",
               "platforms":[platform],"topic_terms":[term],"geography_terms":["中国"]}
    return build_acquisition_plan(business_requests=[request],registry_loader=lambda:rows).queries[0]
def source(platform="douyin", term="新品"):
    q = query(platform, term)
    return {"source_key":platform+":"+term,"source_version":"source/1",
            "scope_version":"scope/1","cadence_seconds":3600,"authorization_ref":"unit-review-approved",
            "platform":platform,"source_url":q.keyword,"domain_id":"bmp",
            "subject_id":None,"brand_focus_id":"BRAND-NIKE","plan_version":"seed-1",
            "purpose_query":q.to_dict()}
def signed(path, sources, **overrides):
    config = {"schema_version":1,"enabled":True,"end_user_auto":False,
              "internal_auto_opt_in":True,"policy_id":PURPOSE_POLICY,
              "plan_version":"seed-1","sources":sources, **overrides}
    config["hmac"]={"algorithm":"HMAC-SHA256","value":hmac.new(KEY.encode(),_canonical_config(config),hashlib.sha256).hexdigest()}
    path.write_text(json.dumps(config,ensure_ascii=False),encoding="utf-8")
    return config

def test_explicit_internal_optin_and_signature_required(tmp_path):
    path=tmp_path/"config.json"
    signed(path,[source()],internal_auto_opt_in=False)
    with pytest.raises(BaselineConfigError):load_prelaunch_baseline_config(str(path),hmac_key=KEY)


    signed(path,[source()])
    with pytest.raises(BaselineConfigError):load_prelaunch_baseline_config(str(path),hmac_key="wrong")
    loaded=load_prelaunch_baseline_config(str(path),hmac_key=KEY)
    assert loaded["plans"][0].internal_auto_opt_in is True
    assert loaded["plans"][0].end_user_auto is False

def test_query_scope_period_and_version_bound(tmp_path):
    path=tmp_path/"config.json";original=source()
    signed(path,[original]);plan=load_prelaunch_baseline_config(str(path),hmac_key=KEY)["plans"][0]
    changed=source(term="联名");signed(path,[changed])
    nextplan=load_prelaunch_baseline_config(str(path),hmac_key=KEY)["plans"][0]
    assert nextplan.plan_id != plan.plan_id
    assert not maintenance_authorization(plan).matches(nextplan,source_url=nextplan.source_url,
        platform=nextplan.platform,scope={"domain_id":"bmp","subject_id":None,"brand_focus_id":"BRAND-NIKE"})
    changed["purpose_query"]["business_context"]["publication_since"]="2025-01-01"
    signed(path,[changed])
    with pytest.raises(BaselineConfigError):load_prelaunch_baseline_config(str(path),hmac_key=KEY)

def test_source_and_query_scope_disagreement_rejected(tmp_path):
    path=tmp_path/"config.json";s=source();s["brand_focus_id"]="BRAND-OTHER"
    signed(path,[s])
    with pytest.raises(BaselineConfigError):load_prelaunch_baseline_config(str(path),hmac_key=KEY)

def test_existing_store_claims_once_reopens_and_backs_off(tmp_path):
    path=tmp_path/"config.json";signed(path,[source()])
    plan=load_prelaunch_baseline_config(str(path),hmac_key=KEY)["plans"][0]
    db=str(tmp_path/"existing-schedule.db")
    first=ScheduleDecisionStore(db);attempt,decision=first.claim_public_baseline_attempt(plan,now=NOW)
    assert attempt and decision.due
    other=ScheduleDecisionStore(db)
    duplicate,decision=other.claim_public_baseline_attempt(plan,now=NOW)
    assert duplicate is None and decision.reason=="ATTEMPT_IN_PROGRESS"
    assert other.finish_public_baseline_attempt(plan,attempt,success=False,now=NOW,error_code="NEED_VERIFY")
    _,decision=ScheduleDecisionStore(db).claim_public_baseline_attempt(plan,now=NOW+timedelta(seconds=1))
    assert decision.reason=="RETRY_BACKOFF"
    resumed,decision=ScheduleDecisionStore(db).claim_public_baseline_attempt(plan,now=NOW+timedelta(seconds=301))
    assert resumed != attempt and decision.reason=="RETRY_DUE"

def test_rotates_platforms_and_isolates_challenge_with_durable_history(tmp_path):
    path=tmp_path/"config.json"
    signed(path,[source("douyin","新品"),source("douyin","联名"),source("x","新品"),source("instagram","新品")])
    seen=[]
    def collect(platform,keyword,**kw):
        seen.append((platform,keyword,kw))
        if platform=="douyin":
            return {"ok":False,"status":"NEED_VERIFY"}
        return {"ok":True,"status":"SUCCESS","returned_count":1,"canonical_synced":1,
                "evidence_recorded":True,"refresh_verified":True,"scope_status":"VERIFIED"}
    store=ScheduleDecisionStore(str(tmp_path/"schedule.db"))
    result=run_due_prelaunch_baseline(config_path=str(path),hmac_key=KEY,store=store,
                                    now=NOW,finish_now=lambda:NOW,collect=collect)
    assert set(p for p,_,_ in seen)=={"douyin","x","instagram"}
    assert "x" in [p for p,_,_ in seen[:3]]
    assert result["summary"]["failed"]==1 and result["summary"]["succeeded"]==2
    assert result["summary"]["deferred"]==1
    assert all(kw["business_query"].keyword==term and kw["prelaunch_authorization"].signature_verified for _,term,kw in seen)
    seen.clear()
    repeated=run_due_prelaunch_baseline(config_path=str(path),hmac_key=KEY,store=ScheduleDecisionStore(store.db_path),
                                      now=NOW+timedelta(seconds=1),collect=collect)
    assert not seen and repeated["summary"]["deferred"]==4

def test_unsigned_tampering_never_calls_collector(tmp_path):
    path=tmp_path/"config.json";config=signed(path,[source()])
    config["sources"][0]["source_url"]="another keyword"
    path.write_text(json.dumps(config),encoding="utf-8")
    result=run_due_prelaunch_baseline(config_path=str(path),hmac_key=KEY,
        store=ScheduleDecisionStore(str(tmp_path/"schedule.db")),
        now=NOW,collect=lambda *a,**kw:pytest.fail("tampered plan attempted collection"))
    assert result["status"]=="FAILED"

def test_old_public_policy_cannot_enable_social_purpose(tmp_path):
    path=tmp_path/"config.json"
    signed(path,[source()],policy_id="public-read-only-exact-import-v1")
    with pytest.raises(BaselineConfigError):load_prelaunch_baseline_config(str(path),hmac_key=KEY)




def test_compiled_pages_keep_all_queries_and_disable_until_owner_signature(tmp_path):
    from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import purpose_baseline_config
    qs=[query("douyin","新品"),query("x","联名"),query("instagram","城市香")]
    pages=[{"status":"READY","queries":[q.to_dict() for q in qs[:2]]},
           {"status":"READY","queries":[q.to_dict() for q in qs[2:]]}]
    config=purpose_baseline_config(pages,source_version="native-1",scope_version="registry-1",
                                 authorization_ref="owner-pending")
    assert len(config["sources"])==3 and config["enabled"] is False and config["hmac"] is None
    assert {s["platform"] for s in config["sources"]}=={"douyin","x","instagram"}
    path=tmp_path/"unsigned.json";path.write_text(json.dumps(config),encoding="utf-8")
    assert load_prelaunch_baseline_config(str(path),hmac_key=KEY)["status"]=="DISABLED"


def test_actual_reviewed_100_seed_compiles_with_originals_and_no_implicit_admission(tmp_path):
    from lumenis.system.collector.acquisition_plan import load_approved_topic_seed, APPROVED_TOPIC_SEED_SHA256
    from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import purpose_baseline_config
    from lumenis.system.collector.adapters.platform_naming import normalize_platform
    seed = load_approved_topic_seed()
    requests, rows = [], []
    for index, entity in enumerate(seed['metadata']['confirmed_entities']):
        domain = 'CTH' if index < 2 else 'BMP'
        rows.append({'domain_id': domain, 'subject_id': f'SUBJ-{index}',
                     'brand_focus_id': None if index < 2 else f'BRAND-{index}',
                     'subject_type': 'company' if index < 2 else 'brand',
                     'name_zh': entity, 'name_en': entity, 'status': 'active'})
    for topic in seed['topics']:
        row = next(row for row in rows if row['name_zh'] == topic['entity'])
        requests.append({'domain_id': row['domain_id'],
            'scope_key': row['brand_focus_id'] or row['subject_id'], 'aliases': [topic['entity']],
            'platforms': [normalize_platform(topic['platform'])],
            'purpose': 'Explicit isolated seed compilation check', 'dimension': 'market_activity',
            'topic_terms': [topic['topic']], 'user_seed_topic_ref': {
                'input_sha256': APPROVED_TOPIC_SEED_SHA256, 'topic_id': topic['id'],
                'source_id': topic['source_id'], 'source_url': topic['source_url'],
                'term_preserved': topic['topic'], 'literal': topic['observed_literal']}})
    pages, cursor = [], None
    while True:
        page = build_acquisition_plan(business_requests=requests, registry_loader=lambda: rows,
                                      continuation=cursor).to_dict()
        pages.append(page)
        cursor = page['next_cursor']
        if cursor is None:
            break
    config=purpose_baseline_config(pages,source_version=APPROVED_TOPIC_SEED_SHA256,
        scope_version="isolated-current-registry",authorization_ref="CURRENT_OWNER_SIGNATURE_PENDING",
        plan_version="user-seed-20261004")
    assert len(seed['topics']) == len(requests) == 100
    assert len(seed['sources']) == 41
    assert {q['business_context']['user_seed_topic_ref']['topic_id'] for page in pages for q in page['queries']} == {t['id'] for t in seed['topics']}
    assert all(t['heat_value'] is None and t['trend_rank'] is None for t in seed['topics'])
    assert config["enabled"] is False and config["hmac"] is None
    assert {s["platform"] for s in config["sources"]}=={"xhs","douyin","x","instagram","facebook","wechat"}
    target=tmp_path/"unsigned-purpose-schedule.json"
    target.write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert load_prelaunch_baseline_config(str(target),hmac_key=KEY)['status'] == 'DISABLED'

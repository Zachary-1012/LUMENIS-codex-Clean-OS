from types import SimpleNamespace
import pytest
import collector
from lumenis.system.collector import acquisition_plan as planner

def test_collector_keeps_all_sixteen_requested_queries_and_unlimited_detail_setting(monkeypatch):
    requested=["耐克中国消费者体验"+str(i) for i in range(16)]
    rows=[{"subject_id":"SUBJ-UNIT-"+str(i),"subject_type":"company","domain_id":"CTH","name_zh":term,"status":"active"} for i,term in enumerate(requested)]
    real = planner.build_acquisition_plan
    monkeypatch.setattr(planner,"build_acquisition_plan",
                        lambda *a,**kw: real(*a,registry_loader=lambda:rows,**kw))
    monkeypatch.setattr(collector,"_collection_policy_gate",lambda **kw:{"ok":True,"account":"UNIT_APPROVED_HK"})
    policy=SimpleNamespace(can_run_kind=lambda _:True,auto_run_enabled=False,human_cadence={})
    monkeypatch.setattr(collector,"_rednote_policy",SimpleNamespace(effective_policy=lambda:policy))
    monkeypatch.setattr(collector,"_get_xhs_guard",lambda:object())
    monkeypatch.setattr(collector,"_get_xhs_risk_engine",lambda:SimpleNamespace(snapshot=lambda:{"lifecycle_action":"schedule_normal"}))
    monkeypatch.setattr(collector,"_feed_risk_engine",lambda *a,**kw:False)
    import lumenis.system.collector.guard.schedule_adapter as scheduling
    monkeypatch.setattr(scheduling,"schedule_sleep_seconds",lambda *a,**kw:0)
    calls=[]
    def collect_one(guard,keyword,max_scroll,max_details,account):
        calls.append((keyword,max_details))
        return SimpleNamespace(should_stop=False,state="NORMAL"),{
            "total":1,"notes":[{"note_id":"unit-"+str(len(calls)),"content":keyword}]}
    monkeypatch.setattr(collector,"_collect_one_keyword",collect_one)
    notes,results=collector.collect_all(requested,max_details=0,account="UNIT_APPROVED_HK")
    assert len(calls)==16 and {kw for kw,_ in calls}==set(requested)
    assert all(limit==0 for _,limit in calls)
    assert len(notes)==16 and results[-1]["pending_queries"]==[]
    assert results[-1]["coverage_complete"] is False

# -*- coding: utf-8 -*-
"""统一动态调度层单测（对齐《采集调度与风控最终执行指令》第十六节关键验收项）。

纯逻辑 + 临时 DB，不触网、不起浏览器、不依赖 AI。直接运行：
    .venv\\Scripts\\python.exe tests\\test_scheduling.py
"""
import os
import sys
import tempfile
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.system.collector.adapters.scheduling import (
    PlatformSchedulePolicy, ScheduleDecider, PlatformScheduleState,
    PlatformSchedulePlanner, ScheduleDecisionStore, state_map as sm,
)


def xhs_policy(**kw):
    p = PlatformSchedulePolicy(platform="xhs", name="小红书", enabled=True, priority="primary")
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def decider(**kw):
    return ScheduleDecider(xhs_policy(**kw))


results = []
def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


t0 = datetime(2026, 8, 30, 12, 0, 0)

# 1. 首次运行放行
d = decider()
r = d.decide(now=t0)
check("1 首次运行允许", r.allow and r.reason_code == "FIRST_RUN" and r.next_run_at)

# 2. SUCCESS 后未到动态间隔则等待，到点放行且 next_run_at 正确
d.record_result(sm.CS.SUCCESS, now=t0, items_found=5)
r_wait = d.decide(now=t0 + timedelta(seconds=1800))   # 30min < normal 60min
r_due = d.decide(now=t0 + timedelta(seconds=3600))
check("2 未到间隔等待", (not r_wait.allow) and r_wait.reason_code == "WAIT_INTERVAL")
check("2 到点放行", r_due.allow and r_due.reason_code == "RUN_DUE")
expect_next = (t0 + timedelta(seconds=3600 + 3600)).strftime("%Y-%m-%d %H:%M:%S")
check("2 next_run_at正确", r_due.next_run_at == expect_next)

# 3. 连续 NO_NEW_DATA 间隔延长（不为证明在工作而高频）
d = decider()
d.record_result(sm.CS.NO_NEW_DATA, now=t0)
i1 = d.state.current_interval
d.record_result(sm.CS.NO_NEW_DATA, now=t0 + timedelta(seconds=i1))
i2 = d.state.current_interval
d.record_result(sm.CS.NO_NEW_DATA, now=t0 + timedelta(seconds=i1 + i2))
i3 = d.state.current_interval
check("3 无新数据间隔递增且封顶", i1 == 5400 and i2 > i1 and i3 >= i2 and i3 <= 21600)

# 4. RISK_WARNING 降频（间隔被拉长）
d = decider()
d.record_result(sm.CS.RISK_WARNING, now=t0)
check("4 轻度风险降频", d.state.current_interval == int(3600 * 1.5))

# 5. NEED_VERIFY -> 等人，验证必需，不自动给恢复时间
d = decider()
d.record_result(sm.CS.NEED_VERIFY, now=t0)
r = d.decide(now=t0 + timedelta(hours=5))
check("5 人机验证保持暂停等人", (not r.allow) and r.reason_code == "AWAIT_HUMAN"
      and r.verification_required and r.next_run_at is None)

# 6. SESSION_EXPIRED -> A 类等人
d = decider()
d.record_result(sm.CS.SESSION_EXPIRED, now=t0)
r = d.decide(now=t0 + timedelta(hours=2))
check("6 登录失效弹Auth不自动重试", not r.allow and r.verification_required)

# 7. BLOCKED(300012) -> 冷却，冷却内拒绝，冷却后才放行，且不是“扫码可解”
d = decider()
d.record_result(sm.CS.BLOCKED, now=t0)
r_in = d.decide(now=t0 + timedelta(seconds=100))
r_after = d.decide(now=t0 + timedelta(seconds=901))
check("7 熔断冷却中拒绝", not r_in.allow and r_in.reason_code == "IN_COOLDOWN"
      and not r_in.verification_required)
check("7 冷却结束后可再评估", r_after.allow)

# 8. NETWORK_ERROR 退避递增，连续达阈值进入冷却
d = decider()
d.record_result(sm.CS.NETWORK_ERROR, now=t0)
b1 = d.state.current_interval
d.record_result(sm.CS.NETWORK_ERROR, now=t0 + timedelta(seconds=b1))
b2 = d.state.current_interval
d.record_result(sm.CS.NETWORK_ERROR, now=t0 + timedelta(seconds=b1 + b2))
check("8 网络退避递增且封顶", b1 == 60 and b2 == 120 and d.state.current_interval <= 900
      and d.state.cooldown_until is not None)

# 9. 恢复渐进：人工恢复后先低频试探，连续成功 N 次才回正常
d = decider()
d.record_result(sm.CS.BLOCKED, now=t0)
d.mark_human_resolved(now=t0 + timedelta(seconds=1000))
check("9a 恢复先低频试探", d.state.current_interval == 1800 and d.state.in_recovery)
d.record_result(sm.CS.SUCCESS, now=t0 + timedelta(seconds=1000 + 1800), items_found=1)
check("9b 试探期未回最高频", d.state.current_interval == 1800 and d.state.recovery_streak == 1)
d.record_result(sm.CS.SUCCESS, now=t0 + timedelta(seconds=1000 + 3600), items_found=1)
d.record_result(sm.CS.SUCCESS, now=t0 + timedelta(seconds=1000 + 5400), items_found=1)
check("9c 连续稳定后回正常", not d.state.in_recovery and d.state.current_interval == 3600)

# 10. 热点可提频但不突破平台硬上限 min_interval
d = decider()
d.record_result(sm.CS.SUCCESS, now=t0, items_found=1)
normal = d.decide(now=t0 + timedelta(seconds=1800))             # 非热点：30min < 正常60min，等待
hot = d.decide(now=t0 + timedelta(seconds=1800), is_hotspot=True)  # 热点：目标1200s，30min已过
check("10 非热点不提前", not normal.allow)
check("10 热点提频且不破硬上限", hot.allow and hot.target_interval_sec >= 1200)

# 11. 平台隔离：一个平台熔断不影响另一个平台
pol = {"a": PlatformSchedulePolicy(platform="a", enabled=True, normal_interval=600,
                                   min_interval=300, max_interval=3600),
       "b": PlatformSchedulePolicy(platform="b", enabled=True, normal_interval=600,
                                   min_interval=300, max_interval=3600)}
pl = PlatformSchedulePlanner(policies=pol)
pl.record_result("a", "BLOCKED", now=t0)
ra = pl.decide("a", now=t0 + timedelta(seconds=10))
rb = pl.decide("b", now=t0)
check("11 平台隔离互不影响", (not ra.allow) and rb.allow)

# 12. 未启用平台不放行（抖音/微博等扩展槽）
pl2 = PlatformSchedulePlanner()
r = pl2.decide("douyin", now=t0)
check("12 未启用平台拒绝", not r.allow and r.reason_code == "PLATFORM_DISABLED")

# 12b. 序境采集硬边界：自动<=60min / 手动<=30min 构造夹紧；自动时间槽固定 00:00/12:00
p_cap = PlatformSchedulePolicy(platform="xhs", name="小红书", enabled=True,
                               run_duration_auto=99999, run_duration_manual=99999)
check("12b 自动时长夹紧60min", p_cap.run_duration_auto == 3600)
check("12b 手动时长夹紧30min", p_cap.run_duration_manual == 1800)
check("12b 自动时间槽固定", p_cap.auto_slots == ("00:00", "12:00"))
check("12b 默认关闭(UI隐藏)", PlatformSchedulePolicy(platform="xhs").enabled is False)

# 13. 状态映射统一 + 三类分清
check("13a 小写success兼容", sm.to_canonical("success", items=3) == sm.CS.SUCCESS)
check("13b 空结果区分NO_NEW", sm.to_canonical("success", items=0) == sm.CS.NO_NEW_DATA)
check("13c 300012为C类熔断", sm.incident_class(sm.to_canonical(None, xhs_code="IP_RISK_OR_300012")) == sm.CLASS_C_RISK)
check("13d 登录失效为A类", sm.incident_class(sm.to_canonical("AUTH_REQUIRED")) == sm.CLASS_A_AUTH)
check("13e 验证码为B类", sm.incident_class(sm.to_canonical("CAPTCHA")) == sm.CLASS_B_VERIFY)
check("13f 风控态必须停请求", sm.is_stop_request(sm.CS.BLOCKED) and sm.is_stop_request(sm.CS.NEED_VERIFY))
check("13g 网络态走退避非0条", sm.is_network(sm.to_canonical("NETWORK_ERROR")))
check("13h AUTH_FAILED归A类登录失效", sm.to_canonical("AUTH_FAILED") == sm.CS.SESSION_EXPIRED and sm.incident_class(sm.to_canonical("AUTH_FAILED")) == sm.CLASS_A_AUTH)
check("13i 部分拦截归RISK_WARNING", sm.to_canonical("PARTIAL_BLOCKED") == sm.CS.RISK_WARNING)

# 14/15. 旁路决策表：幂等建表、字段完整、绝不影响旧表
tmpdir = tempfile.mkdtemp()
dbp = os.path.join(tmpdir, "t.db")
store = ScheduleDecisionStore(dbp)
store.ensure_schema(); store.ensure_schema()  # 幂等
rid = store.record(platform="xhs", allow=False, scheduler_decision="熔断冷却中",
                   result_status="BLOCKED", next_run_at="2026-08-30 12:15:00",
                   cooldown_until="2026-08-30 12:15:00", verification_required=False,
                   trigger_source="shadow", risk_status="CIRCUIT/COOLDOWN")
rows = store.recent("xhs")
cols = {r[1] for r in sqlite3.connect(dbp).execute("PRAGMA table_info(schedule_decisions)")}
need = {"platform", "result_status", "next_run_at", "cooldown_until", "scheduler_decision",
        "trigger_source", "verification_required", "risk_status", "allow"}
check("14 决策审计表字段齐全", rid and rows and need.issubset(cols))
check("15 决策原因可追溯(为什么没采集)", rows[0]["scheduler_decision"] == "熔断冷却中"
      and rows[0]["next_run_at"] and rows[0]["allow"] == 0)

# 端到端：planner + store 影子评估
pl3 = PlatformSchedulePlanner(state_file=os.path.join(tmpdir, "s.json"), store=store)
ev = pl3.shadow_evaluate(now=t0)
check("E2E 影子仅评估启用平台", [e.platform for e in ev] == ["xhs"] and ev[0].allow)
pl3.record_result("xhs", "success", now=t0, items_found=2)
pl4 = PlatformSchedulePlanner(state_file=os.path.join(tmpdir, "s.json"))  # 重启
check("E2E 调度状态持久化", pl4.decider("xhs").state.last_items_found == 2)

fails = [n for n, ok in results if not ok]
print(f"\n总计 {len(results)} 项，失败 {len(fails)} 项")
if fails:
    print("FAILED:", fails); sys.exit(1)
print("ALL_SCHEDULING_TESTS_PASS")

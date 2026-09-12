# -*- coding: utf-8 -*-
"""CTH domain screens CTH-01..10. CTH-01 is the second benchmark screen."""
from specutil import *
SPECS={}

SPECS["CTH-01"]={
 "titleKey":"screen.CTH-01","patterns":["PAT-DATA-01","PAT-EVD-01","PAT-NAV-01"],"motions":["M01","M03","M08","M14"],
 "sections":[
  head("CTH · 序境·商业运营","商业运营总览","以当前 Subject 为上下文：核心指标 → 趋势 → 事件/证据 → 洞察 → 决策行动，全部可追溯。",
       titleKey="screen.CTH-01",
       actions=[btn("生成运营简报","primary","report",act="draft-brief",cls="DRAFT",scope="subject:current",target="report",perm="report:write"),
                btn("切换时间范围","secondary","calendar"),btn("导出","ghost","download",act="export-overview",cls="QUERY")]),
  kpis([
    metric("今日到店客流",38214,icon="production",spark=SPARK12,source="EV: footfall.canonical",delta=6.2,decimals=0),
    metric("会员销售占比",41.8,unit="%",icon="trend",spark=SPARK7,source="EV: sales.canonical",delta=2.1,decimals=1),
    metric("在线负面声量",46,icon="risk",spark=SPARK7B,source="EV: sentiment.canonical",delta=-12,deltaUnit=""),
    metric("在办事件",9,icon="event",source="EV: event.open",fresh="m5")]),
  split([
    chart("近 30 天客流 vs 销售指数","line",series=[
      {"data":[62,66,64,70,74,71,78,82,80,86,90,88],"color":"var(--lum-c-brand-500)"},
      {"data":[40,44,43,49,52,50,55,58,57,61,65,63],"color":"var(--lum-c-success)"}],labels=DAYS30,
      legend=[{"label":"客流指数","color":"var(--lum-c-brand-500)"},{"label":"销售指数","color":"var(--lum-c-success)"}]),
    events("最新事件",[
      evt("10:22","北区 18–21 点离场排队回升","停车相关讨论 +24，风险分上行。","09-10","high",["停车","北区"],"EV-7710"),
      evt("09:05","新品牌快闪开业","L2 西区快闪首日客流 +31%。","09-10","low",["品牌","活动"],"EV-7706"),
      evt("昨日","会员日 Campaign 复盘归档","ROI 1:4.2，证据已归档。","09-09","low",["Campaign"],"EV-7688")]),
    evidence("关键证据链",[
      ev("Metric","EV-7701",["Source","Canonical","Metric","VM"],"今日客流 38,214，环比 +6.2%，口径=已去重闸机。","10:00","footfall",99),
      ev("Finding","EV-7704",["Comment","Cluster","Finding"],"停车体验簇占负面 30.8%。","09:31","cluster.rule",93)]),
  ],[
    insight("离场高峰的停车摩擦正在抵消晚间促销带来的客流增量，建议 18–21 点增派引导并开放 B3 备用通道。",
            why="依据 EV-7701/7704/7710：客流升但负面同向升，时间重合度 47%。",kind="决策建议",
            cites=["EV-7701","EV-7704","EV-7710"],actions=[btn("生成处置 Case","secondary","case",act="mk-case",cls="DRAFT")]),
    risks([risk("high","停车/离场摩擦","晚高峰集中，风险分 72。",72,"EV-7710"),
           risk("med","会员复购下滑","近 7 日复购率 -2.4pt。",46,"EV-7699")]),
    actions("建议行动",[
      act("open-event","打开事件 EV-7710","NAVIGATION",icon="event",target="CTH-04"),
      act("draft-action","起草引导排班调整","DRAFT",icon="edit",scope="subject:current",target="ops_plan",perm="plan:write"),
      act("notify-team","通知运营值班群","EFFECT",icon="message",scope="team:ops",target="im",perm="notify:write",risk=True)]),
    runtime("数据新鲜度",[rt("Canonical 主链","ok","10:00 已确认"),rt("采集器 ×6","ok","5 个运行/1 待机"),rt("AI 派生","idle","不影响主链")]),
  ]),
 ],
 "context":{"evidence":["EV-7701","EV-7704","EV-7706","EV-7710"]},
 "viewmodel":{"kpis":["{id,label_key,value,unit,delta,spark,evidence_id,freshness}"],"trend":"{series[],labels[]}",
   "events":["{time,title,level,tags,evidence_id}"],"insight":"{text,why,cites[]}"},
 "actions":[act("draft-brief","生成运营简报","DRAFT"),act("export-overview","导出总览","QUERY")],
 "binding":{"kpis":"CODEX_VERIFY (canonical_metrics routes = UNKNOWN)","events":"CODEX_VERIFY (event list = UNKNOWN)","insight":"VIEWMODEL only; backend insight API = UNKNOWN"},
}

SPECS["CTH-02"]={
 "titleKey":"screen.CTH-02","patterns":["PAT-DATA-01","PAT-FILTER-01"],"motions":["M01","M07"],
 "sections":[
  head("CTH · 商业运营","主体档案 / 业务单元 / 品牌业态","选择主体只改变工作上下文；品牌、业态、业务单元的事实归属保持不变。",titleKey="screen.CTH-02"),
  split([
    cards([
      card("广州太古汇","商业综合体 ·  mall_group","target",badge={"text":"当前主体","cls":"brand"},meta="subject_id=subj_taikoo_hui"),
      card("业务单元 12","北区/西区/L1-L4 等","layers"),
      card("在场品牌 386","零售/餐饮/体验/服务","campaign"),
      card("业态 24","一级业态 6 / 二级 18","grid"),
    ],cols=2),
    table("品牌与业态",[col("品牌","b"),col("业态","cat"),col("楼层","fl"),col("业务单元","unit"),col("状态","s","toneKey","t"),col("声量","v",True)],
      [{"b":"Dior","cat":"美妆精品","fl":"L1","unit":"西区","s":"正常","t":"success","v":1240},
       {"b":"lululemon","cat":"运动生活","fl":"L3","unit":"北区","s":"活动期","t":"info","v":980},
       {"b":"新茶饮品牌 A","cat":"餐饮","fl":"B1","unit":"食集","s":"新入驻","t":"warning","v":412},
       {"b":"体验品牌 B","cat":"体验业态","fl":"L4","unit":"北区","s":"装修","t":"neutral","v":0}]),
  ],[
    filters([chip("全部",True),chip("零售"),chip("餐饮"),chip("体验"),chip("服务")]),
    chart("业态声量占比","ring",parts=[{"v":34,"color":"var(--lum-c-brand-500)"},{"v":26,"color":"var(--lum-c-info)"},{"v":18,"color":"var(--lum-c-success)"},{"v":22,"color":"var(--lum-c-slate-300)"}]),
    note("品牌/业态为业务数据（ViewModel），不进入 i18n；主体切换不重写 Canonical 归属。","RULE","SUBJECT-CTX"),
  ]),
 ],
 "context":{"evidence":["EV: subject_profile","EV: brand_directory"]},
 "viewmodel":{"units":["{unit_id,name,categories[]}"],"brands":["{brand_id,name,category,floor,unit,state,voice}"]},
 "binding":{"brands":"CODEX_VERIFY (brand_directory/brand APIs = UNKNOWN)"},
}

SPECS["CTH-03"]={
 "titleKey":"screen.CTH-03","patterns":["PAT-DATA-01"],"motions":["M06","M14"],
 "sections":[
  head("CTH · 商业运营","实时监测","采集→Canonical→指标的实时链路，区分实时值与已确认值，展示采集器健康。",titleKey="screen.CTH-03"),
  kpis([metric("实时在线提及/分",86,icon="runtime",source="STREAM: collector",fresh="live"),
       metric("已确认延迟",38,unit="s",icon="clock",source="RUNTIME: pipeline",decimals=0),
       metric("活跃采集器",5,unit="/6",icon="collector",source="RUNTIME: collector"),
       metric("待入链消息",12,icon="layers",source="STREAM: queue")]),
  split([
    chart("实时声量流（分钟）","line",series=[{"data":[40,55,51,68,62,74,70,86,80,86],"color":"var(--lum-c-brand-500)"}],
          labels=["-9","-8","-7","-6","-5","-4","-3","-2","-1","now"]),
    runtime("采集器",[rt("小红书采集","ok","running"),rt("微博采集","ok","running"),rt("评论同步","ok","running"),
                     rt("点评采集","warn","限流退避"),rt("会员/闸机","ok","running"),rt("外部 API","idle","standby")]),
  ],[
    events("实时事件流",[evt("now","新帖：停车相关","小红书 · 负面倾向 0.71","实时","med",["停车"],"EV-STREAM"),
                      evt("1m","微博提及 +12","话题 #广州太古汇#","1m","low",["微博"],"EV-STREAM")]),
    note("实时流是未确认数据，进入 Canonical 前不计入正式指标；界面用不同视觉区分 live vs confirmed。","RULE","LIVE-VS-CONFIRMED"),
  ]),
 ],
 "context":{"evidence":["RUNTIME: collector/pipeline"]},
 "viewmodel":{"realtime_series":["number"],"collectors":["{name,state,detail}"]},
 "binding":{"stream":"CODEX_VERIFY (collector_v2/realtime endpoints = UNKNOWN)"},
}

SPECS["CTH-04"]={
 "titleKey":"screen.CTH-04","patterns":["PAT-EVD-01"],"motions":["M08","M11"],
 "sections":[
  head("CTH · 商业运营","事件与事件关系","Source→Event→Case 的关系图与时间线，点击节点回跳证据。",titleKey="screen.CTH-04",
       actions=[btn("新建事件","primary","plus",act="new-event",cls="DRAFT",perm="event:write")]),
  split([
    raw("""<section class="lum-card lum-card-pad" data-reveal><div class="lum-section-head"><span class="lum-eyebrow">Event Graph</span><h2 class="lum-h4">事件关系图（原型示意）</h2></div>
      <svg viewBox="0 0 560 300" class="lum-chart" role="img" aria-label="event graph">
        <line x1="120" y1="80" x2="300" y2="150" class="lum-flow-link"/>
        <line x1="120" y1="220" x2="300" y2="150" class="lum-flow-link"/>
        <line x1="300" y1="150" x2="470" y2="90" class="lum-flow-link"/>
        <line x1="300" y1="150" x2="470" y2="210" class="lum-flow-link"/>
        <g><circle cx="120" cy="80" r="34" fill="var(--lum-c-brand-100)"/><text x="120" y="84" text-anchor="middle" font-size="11" fill="var(--lum-text)">评论簇</text></g>
        <g><circle cx="120" cy="220" r="34" fill="var(--lum-c-warning-bg)"/><text x="120" y="224" text-anchor="middle" font-size="11" fill="var(--lum-text)">帖子簇</text></g>
        <g><circle cx="300" cy="150" r="42" fill="var(--lum-c-brand-500)"/><text x="300" y="154" text-anchor="middle" font-size="11" fill="var(--lum-text-invert)">EV-7710</text></g>
        <g><circle cx="470" cy="90" r="32" fill="var(--lum-c-danger-bg)"/><text x="470" y="94" text-anchor="middle" font-size="11" fill="var(--lum-text)">Case</text></g>
        <g><circle cx="470" cy="210" r="32" fill="var(--lum-c-info-bg)"/><text x="470" y="214" text-anchor="middle" font-size="11" fill="var(--lum-text)">Risk</text></g>
      </svg></section>"""),
    events("事件时间线",[evt("09:05","首条相关评论","","09-10","low",[],"EV-7690"),
                      evt("09:31","聚类形成停车簇","96 条","09-10","med",[],"EV-7704"),
                      evt("10:22","升级为事件 EV-7710","风险分 72","09-10","high",[],"EV-7710")]),
  ],[
    evidence("事件证据",[ev("Event","EV-7710",["Cluster","Event","Case?","Risk?"],"停车/离场摩擦事件，关联 3 个簇、2 个潜在 Case。","10:22","event_engine",91)]),
    actions("事件操作",[act("to-case","转 Case","DRAFT",icon="case",perm="case:write"),act("link-risk","关联风险","DRAFT",icon="risk")]),
  ]),
 ],
 "context":{"evidence":["EV-7710","EV: event_graph"]},
 "viewmodel":{"graph":"{nodes[],edges[]}","timeline":["event"]},
 "binding":{"graph":"CODEX_VERIFY (event_graph API = UNKNOWN)"},
}

SPECS["CTH-05"]={
 "titleKey":"screen.CTH-05","patterns":["PAT-FILTER-01"],"motions":["M07"],
 "sections":[
  head("CTH · 商业运营","舆情日历","按日聚合情绪/事件密度，点选日期联动右侧证据与事件。",titleKey="screen.CTH-05"),
  split([
    raw("""<section class="lum-card lum-card-pad" data-reveal><div class="lum-section-head"><span class="lum-eyebrow">Calendar</span><h2 class="lum-h4">2026 年 9 月</h2></div>
      <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px" id="cal-grid"></div></section>"""),
  ],[
    events("当日明细 · 09-10",[evt("10:22","停车事件升级","","","high",[],"EV-7710"),evt("09:05","快闪开业","","","low",[],"EV-7706")]),
    kpis([metric("当日负面",12,icon="risk",source="EV:calendar"),metric("当日事件",3,icon="event",source="EV:calendar")]),
  ]),
 ],
 "context":{"evidence":["EV: calendar aggregate"]},
 "viewmodel":{"calendar":"{date:{sentiment,event_count,evidence[]}}"},
 "binding":{"calendar":"CODEX_VERIFY (weekly_events/calendar = UNKNOWN)"},
 "onMountClient":"fillCalendar",
}

SPECS["CTH-06"]={
 "titleKey":"screen.CTH-06","patterns":["PAT-EVD-01","PAT-FILTER-01"],"motions":["M07","M11"],
 "sections":[
  head("CTH · 商业运营","负面监测与用户/评论反馈","负面条目必须可追溯到原始 Source；区分用户反馈与公开舆情。",titleKey="screen.CTH-06"),
  filters([chip("全部",True),chip("公开舆情"),chip("用户反馈"),chip("评论"),chip("高风险")]),
  split([
    table("负面条目",[col("时间","t"),col("渠道","ch"),col("内容摘要","c"),col("情绪","s","toneKey","st"),col("簇","clu"),col("证据","ev")],
      [{"t":"10:21","ch":"小红书","c":"B3 找车绕了二十分钟……","s":"负面","st":"danger","clu":"停车","ev":"EV-7720"},
       {"t":"09:58","ch":"会员反馈","c":"北区指引牌不够明显","s":"负面","st":"warning","clu":"指引","ev":"EV-7721"},
       {"t":"09:40","ch":"微博","c":"晚高峰排队但活动不错","s":"中性","st":"neutral","clu":"活动","ev":"EV-7722"}]),
  ],[
    risks([risk("high","停车体验","96 条/30.8%",72,"EV-7704"),risk("med","指引不清",None,48,"EV-7712")]),
    evidence("原始来源",[ev("Source","EV-7720",["Source","Comment"],"原帖快照与链接已固定，采集时间 10:21。","10:21","xhs",97)]),
  ]),
 ],
 "context":{"evidence":["EV-7704","EV-7720"]},
 "viewmodel":{"items":["{time,channel,summary,sentiment,cluster,evidence_id}"]},
 "binding":{"items":"CODEX_VERIFY (negative/comment feedback APIs = UNKNOWN)"},
}

SPECS["CTH-07"]={
 "titleKey":"screen.CTH-07","patterns":["PAT-DATA-01"],"motions":["M03","M06"],
 "sections":[
  head("CTH · 商业运营","趋势分析","统一口径下的多指标趋势、同环比与构成变化，所有数值来自 Canonical。",titleKey="screen.CTH-07"),
  filters([chip("近 7 天"),chip("近 30 天",True),chip("近 90 天"),chip("自定义")]),
  chart("客流 / 销售 / 声量趋势","line",series=[
    {"data":[60,66,64,72,78,76,84],"color":"var(--lum-c-brand-500)"},
    {"data":[42,46,45,50,55,54,60],"color":"var(--lum-c-success)"},
    {"data":[30,34,33,41,44,42,49],"color":"var(--lum-c-warning)"}],labels=DAYS30[:7],
    legend=[{"label":"客流","color":"var(--lum-c-brand-500)"},{"label":"销售","color":"var(--lum-c-success)"},{"label":"声量","color":"var(--lum-c-warning)"}]),
  split([
    chart("负面构成变化","bar",series=[{"data":[30,18,16,14,22],"color":"var(--lum-c-brand-500)"}],labels=["停车","指引","排队","价格","其他"]),
    insight("停车类占比连续 3 日上升，与晚高峰客流高度相关，是本周主要拖累项。",why="构成变化 + 时间重合度，见 EV-7704/7710。",cites=["EV-7704","EV-7710"]),
  ]),
 ],
 "context":{"evidence":["EV: canonical_metrics"]},
 "viewmodel":{"series":["{label,data[],color}"]},
 "binding":{"trend":"CODEX_VERIFY (trend_api/canonical_metrics = UNKNOWN)"},
}

SPECS["CTH-08"]={
 "titleKey":"screen.CTH-08","patterns":["PAT-EVD-01","PAT-FILTER-01"],"motions":["M07","M11"],
 "sections":[
  head("CTH · 商业运营","案例库 / 案例分析 / 知识库","Case 由事件与证据沉淀，知识库沉淀可复用结论，不覆盖原始事实。",titleKey="screen.CTH-08",
       actions=[btn("新建案例","primary","case",act="new-case",cls="DRAFT",perm="case:write")]),
  tabs("cth08",[
    tab("案例库",[table("",[col("案例","n"),col("状态","s","toneKey","t"),col("关联事件","e"),col("风险","r"),col("证据","ev")],
      [{"n":"晚高峰停车摩擦处置","s":"进行中","t":"warning","e":"EV-7710","r":"高","ev":"CASE-221"},
       {"n":"快闪开业保障","s":"已关闭","t":"success","e":"EV-7706","r":"低","ev":"CASE-218"},
       {"n":"会员日复盘","s":"已归档","t":"neutral","e":"EV-7688","r":"低","ev":"CASE-210"}])]),
    tab("案例分析",[evidence("案例证据链",[ev("Case","CASE-221",["Event","Evidence","Decision","Action","Outcome"],"处置：增派引导+开放 B3，平均离场时间 -6.2 分钟。","进行中","case_engine",90)]),
                    timeline("处置时间线",[tl("10:22","建 Case",None,True),tl("10:40","指派运营",None,True),tl("11:00","现场执行","观察中")])]),
    tab("知识库",[cards([card("高峰停车疏导 SOP","历史复盘沉淀的标准动作","folder",badge={"text":"可复用","cls":"brand"}),
                      card("快闪活动保障清单","跨部门 checklist","folder"),
                      card("负面回应口径模板","经审批的回应模板","content")],cols=3)]),
  ]),
 ],
 "context":{"evidence":["CASE-221","EV-7710"]},
 "viewmodel":{"cases":["{id,title,state,events[],risk,evidence}"]},
 "binding":{"cases":"CODEX_VERIFY (case_library/case_templates = UNKNOWN)"},
}

SPECS["CTH-09"]={
 "titleKey":"screen.CTH-09","patterns":["PAT-DATA-01","PAT-EVD-01"],"motions":["M03","M13"],
 "sections":[
  head("CTH · 商业运营","风险中心与决策看板","风险分、决策项、行动与证据一屏对齐；高风险行动需确认与权限。",titleKey="screen.CTH-09"),
  kpis([metric("严重风险",1,icon="risk",source="EV:risk",delta=0,deltaUnit=""),metric("高风险",3,icon="alert",source="EV:risk"),
       metric("待决策",5,icon="target",source="EV:decision"),metric("已缓解(7d)",11,icon="check",source="EV:risk")]),
  split([
    risks([risk("critical","晚高峰停车摩擦","影响到店体验与口碑，风险分 84。",84,"EV-7710"),
           risk("high","会员复购下滑","复购率 -2.4pt，需运营干预。",68,"EV-7699"),
           risk("med","北区指引不清","投诉占 18%。",48,"EV-7712"),
           risk("low","活动物料库存偏紧","预计 3 天后到安全线。",26,"EV-7715")]),
  ],[
    actions("待决策",[
      act("decide-b3","开放 B3 备用通道（18-21点）","EFFECT",icon="check",scope="facility:parking",target="access_control",perm="facility:write",risk=True),
      act("decide-staff","增派晚高峰引导 4 人","DRAFT",icon="users",scope="team:ops",target="roster",perm="roster:write"),
      act("decide-sign","更新北区指引标识","DRAFT",icon="edit",scope="facility:signage",target="work_order",perm="ops:write")]),
    evidence("决策依据",[ev("Risk","EV-7710",["Metric","Cluster","Risk","Decision"],"风险分 84，依据 312 条评论与现场记录。","10:22","risk_engine",90)]),
  ]),
 ],
 "context":{"evidence":["EV-7710","EV-7699","EV-7712"]},
 "viewmodel":{"risks":["{level,title,score,evidence_id}"],"decisions":["action"]},
 "binding":{"risk":"CODEX_VERIFY (risk_engine = UNKNOWN)","decision":"DRAFT/EFFECT contract = UNKNOWN"},
}

SPECS["CTH-10"]={
 "titleKey":"screen.CTH-10","patterns":["PAT-EVD-01","PAT-UPLOAD-01"],"motions":["M11","M15"],
 "sections":[
  head("CTH · 商业运营","报告 / 周报 / 证据","报告由 Canonical 与 Evidence 生成，导出保留口径、时间窗与证据清单。",titleKey="screen.CTH-10",
       actions=[btn("生成周报","primary","report",act="gen-weekly",cls="DRAFT",perm="report:write"),btn("导出 PDF/Excel","secondary","download",act="export",cls="QUERY")]),
  tabs("cth10",[
    tab("报告列表",[table("",[col("报告","n"),col("周期","p"),col("状态","s","toneKey","t"),col("证据数","e",True),col("更新","u")],
      [{"n":"商业运营周报 W37","p":"09/02-09/08","s":"已确认","t":"success","e":128,"u":"09-09"},
       {"n":"停车专题分析","p":"近30天","s":"草稿","t":"warning","e":42,"u":"10:20"},
       {"n":"会员日 Campaign 复盘","p":"活动期","s":"已归档","t":"neutral","e":96,"u":"09-05"}])]),
    tab("周报预览",[insight("本周客流 +6.2%、销售占比 +2.1pt；停车摩擦为主要风险，建议晚高峰增派引导并开放 B3。",cites=["EV-7701","EV-7710"]),
                  chart("周内关键指标","bar",series=[{"data":[62,71,78,70,84,90,88],"color":"var(--lum-c-brand-500)"}],labels=["一","二","三","四","五","六","日"])]),
    tab("证据清单",[evidence("报告引用证据",[ev("Metric","EV-7701",["Source","Canonical","Metric","Report"],"客流口径与数值。","09-09","canonical",99),
                  ev("Risk","EV-7710",["Risk","Report"],"风险分与依据。","09-09","risk_engine",90)])]),
  ]),
 ],
 "context":{"evidence":["报告内全部 EV 清单随导出固化"]},
 "viewmodel":{"reports":["{id,title,period,state,evidence_count}"]},
 "binding":{"report":"CODEX_VERIFY (report_api/report_export = UNKNOWN)"},
}

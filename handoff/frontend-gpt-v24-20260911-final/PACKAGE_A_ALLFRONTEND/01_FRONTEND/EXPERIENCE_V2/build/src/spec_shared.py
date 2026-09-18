# -*- coding: utf-8 -*-
"""Shared domain screens SH-01..06."""
from specutil import *
SPECS={}

SPECS["SH-01"]={
 "titleKey":"screen.SH-01","patterns":["PAT-AI-01","PAT-AI-02","PAT-UPLOAD-01","PAT-FILTER-01"],"motions":["M05","M06","M09","M12","M15"],
 "sections":[
  head("Shared · 序境·内容创作","内容创作工作室 Content Studio",
       "Brief→Context→Evidence→Strategy→Create→Review→Approval→Export→Evaluation→Learning；AI 只按真实 Brief/Evidence 起草原创产物，定稿与发布在人。",
       titleKey="screen.SH-01",
       actions=[btn("新建 Brief","primary","content",act="new-brief",cls="DRAFT",perm="content:draft")]),
  steps([st("Brief · 真实简报","done"),st("Context · 主体/品牌","done"),st("Evidence · 事实素材","done"),
         st("Strategy · 叙事策略","done"),st("Create · 原创产物","active"),st("Review · 事实墙校验","todo"),
         st("Approval · 人工审批","todo"),st("Export · 导出/发布","todo"),st("Evaluation · 效果评估","todo"),st("Learning · 沉淀 Pattern","todo")]),
  split([
    tabs("sh01",[
      tab("创作 Create",[
        form("Brief / Context（事实来源，非 locale 文案）",[
          field("平台","select",opts=["小红书","抖音","微博","微信","播客"]),
          field("创作物类型","select",opts=["文案 Copy","视觉 Visual","轮播/海报 Carousel/Poster","短视频脚本/分镜 Short Video/Storyboard","Campaign Matrix"]),
          field("受众","input","例如：北区高价值会员"),field("目标","select",opts=["种草","到店转化","会员复购","品牌认知"]),
          field("语言","select",opts=["简体中文","English","한국어（语义本地化，非逐句翻译）"])],
          [btn("按 Pattern 检索并起草","primary","orb",act="ai-draft",cls="TASK",perm="content:draft"),
           btn("保存草稿","secondary","check",act="save",cls="DRAFT")]),
        note("Scoped Retrieval：只按 Brief/主体/平台/形式/受众/目标/语言/Evidence 检索相关 Pattern，不把整份研究母资产灌进提示词（Contract §6）。","RULE","CC-RETRIEVE")]),
      tab("素材 Assets",[upload("素材库（上传管线 M12，不制造假进度）",
        [{"name":"KV_主视觉.png","pct":100,"stage":"已入库 · 关联 ASSET-01"},{"name":"门店素材.mp4","pct":72,"stage":"转码中 72%"},
         {"name":"会员日权益口径.pdf","pct":100,"stage":"事实源 · BRIEF"}],"拖入素材 / 引用 Evidence")]),
      tab("成片 Artifacts",[cards([
        card("春季种草 · 文案 v2","Review · 3 处事实已锚定","content",badge={"text":"待审批","cls":"warning"},action=btn("打开","secondary",size="sm")),
        card("探店短视频脚本+分镜","Draft · 故事节拍连续","content",badge={"text":"草稿","cls":"brand"}),
        card("一策略多产物：KV/轮播/口播","同一事实核，跨格式复用","layers",badge={"text":"跨格式","cls":"success"}),
        card("会员日 Campaign Matrix","决策点/素材矩阵","campaign")],cols=2)]),
    ]),
  ],[
    ai(title="AI 协同过程（原型示例，非真实运行结果）",
       thread=[msg("user","按这份 Brief 与已锚定 Evidence，产出小红书首图文案 3 版。"),
               msg("ai","已生成 3 版（场景/权益/口碑）。每处事实声明均回链 Evidence；无法核实的档期与价格保持 UNKNOWN，未编造。",
                   tools=["pattern.retrieve","content.draft"],cites=["ASSET-01","EV-B110"])],
       steps=[st("INTENT","done"),st("RETRIEVE PATTERN","done"),st("DRAFT","active"),st("FACT WALL",""),st("ARTIFACT","")]),
    note("事实墙 Factuality Wall（§8）：创作自由只针对表达；产品可得性/日期/价格/促销/商户/业绩/引述/平台数据/法务声明必须回链已验证 Evidence 或 Brief 明确给出，否则保持 UNKNOWN 并请求确认。","RULE","CC-FACT-WALL"),
    table("内容学习 Pattern Registry（§4，结构化学习源，非生产事实）",
      [col("Registry","r"),col("承载","d"),col("状态","s","toneKey","t")],
      [{"r":"Narrative 叙事","d":"开场/张力/推进/情绪曲线/证据位/收束","s":"ADOPT","t":"success"},
       {"r":"Copy 文案","d":"标题逻辑/句式节奏/信息密度/CTA/禁用措辞","s":"ADOPT","t":"success"},
       {"r":"Visual 视觉","d":"层级/焦点/构图/材质/图文关系/裁剪","s":"EXPERIMENT","t":"warning"},
       {"r":"Motion/Storyboard","d":"节拍连续性/前后态/静态降级","s":"EXPERIMENT","t":"warning"},
       {"r":"Campaign 活动","d":"叙事弧/内容矩阵/素材矩阵/决策点/度量","s":"ADOPT","t":"success"},
       {"r":"Evaluation 评估","d":"事实/品牌契合/原创/平台/可达性 Gate","s":"ADOPT","t":"success"}]),
    actions("流转（Review→Approval→Export→Evaluation→Learning）",
      [act("submit-review","提交评审","DRAFT",icon="evaluation",perm="content:submit"),
       act("approve","审批通过","EFFECT",icon="check",perm="content:approve"),
       act("publish","发布/导出","EFFECT",icon="share",risk=True,perm="content:publish"),
       act("promote-learning","评估后沉淀 Pattern","DRAFT",icon="skill")])]),
 ],
 "context":{"evidence":["ASSET-01","EV-B110","BRIEF"],"state_source":"DESIGN_ONLY fixture"},
 "viewmodel":{
   "pipeline_stage":"enum[Brief,Context,Evidence,Strategy,Create,Review,Approval,Export,Evaluation,Learning]",
   "brief":"{platform,artifact_type,audience,objective,language,subject_id}",
   "artifacts":["{id,type,stage,fact_anchors[],unknowns[],assets[]}"],
   "pattern_registries":"Narrative|Copy|Visual|Motion|Campaign|Evaluation (schema per Contract §4)",
   "content_learning_asset":"ContentLearningAsset schema per Contract §5",
   "factuality":"claim -> verified Evidence | brief-supplied | UNKNOWN"},
 "binding":{
   "studio":"CODEX_BINDING_REQUIRED (content creation APIs = UNKNOWN)",
   "pattern_retrieval":"CODEX_BINDING_REQUIRED (scoped retrieval = UNKNOWN, no whole-file injection)",
   "fact_wall":"CODEX_BINDING_REQUIRED (claim->evidence resolver = UNKNOWN)",
   "publish":"CODEX_BINDING_REQUIRED + permission content:publish (UNKNOWN)",
   "ai_thread":"DESIGN_ONLY fixture -> backend task state at binding",
   "capability_status":"PARTIAL"},
}

SPECS["SH-02"]={
 "titleKey":"screen.SH-02","patterns":["PAT-EVD-01","PAT-FILTER-01"],"motions":["M07","M11"],
 "sections":[
  head("Shared · 序境·内容创作","证据库 Evidence Library","统一检索 Source/Evidence/Canonical 引用；每条证据可回溯原始快照与链路。",titleKey="screen.SH-02"),
  filters([chip("全部",True),chip("Metric"),chip("Source"),chip("Finding"),chip("Risk"),chip("Case")]),
  split([
    table("证据",[col("ID","id"),col("类型","k"),col("摘要","s"),col("置信","c",True),col("时间","t"),col("来源","src")],
      [{"id":"EV-7701","k":"Metric","s":"今日客流 38,214","c":99,"t":"10:00","src":"footfall"},
       {"id":"EV-7704","k":"Finding","s":"停车簇 96 条/30.8%","c":93,"t":"09:31","src":"cluster.rule"},
       {"id":"EV-7710","k":"Risk","s":"停车风险分 72","c":90,"t":"10:22","src":"risk_engine"},
       {"id":"EV-B110","k":"Source","s":"小红书话题快照","c":96,"t":"09:40","src":"xhs"}]),
  ],[evidence("证据链",[ev("Metric","EV-7701",["Source","Canonical","Metric"],"去重闸机口径，原始快照已固定。","10:00","footfall",99)]),
      actions("证据操作",[act("open-source","查看原始来源","NAVIGATION",icon="link"),act("pin","固定到报告","DRAFT",icon="report")])]),
 ],
 "context":{"evidence":["EV-7701","EV-7704","EV-7710"]},
 "viewmodel":{"evidence":["{id,kind,summary,confidence,time,source,chain[]}"]},
 "binding":{"library":"CODEX_VERIFY (evidence_chain/evidence store = UNKNOWN)"},
}

SPECS["SH-03"]={
 "titleKey":"screen.SH-03","patterns":["PAT-DATA-01"],"motions":["M03","M06"],
 "sections":[
  head("Shared · 序境·内容创作","Canonical 数据 / 指标浏览器","浏览 Canonical 表、指标口径与血缘；区分 Canonical 事实与派生指标。",titleKey="screen.SH-03"),
  split([
    table("指标目录",[col("指标","m"),col("口径","d"),col("表","tbl"),col("更新","u"),col("状态","s","toneKey","t")],
      [{"m":"daily_footfall","d":"去重闸机日客流","tbl":"canonical.footfall","u":"1m","s":"OK","t":"success"},
       {"m":"sentiment_volume","d":"去重平台提及","tbl":"canonical.voice","u":"3m","s":"OK","t":"success"},
       {"m":"member_sales_share","d":"会员销售/总销售","tbl":"canonical.sales","u":"1h","s":"OK","t":"success"},
       {"m":"creator_roi","d":"创作者投放 ROI","tbl":"derived","u":"手动","s":"PARTIAL","t":"warning"}]),
  ],[chart("指标血缘（示意）","line",series=[{"data":[3,5,8,12,15],"color":"var(--lum-c-brand-500)"}],labels=["Source","Evidence","Canonical","Metric","VM"]),
      note("Canonical 是唯一事实源；派生指标必须记录计算口径与上游，不允许同名不同义。","RULE","CANONICAL-ONE")]),
 ],
 "context":{"evidence":["DB: canonical"]},
 "viewmodel":{"metrics":["{name,definition,table,cadence,state,lineage}"]},
 "binding":{"canonical":"CODEX_VERIFY (canonical_data/metric engine = UNKNOWN)"},
}

SPECS["SH-04"]={
 "titleKey":"screen.SH-04","patterns":["PAT-UPLOAD-01"],"motions":["M15"],
 "sections":[
  head("Shared · 序境·内容创作","报告导出中心","按模板导出 PDF/Excel/PPT，固化口径、时间窗与证据清单；导出动作可审计。",titleKey="screen.SH-04",
       actions=[btn("新建导出","primary","download",act="new-export",cls="DRAFT",perm="report:export")]),
  split([
    table("导出任务",[col("报告","r"),col("格式","f"),col("范围","scope"),col("状态","s","toneKey","t"),col("证据数","e",True),col("操作","o")],
      [{"r":"运营周报 W37","f":"PDF","scope":"近7天","s":"就绪","t":"success","e":128,"o":"下载"},
       {"r":"品牌月报","f":"Excel","scope":"近30天","s":"生成中","t":"info","e":240,"o":"—"},
       {"r":"停车专题","f":"PPT","scope":"自定义","s":"草稿","t":"warning","e":42,"o":"继续"}]),
  ],[upload("导出输入",[{"name":"自定义封面.png","pct":100,"stage":"已附加"}],"附加封面/备注"),
      note("导出文件内嵌证据清单与生成时间，保证数字可回溯；原型不真正生成文件。","RULE","EXPORT-LINEAGE")]),
 ],
 "context":{"evidence":["导出固化证据清单"]},
 "viewmodel":{"exports":["{report,format,scope,state,evidence_count}"]},
 "binding":{"export":"CODEX_VERIFY (report_export/report_engine = UNKNOWN)"},
}

SPECS["SH-05"]={
 "titleKey":"screen.SH-05","patterns":["PAT-DATA-01"],"motions":["M03"],
 "sections":[
  head("Shared · 序境·内容创作","学习与评估资产","沉淀 SOP、复盘、培训与评估题库，区分已验证资产与草稿。",titleKey="screen.SH-05"),
  cards([
    card("高峰疏导 SOP","已验证 · 来自 CASE-221","folder",badge={"text":"已验证","cls":"success"}),
    card("活动保障 Checklist","跨部门清单","folder"),
    card("AI 提示词库","按能力分类的可复用 Prompt","skill"),
    card("评估题库","验收/回归用例","evaluation",badge={"text":"128 题","cls":"brand"}),
    card("历史复盘","按 Campaign/事件归档","case"),
    card("培训材料","新人上手路径","content"),
  ],cols=3),
  table("最近更新",[col("资产","a"),col("类型","t"),col("验证","v","toneKey","vt"),col("更新","u")],
    [{"a":"高峰疏导 SOP","t":"SOP","v":"已验证","vt":"success","u":"09-10"},{"a":"KOC 脚本模板","t":"Prompt","v":"待验证","vt":"warning","u":"09-08"}]),
 ],
 "context":{"evidence":["资产来源 Case/Report"]},
 "viewmodel":{"assets":["{id,title,kind,verified,updated}"]},
 "binding":{"assets":"CODEX_VERIFY (learning assets = UNKNOWN)"},
}

SPECS["SH-06"]={
 "titleKey":"screen.SH-06","patterns":["PAT-DATA-01"],"motions":["M01"],
 "sections":[
  head("Shared · 序境·内容创作","通知 / 任务中心","聚合待办、审批、告警与订阅；区分需要行动与仅知会。",titleKey="screen.SH-06"),
  split([
    tabs("sh06",[
      tab("待办",[table("",[col("任务","t"),col("来源","s"),col("优先级","p","toneKey","pt"),col("截止","d")],
        [{"t":"审批：门店探店成片","s":"内容中心","p":"高","pt":"danger","d":"今天"},{"t":"确认周报 W37","s":"报告","p":"中","pt":"warning","d":"明天"},{"t":"处置 Case-221","s":"风险中心","p":"高","pt":"danger","d":"今天"}])]),
      tab("通知",[events("",[evt("10:22","停车风险升高","风险分 72","","high",[],"EV-7710"),evt("09:40","导出就绪","运营周报 PDF","","low",[],"")])]),
      tab("告警",[runtime("系统告警",[rt("采集器退避","warn","点评限流"),rt("AI 超时已降级","ok","本地兜底")])]),
    ]),
  ],[actions("快速处理",[act("approve","通过审批","EFFECT",icon="check",risk=True,perm="approval:write"),act("snooze","稍后提醒","DRAFT",icon="clock")]),
      note("EFFECT 类处理（通过/驳回/指派）弹确认并走后端权限；原型仅演示。","RULE","NOTIF-EFFECT")]),
 ],
 "context":{"evidence":["待办来源各域"]},
 "viewmodel":{"tasks":["{id,title,source,priority,due}"]},
 "binding":{"tasks":"CODEX_VERIFY (notification/task center = UNKNOWN)"},
}

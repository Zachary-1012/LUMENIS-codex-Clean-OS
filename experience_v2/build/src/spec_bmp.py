# -*- coding: utf-8 -*-
"""BMP domain screens BMP-01..11."""
from specutil import *
SPECS={}

SPECS["BMP-01"]={
 "titleKey":"screen.BMP-01","patterns":["PAT-DATA-01","PAT-EVD-01"],"motions":["M01","M03","M08"],
 "sections":[
  head("BMP · 序境·品牌市场","品牌市场总览","品牌健康、传播、创作者与市场情报的统一视图，全部锚定证据。",titleKey="screen.BMP-01",
       actions=[btn("品牌简报","primary","report",act="draft",cls="DRAFT",perm="report:write"),btn("切换品牌","secondary","campaign")]),
  kpis([metric("品牌健康分",82.4,icon="evaluation",spark=SPARK7,source="EV:brand_health",decimals=1,delta=1.6),
       metric("全网声量",28640,icon="trend",spark=SPARK12,source="EV:voice.canonical",delta=9.4),
       metric("正向占比",76.2,unit="%",icon="check",spark=SPARK7B,source="EV:sentiment",decimals=1,delta=2.0),
       metric("在投 Campaign",4,icon="campaign",source="EV:campaign.open")]),
  split([
    chart("声量与情绪趋势","line",series=[{"data":[40,48,46,55,60,58,66],"color":"var(--lum-c-brand-500)"},{"data":[28,30,33,32,38,37,42],"color":"var(--lum-c-success)"}],labels=DAYS30[:7],
          legend=[{"label":"声量","color":"var(--lum-c-brand-500)"},{"label":"正向","color":"var(--lum-c-success)"}]),
    events("品牌动态",[evt("09:40","新品话题进入热榜","微博话题榜 #36","09-10","low",["传播"],"EV-B110"),
                   evt("昨日","竞品发布同类新品","声量 +44%","09-09","med",["竞品"],"EV-B108")]),
  ],[
    insight("正向占比回升主要来自 KOC 真实体验内容；建议把预算向腰部 KOC 倾斜并复用高互动脚本。",why="创作者分层贡献拆解，见 EV-B110/B112。",cites=["EV-B110","EV-B112"]),
    risks([risk("med","竞品声量反超","同类新品窗口，需 72h 内回应。",52,"EV-B108")]),
    actions("建议行动",[act("go-creator","打开创作者分析","NAVIGATION",icon="creators",target="BMP-05"),act("draft-plan","起草传播计划","DRAFT",icon="edit",perm="plan:write")]),
  ]),
 ],
 "context":{"evidence":["EV-B108","EV-B110","EV-B112"]},
 "viewmodel":{"kpis":["metric"],"voice_trend":"series","events":["event"]},
 "binding":{"all":"CODEX_VERIFY (brand/market overview APIs = UNKNOWN)"},
}

SPECS["BMP-02"]={
 "titleKey":"screen.BMP-02","patterns":["PAT-FILTER-01","PAT-DATA-01"],"motions":["M07"],
 "sections":[
  head("BMP · 品牌市场","品牌中心 / 多品牌与竞品","管理自有多品牌与竞品集合，切换品牌即切换 Subject 上下文。",titleKey="screen.BMP-02"),
  filters([chip("自有品牌",True),chip("竞品"),chip("全部")]),
  cards([
    card("主品牌","健康分 82.4 · 声量 28.6k","campaign",badge={"text":"当前","cls":"brand"}),
    card("子品牌 A","健康分 76.1","campaign"),
    card("竞品 X","声量反超，重点跟踪","target",badge={"text":"竞品","cls":"warning"}),
    card("竞品 Y","稳态","target",badge={"text":"竞品","cls":"neutral"}),
  ],cols=4),
  table("品牌对比（同口径）",[col("品牌","b"),col("健康分","h",True),col("声量","v",True),col("正向%","p",True),col("互动率","i",True),col("证据","ev")],
    [{"b":"主品牌","h":82.4,"v":28640,"p":76.2,"i":4.8,"ev":"EV-B201"},{"b":"子品牌 A","h":76.1,"v":12040,"p":71.0,"i":3.9,"ev":"EV-B202"},
     {"b":"竞品 X","h":79.8,"v":31200,"p":73.4,"i":5.2,"ev":"EV-B203"},{"b":"竞品 Y","h":70.2,"v":9020,"p":68.1,"i":3.1,"ev":"EV-B204"}]),
 ],
 "context":{"evidence":["EV-B201..204"]},
 "viewmodel":{"brands":["{id,role,health,voice,positive,engagement,evidence}"]},
 "binding":{"brands":"CODEX_VERIFY (brand_center = UNKNOWN)"},
}

SPECS["BMP-03"]={
 "titleKey":"screen.BMP-03","patterns":["PAT-DATA-01","PAT-EVD-01"],"motions":["M03","M11"],
 "sections":[
  head("BMP · 品牌市场","市场情报","行业趋势、品类机会与外部情报，区分已确认情报与待核实线索。",titleKey="screen.BMP-03"),
  split([
    chart("品类热度走势","line",series=[{"data":[30,34,38,36,44,48,52],"color":"var(--lum-c-info)"}],labels=DAYS30[:7]),
    cards([card("品类机会：体验业态","搜索热度 +22%，竞品布局不足","research",badge={"text":"机会","cls":"success"}),
           card("渠道迁移","短视频→直播转化提升","research"),
           card("政策/合规提示","广告法敏感词更新","security",badge={"text":"合规","cls":"warning"})],cols=1),
  ],[
    evidence("情报来源",[ev("External","EV-B301",["External","Intel","VM"],"行业报告：体验业态 Q3 增速领先。","09-08","market.report",82),
                  ev("Social","EV-B302",["Social","Intel"],"话题聚类显示「场景化体验」上升。","09-09","social.cluster",78)]),
    note("外部情报置信度低于内部 Canonical，界面分级展示并要求二次核实后才进入决策。","RULE","INTEL-CONF"),
  ]),
 ],
 "context":{"evidence":["EV-B301","EV-B302"]},
 "viewmodel":{"intel":["{title,kind,confidence,source,evidence}"]},
 "binding":{"intel":"CODEX_VERIFY (market_intel = UNKNOWN)"},
}

SPECS["BMP-04"]={
 "titleKey":"screen.BMP-04","patterns":["PAT-DATA-01"],"motions":["M03","M06"],
 "sections":[
  head("BMP · 品牌市场","传播分析","渠道×内容×时段的传播表现与转化漏斗，统一口径。",titleKey="screen.BMP-04"),
  kpis([metric("总曝光",1.28,unit="M",icon="trend",source="EV:reach",decimals=2,delta=11),
       metric("互动率",4.8,unit="%",icon="creators",source="EV:engage",decimals=1),
       metric("转发/收藏",38420,icon="share",source="EV:share"),
       metric("引流转化",2.1,unit="%",icon="arrow-right",source="EV:convert",decimals=1)]),
  split([
    chart("渠道贡献","bar",series=[{"data":[42,28,16,9,5],"color":"var(--lum-c-brand-500)"}],labels=["小红书","抖音","微博","微信","其他"]),
    chart("传播漏斗","bar",series=[{"data":[100,64,38,18,9],"color":"var(--lum-c-info)"}],labels=["曝光","点击","互动","加购","转化"]),
  ],[insight("小红书贡献最高互动但转化偏低，抖音引流转化更优，建议组合投放并 A/B 脚本。",cites=["EV-B401","EV-B402"]),
      evidence("口径",[ev("Metric","EV-B401",["Source","Canonical","Metric"],"渠道去重口径，已排除刷量异常。","09-09","canonical",95)])]),
 ],
 "context":{"evidence":["EV-B401","EV-B402"]},
 "viewmodel":{"channels":["{name,reach,engage,convert}"]},
 "binding":{"channels":"CODEX_VERIFY (communication_analysis = UNKNOWN)"},
}

SPECS["BMP-05"]={
 "titleKey":"screen.BMP-05","patterns":["PAT-DATA-01","PAT-FILTER-01"],"motions":["M07"],
 "sections":[
  head("BMP · 品牌市场","创作者 KOS / KOL / KOC / UGC","分层管理创作者，评估真实贡献与合作风险，沉淀可复用脚本。",titleKey="screen.BMP-05",
       actions=[btn("添加创作者","primary","creators",act="add",cls="DRAFT",perm="creator:write")]),
  filters([chip("全部",True),chip("KOS"),chip("KOL"),chip("KOC"),chip("UGC"),chip("高风险")]),
  table("创作者表现",[col("创作者","n"),col("分层","t"),col("平台","p"),col("内容数","c",True),col("互动率","i",True),col("转化","cv",True),col("风险","r","toneKey","rt"),col("证据","ev")],
    [{"n":"@城市生活家","t":"KOL","p":"小红书","c":18,"i":6.8,"cv":3.2,"r":"低","rt":"success","ev":"EV-C01"},
     {"n":"门店导购·小林","t":"KOS","p":"抖音","c":42,"i":4.1,"cv":5.6,"r":"低","rt":"success","ev":"EV-C02"},
     {"n":"@真实测评君","t":"KOC","p":"小红书","c":9,"i":9.2,"cv":2.1,"r":"中","rt":"warning","ev":"EV-C03"},
     {"n":"匿名 UGC ×128","t":"UGC","p":"多平台","c":128,"i":2.4,"cv":0.8,"r":"待核","rt":"neutral","ev":"EV-C04"}]),
  split([chart("分层贡献","ring",parts=[{"v":38,"color":"var(--lum-c-brand-500)"},{"v":27,"color":"var(--lum-c-info)"},{"v":24,"color":"var(--lum-c-success)"},{"v":11,"color":"var(--lum-slate-300)"}])],
        [risks([risk("med","刷量嫌疑创作者 2","互动异常，合作前需核验。",44,"EV-C05")])]),
 ],
 "context":{"evidence":["EV-C01..05"]},
 "viewmodel":{"creators":["{id,name,tier,platform,posts,engagement,convert,risk,evidence}"]},
 "binding":{"creators":"CODEX_VERIFY (kos_kol_koc = UNKNOWN)"},
}

SPECS["BMP-06"]={
 "titleKey":"screen.BMP-06","patterns":["PAT-UPLOAD-01","PAT-FILTER-01"],"motions":["M05","M07"],
 "sections":[
  head("BMP · 品牌市场","内容中心","素材/脚本/成片的生产流水线与审批状态，EFFECT 发布需权限。",titleKey="screen.BMP-06",
       actions=[btn("新建内容","primary","content",act="new",cls="DRAFT",perm="content:draft")]),
  split([
    upload("上传素材",[{"name":"主视觉_v3.png","pct":100,"stage":"已入库 · EV-M01"},
                    {"name":"门店短视频.mp4","pct":64,"stage":"AI 分析中…"},
                    {"name":"KOC 脚本包.docx","pct":18,"stage":"等待上传"}],"拖拽或点击上传素材","支持图片/视频/文档，自动去重并建立证据"),
    table("内容资产",[col("标题","t"),col("类型","k"),col("状态","s","toneKey","st"),col("审批","a"),col("证据","ev")],
      [{"t":"新品体验脚本 A","k":"脚本","s":"草稿","st":"warning","a":"待提交","ev":"EV-M11"},
       {"t":"门店探店成片","k":"视频","s":"待审批","st":"info","a":"审批中","ev":"EV-M12"},
       {"t":"主视觉 KV","k":"图片","s":"已确认","st":"success","a":"通过","ev":"EV-M01"}]),
  ],[actions("发布动作（需权限）",[
      act("submit-review","提交审批","DRAFT",icon="check",scope="content:self",target="approval",perm="content:submit"),
      act("publish","发布到平台","EFFECT",icon="share",scope="channel:external",target="publisher",perm="content:publish",risk=True)]),
      note("内容生成是 DRAFT，必须经审批与权限校验后才能 EFFECT 发布；原型不真实发布。","RULE","DRAFT-TO-EFFECT")]),
 ],
 "context":{"evidence":["EV-M01","EV-M11","EV-M12"]},
 "viewmodel":{"assets":["{id,title,kind,state,approval,evidence}"]},
 "binding":{"assets":"CODEX_VERIFY (content_center = UNKNOWN)"},
}

SPECS["BMP-07"]={
 "titleKey":"screen.BMP-07","patterns":["PAT-DATA-01","PAT-UPLOAD-01"],"motions":["M03","M05"],
 "sections":[
  head("BMP · 品牌市场","话题活动 Campaign","Campaign 目标、节奏、内容与效果，按阶段推进并保留证据。",titleKey="screen.BMP-07"),
  steps([st("立项","is-done"),st("内容筹备","is-done"),st("投放执行","is-active"),st("效果复盘",None)]),
  split([
    kpis([metric("Campaign 曝光",640,unit="k",icon="trend",source="EV:camp",delta=14),
          metric("参与量",28.4,unit="k",icon="creators",source="EV:camp"),
          metric("话题排名",36,icon="trend",source="EV:camp"),
          metric("ROI",4.2,unit="x",icon="evaluation",source="EV:camp",decimals=1)]),
    chart("活动节奏与声量","line",series=[{"data":[10,18,26,40,52,48,44],"color":"var(--lum-c-brand-500)"}],labels=["D1","D2","D3","D4","D5","D6","D7"]),
  ],[timeline("关键节点",[tl("D1","话题上线",None,True),tl("D3","KOL 集中发布",None,True),tl("D5","进入热榜",None,True),tl("D7","复盘",None)]),
      actions("活动操作",[act("add-content","追加内容","DRAFT",icon="content",perm="campaign:write"),act("end-campaign","结束活动","EFFECT",icon="check",risk=True,perm="campaign:close")])]),
 ],
 "context":{"evidence":["EV: campaign lineage"]},
 "viewmodel":{"campaign":"{goal,stage,kpis,timeline}","roi":"number"},
 "binding":{"campaign":"CODEX_VERIFY (campaign APIs = UNKNOWN)"},
}

SPECS["BMP-08"]={
 "titleKey":"screen.BMP-08","patterns":["PAT-AI-01","PAT-UPLOAD-01"],"motions":["M05","M11"],
 "sections":[
  head("BMP · 品牌市场","播客工作室","把研究/证据材料转成播客提纲、脚本与成片，AI 仅起草、人工定稿。",titleKey="screen.BMP-08"),
  split([
    upload("导入研究材料",[{"name":"市场情报 W37.pdf","pct":100,"stage":"已解析 · EV-P01"},{"name":"访谈记录.mp3","pct":42,"stage":"转写中…"}],"拖入报告/访谈/数据"),
    ai(thread=[msg("user","基于这些材料生成一期 8 分钟播客提纲。"),
               msg("ai","已生成 3 段结构：市场背景→机会拆解→行动建议，每段标注引用证据。",cites=["EV-P01","EV-P02"],tools=["podcast-skill"])]),
  ],[steps([st("材料解析","is-done"),st("提纲","is-done"),st("脚本","is-active"),st("配音",None),st("成片",None)],title="脚本流水线"),
      actions("制作动作",[act("gen-script","生成完整脚本","DRAFT",icon="edit",perm="podcast:draft"),act("render","渲染成片","EFFECT",icon="podcast",risk=True,perm="podcast:render")])]),
 ],
 "context":{"evidence":["EV-P01","EV-P02"]},
 "viewmodel":{"materials":["file"],"outline":["section"]},
 "binding":{"podcast":"CODEX_VERIFY (podcast_store/skill = UNKNOWN)"},
}

SPECS["BMP-09"]={
 "titleKey":"screen.BMP-09","patterns":["PAT-EVD-01","PAT-DATA-01"],"motions":["M11"],
 "sections":[
  head("BMP · 品牌市场","品牌报告与评估","品牌资产评估、周期报告与评分，结论均可回溯证据。",titleKey="screen.BMP-09",
       actions=[btn("生成评估报告","primary","evaluation",act="gen",cls="DRAFT",perm="report:write")]),
  split([
    chart("品牌资产五维","bar",series=[{"data":[82,76,80,71,85],"color":"var(--lum-c-brand-500)"}],labels=["认知","美誉","传播","体验","忠诚"]),
    table("评估记录",[col("报告","r"),col("周期","p"),col("综合分","s",True),col("状态","st","toneKey","t"),col("证据","ev")],
      [{"r":"Q3 品牌资产评估","p":"Q3","s":82.4,"st":"已确认","t":"success","ev":"EV-R01"},
       {"r":"8 月品牌月报","p":"8月","s":79.6,"st":"已确认","t":"success","ev":"EV-R02"},
       {"r":"竞品对比评估","p":"近30天","s":"草稿","st":"草稿","t":"warning","ev":"UNKNOWN"}]),
  ],[evidence("评估依据",[ev("Metric","EV-R01",["Canonical","Evaluation"],"五维评分来自同口径指标加权。","09-08","eval_engine",92)])]),
 ],
 "context":{"evidence":["EV-R01","EV-R02"]},
 "viewmodel":{"dimensions":["{name,score}"],"reports":["report"]},
 "binding":{"eval":"CODEX_VERIFY (brand_evaluation = UNKNOWN)"},
}

SPECS["BMP-10"]={
 "titleKey":"screen.BMP-10","patterns":["PAT-EVD-01"],"motions":["M11","M13"],
 "sections":[
  head("BMP · 品牌市场","品牌风险与事件","品牌侧风险/舆情事件的监测、分级与处置，复用统一风险引擎。",titleKey="screen.BMP-10"),
  risks([risk("high","竞品对比稿争议","对比表述可能引发合规风险。",66,"EV-BR01"),
         risk("med","KOL 翻车风险","某合作创作者历史争议。",48,"EV-BR02"),
         risk("med","负面话题外溢","从小红书外溢到微博。",45,"EV-BR03")]),
  events("相关事件",[evt("09-09","竞品发布对比内容","","09-09","med",["竞品"],"EV-BR01"),evt("09-08","KOL 历史言论被翻出","","09-08","med",["创作者"],"EV-BR02")]),
  actions("处置",[act("hold-creator","暂停合作创作者","EFFECT",icon="pause",risk=True,perm="creator:hold"),act("draft-response","起草回应口径","DRAFT",icon="edit",perm="response:draft")]),
 ],
 "context":{"evidence":["EV-BR01..03"]},
 "viewmodel":{"risks":["risk"],"events":["event"]},
 "binding":{"risk":"CODEX_VERIFY (brand_risk = UNKNOWN)"},
}

SPECS["BMP-11"]={
 "titleKey":"screen.BMP-11","patterns":["PAT-DATA-01"],"motions":["M03","M06"],
 "sections":[
  head("BMP · 品牌市场","对标与竞品分析","同口径竞品对标：指标、内容、渠道、价格与节奏，输出差异与证据。",titleKey="screen.BMP-11"),
  table("竞品对标矩阵",[col("维度","d"),col("主品牌","a"),col("竞品 X","x"),col("竞品 Y","y"),col("差距","gap","toneKey","t")],
    [{"d":"健康分","a":82.4,"x":79.8,"y":70.2,"gap":"领先","t":"success"},
     {"d":"声量","a":"28.6k","x":"31.2k","y":"9.0k","gap":"落后 X","t":"warning"},
     {"d":"互动率","a":"4.8%","x":"5.2%","y":"3.1%","gap":"略落后 X","t":"warning"},
     {"d":"渠道覆盖","a":"5","x":"5","y":"3","gap":"持平","t":"neutral"}]),
  split([chart("声量对标趋势","line",series=[{"data":[40,44,46,50,52],"color":"var(--lum-c-brand-500)"},{"data":[42,46,50,54,58],"color":"var(--lum-c-danger)"}],labels=["W1","W2","W3","W4","W5"])],
        [insight("竞品 X 以高频短视频拉动声量，我方在互动质量与忠诚维度仍领先，建议补齐短视频频次而非降价。",cites=["EV-B1101"])]),
 ],
 "context":{"evidence":["EV-B1101"]},
 "viewmodel":{"matrix":["{dim,self,competitors[],gap}"]},
 "binding":{"benchmark":"CODEX_VERIFY (benchmark = UNKNOWN)"},
}

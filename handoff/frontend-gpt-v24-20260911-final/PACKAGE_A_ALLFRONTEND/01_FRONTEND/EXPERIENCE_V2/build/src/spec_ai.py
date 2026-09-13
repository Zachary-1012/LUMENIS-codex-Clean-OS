# -*- coding: utf-8 -*-
"""AI domain screens (AI-01..05). AI-01 is a benchmark screen (hand-polished)."""
from specutil import *

COMPOSER = raw("""
<div class="lum-opt lum-opt-composer" data-opt="composer" data-strength="idle" data-reveal>
  <canvas class="lum-opt__gl"></canvas><div class="lum-opt__fallback"></div>
  <div style="padding:20px">
    <div class="lum-row" style="gap:8px;margin-bottom:10px">
      <span class="lum-chip lum-press">${cap}</span>
    </div>
    <textarea class="lum-textarea" style="min-height:84px;background:transparent;border:0;font-size:16px;padding:0" data-i18n-ph="ai.composer_placeholder" placeholder=""></textarea>
    <div class="lum-row-between" style="margin-top:10px">
      <div class="lum-row" style="gap:8px">
        <button class="lum-chip lum-press">引用证据</button>
        <button class="lum-chip lum-press">指定主体</button>
        <button class="lum-chip lum-press">时间范围</button>
      </div>
      <button class="lum-btn lum-btn-primary">${send} →</button>
    </div>
  </div>
</div>""".replace("${cap}","<span data-i18n='ai.task_morph'>能力→任务</span>").replace("${send}","<span data-i18n='ai.send'>发送</span>"))

SPECS={}

SPECS["AI-01"]={
 "titleKey":"screen.AI-01","patterns":["PAT-AI-01","PAT-AI-02"],"optical":["OPT-01","OPT-04"],
 "motions":["M02","M05","M09","M12"],
 "sections":[
  head("AI Agent","AI 意图入口","从一句任务出发，识别意图、检索证据、生成可追溯结论；AI 是增强层，不拥有生产事实。",
       titleKey="screen.AI-01",
       actions=[btn("查看 AI Gateway","secondary","ops",act="go-AI-05"),btn("技能中心","ghost","skill",act="go-AI-04")]),
  COMPOSER,
  kpis([
    metric("今日已锚定证据",1284,icon="link",spark=SPARK12,source="EV: evidence_chain",delta=12),
    metric("AI 结论可追溯率",99.2,unit="%",icon="evaluation",spark=SPARK7B,source="EV: ai_trace",decimals=1),
    metric("Provider 健康",4,unit="/4",icon="ops",source="RUNTIME: ai_gateway",fresh="m5"),
    metric("待人工复核",7,icon="risk",source="EV: review_queue",delta=-3,deltaUnit="")]),
  cards([
    card("生成商业运营简报","汇总主体下指标/事件/风险并标注证据链","report",badge={"text":"商业运营","cls":"brand"}),
    card("追踪一个新事件","沿 Source→Event→Case 建立时间线与影响面","event",None),
    card("对比竞品传播表现","多品牌同口径对比，输出差异与证据","target",None),
    card("起草内容并走审批","生成草稿进入 DRAFT，经权限后才执行","content",None),
  ],cols=4),
  split([
    timeline("最近任务",[
      tl("09:41","北区客流环比分析","已完成 · 引用 6 条证据",True),
      tl("09:12","负面评论聚类","已完成 · 3 个簇",True),
      tl("08:50","周报初稿","等待人工确认"),
      tl("昨日","会员日 Campaign 复盘","已归档",True)],label="History"),
  ],[
    runtime("Provider 状态",[
      rt("智谱 glm-5.3","ok","200 · 1.2s"),
      rt("本地 Ollama","ok","local"),
      rt("规则引擎","ok","deterministic"),
      rt("备用通道","idle","standby")]),
    note("AI 输出为派生结果，携带 Provider/Model/Prompt/Confidence/Evidence 引用与人工修正状态，不覆盖原始 Evidence 或 Canonical Data。","RULE","AI-NOT-TRUTH"),
  ]),
 ],
 "context":{"evidence":["EV: evidence_chain（全局）","EV: subject_context v2.1","RUNTIME: ai_gateway"]},
 "viewmodel":{"composer":{"intent":"string?","subject_id":"string","domain":"enum[CTH,BMP]","time_window":"range"},
   "capability_cards":["{capability_id,label_key,route,permission}"],"providers":["{name,state,latency_ms}"]},
 "actions":[act("go-AI-05","打开 AI Gateway","NAVIGATION",icon="ops"),act("submit-intent","提交意图","QUERY",icon="orb",scope="subject:current",target="ai_orchestrator",perm="ai:read")],
 "binding":{"composer":"CODEX_VERIFY (POST /api/ai/intent = UNKNOWN)","providers":"CODEX_VERIFY (/api/runtime/identity, ai gateway status = UNKNOWN)"},
}

SPECS["AI-02"]={
 "titleKey":"screen.AI-02","patterns":["PAT-AI-02"],"optical":["OPT-04"],"motions":["M05","M09","M10"],
 "sections":[
  head("AI Agent","能力 → 任务工作台","选择能力后，表面发生 Morph：旧能力后退、任务上下文进入、证据落定；全过程可中断。",titleKey="screen.AI-02"),
  steps([
    st("识别意图","is-done"),st("能力后退","is-done"),st("表面 Morph","is-active"),st("上下文解析",None),st("内容进入",None),st("证据落定",None)]),
  raw("""<div class="lum-opt lum-opt-morph" data-opt="morph" data-strength="composing" data-reveal>
    <canvas class="lum-opt__gl"></canvas><div class="lum-opt__fallback"></div>
    <div style="padding:18px;position:relative" class="lum-row-between">
      <div><div class="lum-eyebrow">CAPABILITY</div><b style="font-size:18px">传播分析 Communication Analysis</b></div>
      ${icon}<div><div class="lum-eyebrow">TASK</div><b style="font-size:18px">对比近 30 天小红书 vs 微博声量</b></div>
    </div></div>""".replace("${icon}","<svg width='26' height='26' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8'><path d='M5 12h14M13 6l6 6-6 6'/></svg>")),
  ai(steps=[
    {"label":"识别意图：跨平台声量对比","state":"done","tool":"intent"},
    {"label":"检索 Subject 范围内已确认证据","state":"done","tool":"evidence_store"},
    {"label":"按统一口径计算趋势","state":"done","tool":"canonical_metrics"},
    {"label":"生成结论并标注引用","state":"running","tool":"llm:glm-5.3"}],
    children="""<div style="margin-top:6px"></div>"""),
  evidence("本任务引用的证据",[
    ev("Canonical","EV-7731",["Source 小红书","Canonical","Metric"],"近 30 天小红书提及 4,218 条，环比 +18.4%。","09:42","xhs.collector",96),
    ev("Canonical","EV-7732",["Source 微博","Canonical","Metric"],"同期微博提及 2,106 条，环比 +3.1%。","09:42","weibo.collector",95)]),
  actions("下一步",[
    act("insert-to-report","插入到周报草稿","DRAFT",icon="report",scope="report:draft",target="weekly_report",perm="report:write"),
    act("save-task","保存为可复用任务","QUERY",icon="folder",scope="user:self",target="task_library",perm="task:write"),
    act("run-effect","推送到协作群","EFFECT",icon="message",scope="channel:external",target="im_webhook",perm="notify:write",risk=True)]),
 ],
 "context":{"evidence":["EV-7731","EV-7732","EV: ai_trace"]},
 "viewmodel":{"task_steps":["{key,label_key,state,tool}"],"evidence_refs":["evidence_id"]},
 "actions_detail":"see sections",
 "binding":{"task_orchestration":"CODEX_VERIFY (ai_task_engine = UNKNOWN route)"},
}

SPECS["AI-03"]={
 "titleKey":"screen.AI-03","patterns":["PAT-AI-01","PAT-EVD-01"],"motions":["M11","M13"],
 "sections":[
  head("AI Agent","证据锚定分析线程","每条 AI 结论都可回跳到 Evidence；缺证据的推断显式标 UNKNOWN，不编造。",titleKey="screen.AI-03"),
  ai(thread=[
    msg("user","帮我判断本周负面是否在升温，并给出处置优先级。"),
    msg("ai","本周负面声量环比 +9.6%，主要集中在「停车体验」与「北区指引」两个簇；建议优先处理停车体验（风险分 72）。",
        cites=["EV-7701","EV-7704","EV-7710"],tools=["canonical_metrics","risk_engine"]),
    msg("user","和上周同期相比，哪个时段最集中？"),
    msg("ai","工作日 18:00–21:00 占负面增量的 47%，与离场高峰重合；该结论由 312 条已确认评论聚合。",cites=["EV-7711"])]),
  split([
    evidence("结论引用",[
      ev("Metric","EV-7701",["Comment","Canonical","Metric"],"本周负面 312 条，上周 285 条。","09:30","comment.canonical",99),
      ev("Cluster","EV-7704",["Comment","Cluster","Finding"],"「停车体验」簇 96 条，占比 30.8%。","09:31","cluster.rule",93),
      ev("Risk","EV-7710",["Finding","Risk"],"停车体验风险分 72（高），趋势上行。","09:32","risk_engine",90)]),
  ],[
    risks([risk("high","停车体验负面升温","18–21 点离场高峰集中，建议增派引导。",72,"EV-7710"),
           risk("med","北区指引不清","指示牌缺失导致绕路投诉，占 18%。",48,"EV-7712")]),
    actions("建议行动",[
      act("create-case","生成处置 Case","DRAFT",icon="case",scope="subject:current",target="case",perm="case:write"),
      act("assign-owner","指派责任人","EFFECT",icon="user",scope="team:ops",target="assignment",perm="team:assign",risk=True)]),
  ]),
 ],
 "context":{"evidence":["EV-7701","EV-7704","EV-7710","EV-7711"]},
 "viewmodel":{"thread":["{who,text,cites[],tools[]}"]},
 "binding":{"thread":"CODEX_VERIFY (ai thread stream = UNKNOWN)","evidence_jump":"CODEX_VERIFY (evidence detail route = UNKNOWN)"},
}

SPECS["AI-04"]={
 "titleKey":"screen.AI-04","patterns":["PAT-FILTER-01"],"motions":["M01","M07"],
 "sections":[
  head("AI Agent","Agent / 技能中心","所有 Agent/Skill 必须有真实调用链与权限边界；文件存在不等于能力可用。",titleKey="screen.AI-04",
       actions=[btn("仅看可用","secondary","evaluation")]),
  filters([chip("全部",True),chip("商业运营"),chip("品牌市场"),chip("采集"),chip("分析"),chip("创作"),chip("系统")]),
  cards([
    card("证据检索 Agent","沿证据链检索并回标来源，状态 VERIFIED","link",badge={"text":"VERIFIED","cls":"success"}),
    card("事件聚类 Skill","规则+模型聚类评论/帖子","event",badge={"text":"VERIFIED","cls":"success"}),
    card("内容草稿 Agent","生成多平台草稿，进入 DRAFT 审批","content",badge={"text":"PARTIAL","cls":"warning"}),
    card("播客脚本 Skill","把研究材料转成播客提纲","podcast",badge={"text":"PARTIAL","cls":"warning"}),
    card("自动处置 Agent","EFFECT 类，默认禁用，需审批","shield-off",badge={"text":"BLOCKED","cls":"danger"}),
    card("跨仓研究桥","仅研发侧参考，非运行时依赖","research",badge={"text":"LEGACY","cls":"neutral"}),
  ],cols=3),
  table("Agent / Skill 调用链",[
    col("名称","name"),col("领域","domain"),col("类型","kind"),col("权限","perm"),col("调用链状态","state","toneKey","stateTone"),col("证据","ev")],
    [{"name":"证据检索 Agent","domain":"共享能力","kind":"检索","perm":"evidence:read","state":"VERIFIED","stateTone":"success","ev":"EV-AG-01"},
     {"name":"事件聚类 Skill","domain":"商业运营","kind":"规则+模型","perm":"content:read","state":"VERIFIED","stateTone":"success","ev":"EV-AG-02"},
     {"name":"内容草稿 Agent","domain":"共享能力","kind":"生成","perm":"content:draft","state":"PARTIAL","stateTone":"warning","ev":"UNKNOWN"},
     {"name":"自动处置 Agent","domain":"系统层","kind":"执行","perm":"effect:write","state":"BLOCKED","stateTone":"danger","ev":"—"}]),
 ],
 "context":{"evidence":["EV: skill_registry","EV: agent call graph"]},
 "viewmodel":{"agents":["{id,name_key,domain,kind,permission,callchain_state,evidence}"]},
 "binding":{"registry":"CODEX_VERIFY (skill_registry/ai_agent_registry = UNKNOWN)"},
}

SPECS["AI-05"]={
 "titleKey":"screen.AI-05","patterns":["PAT-DATA-01"],"motions":["M06"],
 "sections":[
  head("AI Agent","AI Gateway 与 Provider","Provider 不可用时核心生产链由规则与数据继续运行；云 AI 不是启动硬依赖。",titleKey="screen.AI-05"),
  runtime("Provider 实时状态",[
    rt("智谱 glm-5.3（深度推理）","ok","healthy · 1.2s · balance ok"),
    rt("智谱 glm-4.5-air（快速）","ok","healthy · 0.4s"),
    rt("本地 Ollama","ok","local fallback"),
    rt("确定性规则引擎","ok","always-on")]),
  split([
    chart("近 24h 调用量（按 Provider）","line",series=[
      {"data":[12,18,15,22,30,26,34,40,38,46,52,48],"color":"var(--lum-c-brand-500)"},
      {"data":[4,6,5,8,7,9,11,10,12,13,12,14],"color":"var(--lum-c-success)"}],labels=["00","02","04","06","08","10","12","14","16","18","20","22"],
      legend=[{"label":"智谱","color":"var(--lum-c-brand-500)"},{"label":"本地","color":"var(--lum-c-success)"}]),
  ],[
    kpis([metric("今日调用",1842,icon="ops",source="RUNTIME:ai_gateway",delta=8),
          metric("规则兜底率",6.4,unit="%",icon="skill",source="RUNTIME:rules",decimals=1)]),
    note("降级策略：云端失败→本地模型→确定性规则；任何一层失败都不阻塞 Evidence/Canonical 主链。","RULE","AI-FALLBACK"),
  ]),
  table("Provider 配置",[col("Provider","n"),col("用途","use"),col("状态","s","toneKey","t"),col("延迟ms","lat",True)],
    [{"n":"glm-5.3","use":"深度推理","s":"OK","t":"success","lat":1204},{"n":"glm-4.5-air","use":"日常快速","s":"OK","t":"success","lat":410},
     {"n":"ollama-local","use":"本地兜底","s":"OK","t":"success","lat":88},{"n":"legacy-provider","use":"历史通道","s":"STANDBY","t":"neutral","lat":"—"}]),
 ],
 "context":{"evidence":["RUNTIME: ai_gateway","EV: provider health"]},
 "viewmodel":{"providers":["{name,use,state,latency_ms}"],"call_series":["number[]"]},
 "binding":{"status":"CODEX_VERIFY (provider_registry/ai_governance = UNKNOWN)"},
}

# -*- coding: utf-8 -*-
"""System domain screens SYS-01..08."""
from specutil import *
SPECS={}

SPECS["SYS-01"]={
 "titleKey":"screen.SYS-01","patterns":["PAT-DATA-01"],"motions":["M06","M14"],
 "sections":[
  head("System","运行时健康 Runtime Health","唯一生产 Runtime 的进程、端口、依赖与降级状态；启动链与健康检查可追溯。",titleKey="screen.SYS-01",
       actions=[btn("运行时身份","secondary","runtime",act="identity",cls="QUERY"),btn("重启服务","ghost","refresh",act="restart",cls="EFFECT",risk=True,perm="runtime:restart")]),
  kpis([metric("在线进程",7,unit="/7",icon="runtime",source="RUNTIME: process",fresh="live"),
       metric("健康检查",24,unit="/24",icon="check",source="RUNTIME: health"),
       metric("平均响应",142,unit="ms",icon="trend",source="RUNTIME: latency"),
       metric("降级中",0,icon="alert",source="RUNTIME: degraded")]),
  split([
    runtime("核心服务",[rt("Web/API (0.0.0.0:8201)","ok","listening"),rt("Canonical 主链","ok","running"),
                     rt("Evidence 服务","ok","running"),rt("Metric 引擎","ok","running"),
                     rt("Scheduler","ok","running"),rt("AI Gateway","ok","running (非硬依赖)"),rt("内部浏览器","idle","standby")]),
    chart("近 1h 请求与延迟","line",series=[{"data":[120,140,132,150,142,138,142],"color":"var(--lum-c-brand-500)"}],labels=["-60","-50","-40","-30","-20","-10","now"]),
  ],[note("Runtime 启动链：scripts/start_production.ps1 → run_supervised.py → app factory → blueprint 注册；Canonical 启动身份以 /api/runtime/identity 为准。","RULE","RUNTIME-ENTRY"),
      actions("运行时操作",[act("view-identity","查看运行时身份","QUERY",icon="runtime"),act("graceful-reload","平滑重载","EFFECT",icon="refresh",risk=True,perm="runtime:reload")])]),
 ],
 "context":{"evidence":["RUNTIME: process/health/identity"]},
 "viewmodel":{"services":["{name,state,detail}"],"latency":"number[]"},
 "binding":{"health":"CODEX_VERIFY (/api/runtime/identity, health = UNKNOWN)"},
}

SPECS["SYS-02"]={
 "titleKey":"screen.SYS-02","patterns":["PAT-UPLOAD-01","PAT-DATA-01"],"motions":["M05"],
 "sections":[
  head("System","采集器状态 Collector","各平台采集任务的调度、限流、退避与入链情况；采集失败不污染 Canonical。",titleKey="screen.SYS-02"),
  kpis([metric("活跃采集器",5,unit="/6",icon="collector",source="RUNTIME:collector"),
       metric("今日采集",38420,icon="download",source="EV:ingest",delta=9),
       metric("限流退避",1,icon="alert",source="RUNTIME:collector"),
       metric("入链失败",0,icon="check",source="EV:ingest")]),
  table("采集任务",[col("采集器","n"),col("平台","p"),col("状态","s","toneKey","t"),col("频率","f"),col("最近成功","ok"),col("待处理","q",True),col("证据","ev")],
    [{"n":"小红书采集","p":"小红书","s":"运行","t":"success","f":"2m","ok":"10:22","q":12,"ev":"COL-01"},
     {"n":"微博采集","p":"微博","s":"运行","t":"success","f":"3m","ok":"10:21","q":4,"ev":"COL-02"},
     {"n":"点评采集","p":"大众点评","s":"退避","t":"warning","f":"限流","ok":"10:05","q":0,"ev":"COL-03"},
     {"n":"评论同步","p":"会员/评论","s":"运行","t":"success","f":"5m","ok":"10:20","q":2,"ev":"COL-04"},
     {"n":"闸机/会员","p":"内部系统","s":"运行","t":"success","f":"1m","ok":"10:22","q":0,"ev":"COL-05"},
     {"n":"外部 API","p":"第三方","s":"待机","t":"neutral","f":"手动","ok":"昨日","q":0,"ev":"COL-06"}]),
  note("原始数据先入隔离区，经去重/校验/证据固定后才进入 Canonical；采集层异常只标记，不用 0 静默填充。","RULE","INGEST-GUARD"),
 ],
 "context":{"evidence":["COL-01..06"]},
 "viewmodel":{"collectors":["{name,platform,state,cadence,last_ok,queue,evidence}"]},
 "binding":{"collectors":"CODEX_VERIFY (collector_v2 = UNKNOWN)"},
}

SPECS["SYS-03"]={
 "titleKey":"screen.SYS-03","patterns":["PAT-EVD-01"],"motions":["M11"],
 "sections":[
  head("System","数据库与事实链 Database & Truth Chain","schema_version 不等于应用可读；展示版本、完整性、外键、Canonical 链路与隔离契约。",titleKey="screen.SYS-03"),
  kpis([metric("Schema 版本","v12",icon="database",source="DB: schema_version"),
       metric("完整性检查","ok",icon="check",source="DB: integrity_check"),
       metric("外键违规",0,icon="link",source="DB: foreign_key_check"),
       metric("Canonical 表",64,icon="layers",source="DB: canonical")]),
  split([
    timeline("事实链",[tl("Source","原始来源固定（快照/链接/时间）",None,True),
                  tl("Evidence","证据固定 + 置信度",None,True),tl("Canonical","去重归一为 Canonical",None,True),
                  tl("Metric","同口径指标",None,True),tl("View Model","面向界面的归一模型",None,True)]),
    table("数据库身份",[col("项","k"),col("值","v")],
      [{"k":"当前连接身份","v":"ZBC_DB_PATH（隔离）"},{"k":"受保护生产库","v":"只读 / 禁写"},{"k":"WAL/SHM","v":"测试不触碰"},{"k":"外键运行时","v":"写连接 ON（分批）"}]),
  ],[note("version=v12 仅代表迁移跑完；必须再过 Required Schema/Table Contract、Application Readability、Runtime 三道 Gate。","RULE","V12-NOT-READY"),
      risks([risk("med","历史 ai_task 孤儿 4 行","历史数据债，未做依赖追踪前不删。",None,"P0C-B")])]),
 ],
 "context":{"evidence":["DB: integrity/foreign_key","P0C evidence"]},
 "viewmodel":{"truth_chain":["stage"],"db_identity":"{driver,path,isolation,fk}"},
 "binding":{"db":"CODEX_VERIFY (database.py/database_migrations.py = owner CODEX)"},
}

SPECS["SYS-04"]={
 "titleKey":"screen.SYS-04","patterns":["PAT-FILTER-01"],"motions":["M07"],
 "sections":[
  head("System","安全与权限 Security & Permission","READ/TASK/AUDIT/WRITE/DEPLOY 五级边界；EFFECT 行动必须二次确认与权限校验。",titleKey="screen.SYS-04"),
  table("权限矩阵",[col("能力域","d"),col("READ","r"),col("TASK","t"),col("AUDIT","a"),col("WRITE","w"),col("DEPLOY","dp")],
    [{"d":"Evidence/Canonical","r":"✓","t":"✓","a":"✓","w":"受限","dp":"—"},
     {"d":"报告导出","r":"✓","t":"✓","a":"✓","w":"草稿","dp":"—"},
     {"d":"内容发布","r":"✓","t":"草稿","a":"✓","w":"审批","dp":"—"},
     {"d":"生产部署","r":"管理员","t":"—","a":"✓","w":"管理员","dp":"管理员"}]),
  split([
    risks([risk("high","越权写入风险","任何 EFFECT 必须后端重验 Subject/Scope 授权。",None,"SEC-01"),
           risk("med","凭据泄漏面",".env/key 不进前端与交付物。",None,"SEC-02")]),
  ],[actions("审计操作",[act("view-audit","查看审计日志","QUERY",icon="ops",perm="audit:read"),
                    act("rotate-key","轮换密钥","EFFECT",icon="security",risk=True,perm="secret:rotate")]),
      note("前端只做交互确认；真正授权判定在后端，Subject 切换不改变数据归属，后端必须重验。","RULE","PERM-BACKEND")]),
 ],
 "context":{"evidence":["SEC-01","SEC-02"]},
 "viewmodel":{"matrix":["{domain,read,task,audit,write,deploy}"]},
 "binding":{"perm":"CODEX_VERIFY (permission matrix/api = UNKNOWN)"},
}

SPECS["SYS-05"]={
 "titleKey":"screen.SYS-05","patterns":[],"motions":["M01"],
 "sections":[
  head("System","设置 / 外观 / 语言","主题、光学档位、语言（zh/en/ko）、密度与动效偏好；偏好不外溢为业务数据。",titleKey="screen.SYS-05"),
  split([
    form("外观",[
      field("主题","select",opts=["浅色 Light","深色 Dark","跟随系统"]),
      field("光学效果","select",opts=["高（WebGL）","标准","软玻璃","不透明（降级）"]),
      field("界面密度","select",opts=["舒适","紧凑"]),
      field("减弱动效","select",opts=["跟随系统","开启","关闭"])],
      [btn("保存偏好","primary","check",act="save-pref",cls="DRAFT",perm="pref:write"),btn("重置","ghost")]),
  ],[form("语言与区域",[field("界面语言","select",opts=["简体中文","English","한국어"]),field("时区","select",opts=["本地","UTC"]),field("数字/货币格式","select",opts=["跟随语言","自定义"])]),
      note("固定 UI 文案走 i18n key（三语 parity）；业务数据走 ViewModel，不进 locale。另提供 pseudo-expanded 130%/150% 文本压力测试。","RULE","I18N-SPLIT")]),
 ],
 "context":{"evidence":[]},
 "viewmodel":{"prefs":"{theme,optical,density,reduced_motion,locale}"},
 "binding":{"prefs":"CODEX_VERIFY (user settings store = UNKNOWN)"},
}

SPECS["SYS-06"]={
 "titleKey":"screen.SYS-06","patterns":["PAT-AI-01"],"motions":["M05"],
 "sections":[
  head("System","内部浏览器","受控采集/取证浏览器：页面快照、证据固定与操作审计，不与个人浏览混用。",titleKey="screen.SYS-06",
       actions=[btn("新标签","primary","browser",act="new-tab",cls="TASK",perm="browser:open")]),
  split([
    raw("""<section class="lum-card" style="padding:0;overflow:hidden" data-reveal>
      <div class="lum-row" style="gap:8px;padding:10px 12px;border-bottom:1px solid var(--lum-line)">
        <span class="lum-chip">←</span><span class="lum-chip">→</span><span class="lum-chip">⟳</span>
        <div class="lum-search" style="flex:1">https://www.example.com/subject</div><span class="lum-badge lum-badge-success">已固定证据</span></div>
      <div style="height:280px;display:grid;place-items:center;background:var(--lum-surface-2);color:var(--lum-text-3)">受控浏览视口（原型占位 · 不加载真实外站）</div></section>"""),
  ],[runtime("浏览器状态",[rt("隔离上下文","ok","separate profile"),rt("证据固定","ok","snapshot+hash"),rt("操作审计","ok","recorded")]),
      actions("取证",[act("snapshot","固定快照为证据","DRAFT",icon="link",perm="evidence:capture"),act("extract","抽取结构化数据","TASK",icon="layers")])]),
 ],
 "context":{"evidence":["浏览器快照证据"]},
 "viewmodel":{"tabs":["{url,title,evidence_id}"]},
 "binding":{"browser":"CODEX_VERIFY (internal browser = UNKNOWN)"},
}

SPECS["SYS-07"]={
 "titleKey":"screen.SYS-07","patterns":["PAT-DATA-01"],"motions":["M03"],
 "sections":[
  head("System","验收评估 Evaluation / Acceptance","Production Acceptance 六 Gate 状态；PARTIAL/UNKNOWN 不算 PASS，文档存在不算通过。",titleKey="screen.SYS-07"),
  steps([st("G1 P0=0","is-active"),st("G2 仓库完整性",None),st("G3 生产事实",None),st("G4 Runtime+E2E",None),st("G5 安全恢复",None),st("G6 发布血缘/回滚",None)]),
  table("六 Gate",[col("Gate","g"),col("标准","c"),col("状态","s","toneKey","t"),col("证据","ev")],
    [{"g":"G1 P0","c":"P0 阻塞=0","s":"进行中","t":"warning","ev":"—"},
     {"g":"G2 仓库","c":"完整性/隔离","s":"未开始","t":"neutral","ev":"—"},
     {"g":"G3 事实","c":"Truth Owner 唯一","s":"未开始","t":"neutral","ev":"—"},
     {"g":"G4 Runtime","c":"启动+关键 E2E","s":"未开始","t":"neutral","ev":"—"},
     {"g":"G5 安全","c":"权限+恢复","s":"未开始","t":"neutral","ev":"—"},
     {"g":"G6 发布","c":"血缘+回滚演练","s":"未开始","t":"neutral","ev":"—"}]),
  note("体验层交付只声明 DOUBAO_EXPERIENCE_HANDOFF=COMPLETE；Production Ready 必须六 Gate 全 PASS，由 Codex 闭环。","RULE","SIX-GATE"),
 ],
 "context":{"evidence":["acceptance gates"]},
 "viewmodel":{"gates":["{id,criteria,state,evidence}"]},
 "binding":{"acceptance":"owner CODEX (production acceptance)"},
}

SPECS["SYS-08"]={
 "titleKey":"screen.SYS-08","patterns":["PAT-DATA-01"],"motions":["M06"],
 "sections":[
  head("System","可观测 / 日志 Observability & Logs","结构化日志、Trace、错误聚合与链路；区分前端原型日志与后端运行时日志。",titleKey="screen.SYS-08",
       actions=[btn("导出日志","secondary","download",act="export-log",cls="QUERY")]),
  split([
    chart("错误率 / 吞吐","line",series=[{"data":[2,1,3,1,0,1,1],"color":"var(--lum-c-danger)"},{"data":[40,52,48,60,58,55,62],"color":"var(--lum-c-brand-500)"}],labels=["-60","-50","-40","-30","-20","-10","now"]),
    table("最近日志",[col("时间","t"),col("级别","l","toneKey","lt"),col("模块","m"),col("消息","msg"),col("Trace","tr")],
      [{"t":"10:22:01","l":"INFO","lt":"success","m":"canonical","msg":"ingest batch committed n=128","tr":"tr-9f21"},
       {"t":"10:21:44","l":"WARN","lt":"warning","m":"collector.dianping","msg":"rate-limit backoff 30s","tr":"tr-9f1e"},
       {"t":"10:20:10","l":"ERROR","lt":"danger","m":"ai_gateway","msg":"provider timeout -> local fallback","tr":"tr-9f0a"}]),
  ],[runtime("链路",[rt("Log 采集","ok"),rt("Trace 关联","ok"),rt("错误聚合","ok"),rt("告警","idle")]),
      note("AI 超时已按规则降级到本地/规则引擎，主链未阻塞（见 AI-05 降级策略）。","RULE","OBS-FALLBACK")]),
 ],
 "context":{"evidence":["RUNTIME: logs/trace"]},
 "viewmodel":{"logs":["{time,level,module,msg,trace_id}"]},
 "binding":{"logs":"CODEX_VERIFY (observability = UNKNOWN)"},
}

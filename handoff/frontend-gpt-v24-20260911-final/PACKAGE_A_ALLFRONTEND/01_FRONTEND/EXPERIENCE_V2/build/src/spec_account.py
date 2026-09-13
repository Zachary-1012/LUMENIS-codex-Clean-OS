# -*- coding: utf-8 -*-
"""Account & Entry screens ACC-01..04. Login/recovery use chrome='none' (centered, no rail)."""
from specutil import *
SPECS={}

SPECS["ACC-01"]={
 "titleKey":"screen.ACC-01","chrome":"none","patterns":["PAT-AI-01"],"motions":["M01","M02"],
 "sections":[
  raw("""<div style="min-height:78vh;display:grid;place-items:center" data-reveal>
   <div class="lum-opt lum-opt-composer" data-opt="composer" data-strength="idle" style="max-width:440px;width:100%">
     <canvas class="lum-opt__gl"></canvas><div class="lum-opt__fallback"></div>
     <div style="padding:28px" class="lum-stack-4">
       <div class="lum-row" style="gap:10px"><div class="lum-rail__logo" style="width:40px;height:40px">序</div>
         <div><b class="lum-h3" data-i18n="product.mother">序境 LUMENIS</b><div class="lum-caption" data-i18n="acc.signin_sub"></div></div></div>
       <div class="lum-field"><label class="lum-label" data-i18n="acc.choose_domain"></label>
         <div class="lum-segmented" style="width:100%"><button aria-pressed="true">商业运营</button><button aria-pressed="false">品牌市场</button></div></div>
       <div class="lum-field"><label class="lum-label">Enterprise Account</label><input class="lum-input" placeholder="name@company.com"></div>
       <div class="lum-field"><label class="lum-label">Password</label><input class="lum-input" type="password" placeholder="••••••••"></div>
       <button class="lum-btn lum-btn-primary" style="width:100%;justify-content:center" data-i18n="acc.sso"></button>
       <div class="lum-row-between lum-caption"><span data-i18n="acc.recovery"></span><span>SAML / SSO</span></div>
     </div></div></div>"""),
 ],
 "context":{"evidence":[]},
 "viewmodel":{"auth":"{domain,account,sso_provider}","domains":"enum[CTH,BMP]"},
 "binding":{"auth":"CODEX_VERIFY (auth/login/sso = UNKNOWN)"},
}

SPECS["ACC-02"]={
 "titleKey":"screen.ACC-02","patterns":["PAT-NAV-01"],"motions":["M01","M07"],
 "sections":[
  head("Entry","主体选择与领域视角","先选 Subject（主体）再进入领域视角；选择只改变工作上下文，不改变数据归属，后端重验授权。",titleKey="screen.ACC-02"),
  cards([
    card("广州太古汇","商业综合体 · mall_group","target",badge={"text":"最近使用","cls":"brand"},action=btn("进入","primary",size="sm")),
    card("广州太古汇·北区","业务单元 · wing","layers"),
    card("Dior（场内品牌）","品牌主体","campaign"),
    card("2026 春季会员日","Campaign 主体","campaign"),
  ],cols=2),
  split([
    note("SubjectContext 八字段：subject_id / subject_type / domain / scope / permissions / time_window / locale / context_version。切换主体不重写 Canonical 归属。","RULE","SUBJECT-8"),
  ],[form("默认视角",[field("默认领域","select",opts=["商业运营","品牌市场"]),field("默认时间窗","select",opts=["近7天","近30天","近90天"]),field("界面语言","select",opts=["简体中文","English","한국어"])],
          [btn("设为默认并进入","primary","check",act="enter",cls="NAVIGATION")])]),
 ],
 "context":{"evidence":["SubjectContext v2.1"]},
 "viewmodel":{"subjects":["{subject_id,subject_type,scope,name}"]},
 "binding":{"subjects":"CODEX_VERIFY (subject resolver/permission = UNKNOWN)"},
}

SPECS["ACC-03"]={
 "titleKey":"screen.ACC-03","patterns":["PAT-NAV-02","PAT-DATA-01"],"motions":["M01","M08"],
 "sections":[
  head("Entry","全局工作空间启动","从统一入口进入各领域与 AI；底部 Dock 承载一级目的地与中央 AI 入口。",titleKey="screen.ACC-03"),
  kpis([metric("待办",6,icon="bell",source="SH-06"),metric("在办事件",9,icon="event",source="CTH-04"),
       metric("进行中 Campaign",4,icon="campaign",source="BMP-07"),metric("证据新增(24h)",312,icon="link",source="SH-02",delta=8)]),
  cards([
    card("进入商业运营","总览/监测/事件/风险/报告","compass",action=btn("进入","secondary",size="sm")),
    card("进入品牌市场","品牌/传播/创作者/播客","campaign"),
    card("问 AI Composer","沿证据链得到结论","sparkles",badge={"text":"AI","cls":"brand"}),
    card("继续未完成","周报 W37 草稿 / Case-221","folder"),
  ],cols=4),
  runtime("启动检查",[rt("运行时身份","ok","/api/runtime/identity"),rt("数据库隔离","ok","ZBC_DB_PATH"),rt("权限上下文","ok","已加载")]),
 ],
 "context":{"evidence":["启动链 runtime identity"]},
 "viewmodel":{"launch_cards":["{title,desc,icon,route}"],"startup_checks":["{name,state,detail}"]},
 "binding":{"launch":"CODEX_VERIFY (workspace home = UNKNOWN)"},
}

SPECS["ACC-04"]={
 "titleKey":"screen.ACC-04","chrome":"none","patterns":[],"motions":["M01"],
 "sections":[
  raw("""<div style="min-height:78vh;display:grid;place-items:center" data-reveal>
   <div class="lum-card lum-card-pad" style="max-width:460px;width:100%" class2="">
     <span class="lum-badge lum-badge-warning">Auth Guard</span>
     <h2 class="lum-h3" style="margin:10px 0 6px" data-i18n="acc.recovery">账号恢复</h2>
     <p class="lum-body-2">当权限不足、会话过期或主体未授权时进入此守卫：说明原因、给出可执行的恢复路径，不静默降级为假数据。</p>
     <div class="lum-stack-2" style="margin-top:14px">
       <div class="lum-action-item"><span class="lum-action-item__ico">①</span><span class="lum-action-item__txt"><b>重新验证企业身份</b><span>SAML / SSO 重新登录</span></span></div>
       <div class="lum-action-item"><span class="lum-action-item__ico">②</span><span class="lum-action-item__txt"><b>申请 Subject/Scope 授权</b><span>走审批，不绕过权限边界</span></span></div>
       <div class="lum-action-item"><span class="lum-action-item__ico">③</span><span class="lum-action-item__txt"><b>联系管理员并附带 Trace ID</b><span>问题可追溯</span></span></div></div>
     <div class="lum-row" style="margin-top:14px"><button class="lum-btn lum-btn-primary" data-i18n="acc.sso"></button><button class="lum-btn lum-btn-ghost" data-i18n="common.back"></button></div>
   </div></div>"""),
 ],
 "context":{"evidence":[]},
 "viewmodel":{"guard":"{reason,required_permission,subject_id,recovery_paths[]}"},
 "binding":{"guard":"CODEX_VERIFY (auth guard/recovery = UNKNOWN)"},
}

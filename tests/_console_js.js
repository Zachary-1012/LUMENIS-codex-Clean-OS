
const TITLES={home:"总览",collect:"全网采集",ai:"Zachary 助手",shadow:"AI 影子审核",legacy:"经典版模块",settings:"账号与设置"};
const STATE={view:"home",loaded:{},shadowSt:"pending",chats:[],drawerChats:[]};
async function api(path,opt){const r=await fetch(path,Object.assign({credentials:"same-origin",headers:{"Content-Type":"application/json"}},opt||{}));if(r.status===401||r.status===403){location.href="/v4/settings/login";throw new Error("auth");}return r.json();}
function go(v){switchView(v)}
function toggleSide(open){document.getElementById("side").classList.toggle("open",open);document.getElementById("overlaySide").classList.toggle("show",open);}
function switchView(v){
  STATE.view=v;
  document.querySelectorAll(".view").forEach(x=>x.classList.toggle("show",x.dataset.view===v));
  document.querySelectorAll(".nav-item[data-view],.mtab[data-view]").forEach(x=>x.classList.toggle("active",x.dataset.view===v));
  document.getElementById("pageTitle").textContent=TITLES[v]||"";
  document.getElementById("fab").style.display=(v==="ai")?"none":"grid";
  toggleSide(false);
  document.getElementById("content").scrollTop=0;
  const f=document.querySelector(`.view[data-view="${v}"] iframe`);
  if(f&&!f.src&&f.dataset.src){f.src=f.dataset.src;}
  if(v==="home"&&!STATE.loaded.home){loadHome();STATE.loaded.home=true;}
  if(v==="shadow"){loadShadow(STATE.shadowSt);}
  if(v==="ai"&&!STATE.loaded.ai){welcome(document.getElementById("aiScroll"));STATE.loaded.ai=true;}
}
document.querySelectorAll(".nav-item[data-view],.mtab[data-view]").forEach(b=>b.onclick=()=>switchView(b.dataset.view));

/* ---------- 统一 Auth Recovery Center（不跳页·全局） ---------- */
const AUTH_BAD=new Set(["AUTH_REQUIRED","AUTH_FAILED","CAPTCHA","NEED_VERIFY","BLOCKED","IP_RISK","NETWORK_ERROR","FAIL","ERROR"]);
const AUTH_STATE_CN={AUTH_VALID:"登录有效",EXPIRED:"登录已失效",REQUIRED:"准备恢复",QR_DISPLAYED:"二维码已展示",
  WAITING_SCAN:"等待扫码/登录",SCANNED:"已扫码待确认",CONFIRMING:"确认登录中",RECOVERED:"已恢复",
  HEALTH_CHECK:"恢复后健康检查",QR_EXPIRED:"二维码过期·自动刷新",QR_FAILED:"取码失败·可重试",
  AUTH_FAILED:"尚未恢复",PLATFORM_BLOCKED:"平台风控冷却中",UNKNOWN:"浏览器未启动"};
let authTimer=null,authSnoozed=new Set();

function openAuthModal(platform,sourceState,detail){
  if(!platform)return;
  STATE.authPlatform=platform;authSnoozed.delete(platform);
  document.getElementById("authMask").classList.add("show");
  document.getElementById("amPlatform").textContent=platform;
  document.getElementById("amState").textContent=STATE_CN[sourceState]||sourceState||"检测中…";
  document.getElementById("amReason").textContent=detail||"采集时检测到该平台需要重新登录或人工验证";
  document.getElementById("amAccount").textContent="读取中…";
  document.getElementById("amKind").className="am-kind";document.getElementById("amKind").textContent="";
  document.getElementById("amCool").classList.remove("show");
  [1,2,3].forEach(i=>document.getElementById("amStep"+i).className="am-step");
  api("/v4/adapters/recovery/start",{method:"POST",body:JSON.stringify({platform,source_state:sourceState||"",detail:detail||""})})
    .then(d=>renderAuthSession(d.session,d.kind))
    .catch(e=>{document.getElementById("amReason").textContent="恢复通道启动失败："+(e.message||e);});
  if(authTimer)clearInterval(authTimer);
  authTimer=setInterval(pollAuth,2500);pollAuth();
}
function closeAuthModal(){
  document.getElementById("authMask").classList.remove("show");
  if(authTimer){clearInterval(authTimer);authTimer=null;}
  STATE.authPlatform=null;
}
function laterAuth(){ // 稍后处理：保持 NEED_VERIFY/PAUSED，不伪装恢复，恢复前不再自动打扰
  const p=STATE.authPlatform;
  if(p){authSnoozed.add(p);
    api("/v4/adapters/recovery/cancel",{method:"POST",body:JSON.stringify({platform:p})}).catch(()=>{});}
  closeAuthModal();
}
async function recheckAuth(){
  const p=STATE.authPlatform;if(!p)return;
  const btn=document.getElementById("amRecheck");btn.disabled=true;btn.textContent="检测中…";
  try{const d=await api("/v4/adapters/recovery/check",{method:"POST",body:JSON.stringify({platform:p})});
    if(d.recovered)renderRecovered();else pollAuth();}catch(e){}
  btn.disabled=false;btn.textContent="我已完成验证，重新检测";
}
function renderRecovered(){
  setSteps(3);
  document.getElementById("amState").textContent="已恢复 · 自动续采";
  document.getElementById("amQrBox").classList.remove("show");
  document.getElementById("amCool").classList.remove("show");
  const k=document.getElementById("amKind");k.className="am-kind";
  k.textContent="✓ 登录态已恢复，系统自动解除暂停并继续采集。";
  setTimeout(()=>{closeAuthModal();loadHome();},1600);
}
function setSteps(done){for(let i=1;i<=3;i++){const el=document.getElementById("amStep"+i);
  el.className="am-step"+(i<=done?" done":"")+(i===done+1?" active":"");}}
function renderAuthSession(s,kind){
  if(!s)return;kind=kind||s.kind;
  if(s.display||s.account)document.getElementById("amAccount").textContent=s.display||s.account;
  const st=s.state;
  document.getElementById("amState").textContent=AUTH_STATE_CN[st]||st;
  const kindBox=document.getElementById("amKind"),qrBox=document.getElementById("amQrBox"),cool=document.getElementById("amCool");
  if(kind==="BLOCKED"||st==="PLATFORM_BLOCKED"){ // C类：只冷却，不显示扫码
    kindBox.className="am-kind blocked";
    kindBox.textContent="C 类 · IP/平台风控（如 300012）：扫码无法解决，系统已自动降频熔断冷却，不硬刚。";
    qrBox.classList.remove("show");
    const rem=Math.max(0,Math.round(s.cooldown_remain||(s.risk&&s.risk.cooldown_remain)||0));
    cool.classList.add("show");
    cool.innerHTML=`熔断冷却中，剩余约 <b>${Math.floor(rem/60)}分${rem%60}秒</b>，冷却结束先做健康检查再逐步恢复。<div class="bar"><i style="width:${rem?Math.min(100,rem/600*100):0}%"></i></div>`;
    setSteps(0);return;
  }
  if(kind==="VERIFY"){ // B类：人机验证，不是重新登录
    kindBox.className="am-kind verify";
    kindBox.textContent="B 类 · 人机验证：这不是重新登录。请在弹出的采集浏览器完成滑块/安全验证后点“重新检测”。";
  }else{ // A类：登录失效
    kindBox.className="am-kind";
    kindBox.textContent="A 类 · 登录失效：用对应 App 扫码，或在弹出的采集浏览器登录（持久 Profile，登录一次长期复用）。";
  }
  cool.classList.remove("show");
  if(st==="AUTH_VALID"||st==="RECOVERED"){renderRecovered();return;}
  const steps=s.steps||{};
  setSteps(steps.done?3:(steps.scan?1:(steps.open?1:0)));
  if(kind!=="BLOCKED"){
    qrBox.classList.add("show");
    const img=document.getElementById("amQr");
    img.src=`/v4/adapters/recovery/shot/${s.platform}?t=${Date.now()}`;
    img.onerror=()=>{qrBox.classList.remove("show");};
    document.getElementById("amQrHint").textContent=s.remote_hint||"若二维码未出现，可直接在采集浏览器登录页操作";
  }
}
async function pollAuth(){
  const p=STATE.authPlatform;if(!p)return;
  try{const d=await api("/v4/adapters/recovery/status");
    const s=(d.tasks||[]).find(x=>x.platform===p);if(s)renderAuthSession(s);}catch(e){}
}
async function authWatchdog(){ // 任何 view（含 iframe 子页）平台失效即弹；稍后处理过的恢复前不打扰
  try{const h=await fetchAllHealth();
    h.forEach(x=>{
      const healthy=["SUCCESS","IDLE","EMPTY","RUNNING"].includes(x.state);
      if(!healthy&&AUTH_BAD.has(x.state)&&STATE.authPlatform!==x.platform&&!authSnoozed.has(x.platform))
        openAuthModal(x.platform,x.state,x.last_error||"");
      if(healthy)authSnoozed.delete(x.platform);
    });
  }catch(e){}
}

/* ---------- 总览 ---------- */
const STATE_CN={IDLE:"待机",RUNNING:"采集中",SUCCESS:"正常",EMPTY:"无结果",AUTH_REQUIRED:"需登录",AUTH_FAILED:"登录失效",
  CAPTCHA:"人机验证",NEED_VERIFY:"需验证",BLOCKED:"已熔断",IP_RISK:"IP风险",NETWORK_ERROR:"网络异常",FAIL:"失败",ERROR:"错误"};
async function fetchAllHealth(){
  // v4 适配器注册表健康 + 小红书主采集(老链路 /api/xhs/collect-health) 六态合并，状态中心不漏主平台
  const d=await api("/v4/adapters/health");let h=d.health||[];
  try{
    const x=await api("/api/xhs/collect-health"),cnt=x.state_counts||{};let fetched=0;
    Object.keys(cnt).forEach(k=>{if(["SUCCESS","EMPTY"].includes(k))fetched+=(cnt[k].notes||0);});
    const bad=(x.recent||[]).find(r=>["BLOCKED","AUTH_FAILED","CAPTCHA","NETWORK_ERROR"].includes(r.state));
    let st="IDLE";
    if(x.circuit&&x.circuit.open)st="BLOCKED";else if(x.overall==="FAILED")st=bad?bad.state:"FAIL";
    else if(x.overall==="OK")st="SUCCESS";
    h=[{platform:"xiaohongshu",display:"小红书·主采集",needs_browser:true,state:st,fetched,
        last_error:(x.circuit&&x.circuit.detail)||(bad&&bad.msg)||""}].concat(h);
  }catch(e){}
  return h;
}
async function loadHome(){
  fetchAllHealth().then(h=>{
    document.getElementById("kpiPlatforms").textContent=h.length;
    const ok=h.filter(x=>["SUCCESS","IDLE","EMPTY"].includes(x.state)).length;
    document.getElementById("kpiOk").textContent=ok+"/"+h.length;
    const box=document.getElementById("healthMatrix");box.innerHTML="";
    h.forEach(x=>{
      const c=document.createElement("div");c.className="hcell";
      const st=x.state||"IDLE";const bad=AUTH_BAD.has(st);
      c.innerHTML=`<span class="hd ${st} ${x.fetched?'on':''}"></span><span class="hn">${x.display||x.platform}</span><span class="hs">${STATE_CN[st]||st}${x.fetched?(' · '+x.fetched):''}</span>`;
      c.onclick=()=>{ if(bad){openAuthModal(x.platform,st,x.last_error||"");} else {switchView("collect");} };
      box.appendChild(c);
    });
  }).catch(()=>{});
  api("/v4/ai/status").then(d=>renderAi(d.ai)).catch(()=>{});
  api("/v4/ai/shadow/stats").then(d=>{
    const p=d.stats?.pending||0;document.getElementById("kpiShadow").textContent=p;
    document.getElementById("navShadowBadge").style.display=p?"":"none";
    document.getElementById("tabShadowBadge").style.display=p?"":"none";
    document.getElementById("navShadowBadge").textContent=p;document.getElementById("tabShadowBadge").textContent=p;
  }).catch(()=>{});
}
function renderAi(ai){
  if(!ai)return;
  const dot=document.getElementById("aiDot"),txt=document.getElementById("aiPillText");
  const runtime=ai.runtime;
  if(runtime==="local"){dot.className="dot";txt.textContent="本地模型 · "+(ai.model||"");}
  else if(runtime==="cloud"){dot.className="dot";txt.textContent="云端 · "+(ai.provider||"");}
  else{dot.className="dot rule";txt.textContent="规则引擎保底";}
  document.getElementById("kpiAi").textContent=runtime==="local"?"本地":(runtime==="cloud"?"云端":"规则");
}

/* ---------- Zachary 聊天 ---------- */
function welcome(box){
  box.innerHTML="";
  addMsg(box,"ai","你好，我是 Zachary。我可以基于系统内真实数据分析采集、事件、笔记、话题、案例与报告；涉及变更的建议我会先放进影子审核，由你确认。",null);
}
function addMsg(box,role,text,extra){
  const m=document.createElement("div");m.className="msg "+(role==="me"?"me":"ai");
  let inner=`<div class="ma">${role==="me"?"我":"✦"}</div><div><div class="bubble">${escapeHtml(text)}</div>`;
  if(extra){
    if(extra.provider)inner+=`<div class="prov-tag">${providerCN(extra.provider)}${extra.model?(" · "+extra.model):""}</div>`;
    if(extra.targets&&extra.targets.length){
      inner+=`<div class="target-chips">`+extra.targets.map(t=>`<button class="tchip" onclick="targetGo('${t.page}')">${t.label} ›</button>`).join("")+`</div>`;
    }
  }
  inner+="</div>";m.innerHTML=inner;box.appendChild(m);box.scrollTop=box.scrollHeight;return m;
}
function providerCN(p){return{rule:"规则引擎保底",ollama:"本地 Ollama",lmstudio:"本地 LM Studio",zhipu:"智谱",qwen:"通义千问",deepseek:"DeepSeek",ark:"豆包",openai:"OpenAI"}[p]||p||"";}
function escapeHtml(s){return(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function targetGo(page){const m={monitor:"collect",alerts:"collect",overview:"home",events:"legacy",notes:"legacy",topics:"legacy"};if(m[page])switchView(m[page]);}
function fillQ(t){document.getElementById("aiInput").value=t;document.getElementById("aiInput").focus();}
function autoGrow(t){t.style.height="auto";t.style.height=Math.min(t.scrollHeight,140)+"px";}
function sendKey(e,drawer){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat(drawer);}}
let busy=false;
async function sendChat(drawer){
  const input=document.getElementById(drawer?"drawerInput":"aiInput");
  const box=document.getElementById(drawer?"drawerScroll":"aiScroll");
  const q=(input.value||"").trim();if(!q||busy)return;
  if(STATE.loaded.ai===false&&!drawer){}
  if(!box.children.length)welcome(box);
  addMsg(box,"me",q);input.value="";autoGrow(input);busy=true;
  const typ=addMsg(box,"ai",`<span class="typing"><i></i><i></i><i></i></span>`);typ.querySelector(".bubble").style.color="transparent";
  try{
    const d=await api("/v4/ai/chat",{method:"POST",body:JSON.stringify({message:q,scope:STATE.view==="ai"?"all":STATE.view})});
    typ.remove();
    if(d.success){addMsg(box,"ai",d.reply,{provider:d.provider,model:d.model,targets:d.targets});
      if(d.used_rule_fallback){/* 规则保底已在文案内说明 */}
      loadHome();
    }else addMsg(box,"ai","出错了："+(d.error||"未知错误"));
  }catch(e){typ.remove();addMsg(box,"ai","连接中断，请稍后再试。");}
  busy=false;
}

/* ---------- 影子审核 ---------- */
async function loadShadow(st){
  STATE.shadowSt=st;
  document.querySelectorAll("#shadowTabs .btn").forEach(b=>{const on=b.dataset.st===st;b.classList.toggle("ghost",!on);});
  const box=document.getElementById("shadowList");box.innerHTML='<div class="empty">加载中…</div>';
  const d=await api("/v4/ai/shadow?status="+st);
  const items=d.items||[];
  if(!items.length){box.innerHTML='<div class="empty"><span class="big">⛉</span>暂无相关 AI 建议</div>';return;}
  box.innerHTML="";
  items.forEach(it=>{
    const el=document.createElement("div");el.className="sh-item";
    const rat=it.rationale&&Object.keys(it.rationale).length?JSON.stringify(it.rationale):"";
    el.innerHTML=`<div class="sh-head"><span class="sh-mod">${it.module||"-"}</span><span class="sh-title">${escapeHtml(it.title)}</span><span class="sh-time">${it.created_at}</span></div>
      ${rat?`<div class="sh-rationale">依据：${escapeHtml(rat)}</div>`:""}
      <div class="sh-actions">
        ${it.status==="pending"
          ?'<button class="btn sm ok" onclick="decide(\''+it.id+'\',\'accepted\')">采纳</button><button class="btn sm no" onclick="decide(\''+it.id+'\',\'rejected\')">驳回</button>'
          :'<span class="prov-tag">状态：'+({accepted:"已采纳",rejected:"已驳回",dismissed:"已忽略"}[it.status]||it.status)+(it.decided_by?(" · "+it.decided_by):"")+'</span>'}
      </div>`;
    box.appendChild(el);
  });
}
async function decide(id,decision){await api(`/v4/ai/shadow/${id}/decide`,{method:"POST",body:JSON.stringify({decision})});loadShadow(STATE.shadowSt);loadHome();}

/* ---------- 悬浮抽屉 ---------- */
function toggleDrawer(open){document.getElementById("drawer").classList.toggle("open",open);document.getElementById("mask").classList.toggle("show",open);
  if(open){const box=document.getElementById("drawerScroll");if(!box.children.length)welcome(box);document.getElementById("drawerInput").focus();}}

/* ---------- 初始化 ---------- */
loadHome();STATE.loaded.home=true;
setInterval(()=>{if(STATE.view==="home")loadHome();},15000);
setInterval(authWatchdog,12000);  // 全局登录态看门：任何页面(含iframe子页)平台失效即弹统一恢复窗，不跳页

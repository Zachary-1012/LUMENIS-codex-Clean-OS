/* 本地日期（YYYY-MM-DD），避免 toISOString 用 UTC 在北京时间凌晨算成昨天 */
function localDateStr(d){ const x=d||new Date(); const y=x.getFullYear(); const m=String(x.getMonth()+1).padStart(2,'0'); const dd=String(x.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }
/* ===== 全局错误捕获（排查数据空白） ===== */
window.addEventListener('error',function(e){
  console.error('[全局错误]',e.message,e.filename+':'+e.lineno);
  const el=document.getElementById('globalError');
  if(el){el.style.display='block';el.innerHTML='<b>JS错误：</b>'+esc(e.message)+' ('+esc(e.filename||'')+':'+e.lineno+')<br><small>请截图反馈，按F12查看控制台详情</small>'}
});
window.addEventListener('unhandledrejection',function(e){
  console.error('[Promise错误]',e.reason);
  const el=document.getElementById('globalError');
  if(el){el.style.display='block';el.innerHTML='<b>异步错误：</b>'+esc(String(e.reason||''))+'<br><small>请截图反馈，按F12查看控制台详情</small>'}
});

/* ===== 全局fetch拦截器：自动添加Basic Auth认证头 ===== */
(function(){
  const _origFetch = window.fetch;
  const _auth = 'Basic ' + btoa('Zachary:ID082610');
  window.fetch = function(input, init){
    try {
      if (input instanceof Request) {
        // 如果input是Request对象，需要创建新的Request
        const url = input.url.replace(/^https?:\/\/[^@]+@/, ''); // 移除URL中的credentials
        const headers = new Headers(input.headers);
        if(!headers.has('Authorization')) headers.set('Authorization', _auth);
        const newInit = {
          method: input.method,
          headers: headers,
          body: input.body,
          mode: input.mode,
          credentials: input.credentials,
          cache: input.cache,
          redirect: input.redirect,
          referrer: input.referrer,
          integrity: input.integrity
        };
        if(init && init.headers) {
          const extra = new Headers(init.headers);
          extra.forEach((v,k)=>headers.set(k,v));
        }
        return _origFetch.call(this, new Request(url, newInit));
      } else {
        // input是URL字符串
        init = init || {};
        const headers = new Headers(init.headers || {});
        if(!headers.has('Authorization')) headers.set('Authorization', _auth);
        init.headers = headers;
        // 移除URL中可能包含的credentials
        if(typeof input === 'string' && input.includes('@')) {
          input = input.replace(/^https?:\/\/[^@]+@/, '/');
        }
        return _origFetch.call(this, input, init);
      }
    } catch(e) {
      console.error('[fetch拦截器]', e);
      return _origFetch.call(this, input, init);
    }
  };
})();

const $=id=>document.getElementById(id);
let trend=[];let calendarCursor=new Date();  // 默认当前月（不再写死年月，避免跨月失准）
let pageHistory=['overview'];

async function api(u,o){o=o||{};o.headers=Object.assign({'Authorization':'Basic '+btoa('Zachary:ID082610')},o.headers||{});const r=await fetch(u,o);const d=await r.json();if(!r.ok||d.ok===false)throw Error(d.error||`HTTP ${r.status}`);return d}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function toast(msg){const el=$('toast');el.textContent=msg;el.classList.add('show');clearTimeout(window.__toast);window.__toast=setTimeout(()=>el.classList.remove('show'),2600)}
function fmt(n){return Number(n||0).toLocaleString('zh-CN')}
function updateClock(){const n=new Date();$('clock').textContent=n.toLocaleString('zh-CN',{hour12:false}).replace(/\//g,'-')}
setInterval(updateClock,1000);updateClock();

/* ===== 页面路由 ===== */
function navigateTo(pageId){
  document.querySelectorAll('.page-view').forEach(p=>p.classList.remove('active'));
  const target=$('page-'+pageId);
  if(target){
    target.style.opacity='0';
    target.style.transform='translateY(12px)';
    target.classList.add('active');
    window.scrollTo({top:0,behavior:'smooth'});
    requestAnimationFrame(()=>{
      target.style.transition='opacity 0.3s ease,transform 0.3s ease';
      target.style.opacity='1';
      target.style.transform='translateY(0)';
    });
  }
  document.querySelectorAll('.side-item').forEach(x=>x.classList.toggle('active',x.dataset.page===pageId));
  if(pageHistory[pageHistory.length-1]!==pageId)pageHistory.push(pageId);
  if(window.innerWidth<=768){window.__closeMobileNav&&window.__closeMobileNav()}
  // 各页面数据懒加载
  if(pageId==='alerts') renderAlertsPage();
  if(pageId==='cases') renderCasePage();
  if(pageId==='official') renderOfficialPage();
  if(pageId==='brands') renderBrandPage();
  if(pageId==='reports') renderReportsPage();
  if(pageId==='analysis') renderAnalysisPage();
  if(pageId==='monitor') renderMonitorPage();
  if(pageId==='events') loadEventsPage();
  if(pageId==='calendar') refreshCalendar();
  if(pageId==='notes') explorer('notes');
  if(pageId==='swire' && window.renderSwirePage) window.renderSwirePage();
}
function goBack(){
  if(pageHistory.length>1){pageHistory.pop();const prev=pageHistory[pageHistory.length-1];navigateTo(prev);pageHistory.pop()}
  else navigateTo('overview');
}
document.querySelectorAll('[data-page]').forEach(el=>{
  el.addEventListener('click',e=>{e.stopPropagation();const pid=el.dataset.page;if(pid)navigateTo(pid)});
});
document.querySelectorAll('.side-item').forEach(x=>x.onclick=()=>navigateTo(x.dataset.page));
/* ===== 手机端抽屉导航 + 遮罩 ===== */
(function setupMobileNav(){
  const sb=document.querySelector('.sidebar');
  let mask=document.getElementById('navMask');
  if(!mask){mask=document.createElement('div');mask.id='navMask';document.body.appendChild(mask);}
  function setNav(open){
    if(!sb)return;
    sb.classList.toggle('open',open);
    mask.classList.toggle('show',open && window.innerWidth<=768);
    document.body.style.overflow=(open && window.innerWidth<=768)?'hidden':'';
  }
  window.__closeMobileNav=()=>setNav(false);
  $('menuToggle')?.addEventListener('click',e=>{e.stopPropagation();setNav(!sb.classList.contains('open'));});
  mask.addEventListener('click',()=>setNav(false));
  document.addEventListener('click',e=>{
    if(window.innerWidth<=768&&!e.target.closest('.sidebar')&&!e.target.closest('.menu-toggle'))setNav(false);
  });
  window.addEventListener('resize',()=>{if(window.innerWidth>768)setNav(false);});
})();

/* ===== 居中弹窗 ===== */
function openModal(){const m=$('modal');m.classList.add('open');m.setAttribute('aria-hidden','false');document.body.style.overflow='hidden'}
function closeModal(){const m=$('modal');m.classList.remove('open');m.setAttribute('aria-hidden','true');document.body.style.overflow=''}
if($('modalClose'))$('modalClose').onclick=closeModal;
const modalMask=document.querySelector('.modal-mask');if(modalMask)modalMask.onclick=closeModal;
document.addEventListener('keydown',e=>{if(e.key==='Escape'){if($('modal').classList.contains('open'))closeModal()}});

/* ===== tooltip ===== */
function setupTips(){document.querySelectorAll('.tip').forEach(el=>el.addEventListener('click',e=>{if(window.matchMedia('(hover: none)').matches){e.stopPropagation();document.querySelectorAll('.tip-open').forEach(x=>x!==el&&x.classList.remove('tip-open'));el.classList.toggle('tip-open')}}))}setupTips();

/* ===== 图表渲染 ===== */
function spark(values,target,kind='blue'){const el=$(target);if(!el||!values?.length)return;const max=Math.max(...values,1),min=Math.min(...values);const pts=values.map((v,i)=>`${(i/(values.length-1||1))*100},${22-((v-min)/(max-min||1))*18}`).join(' ');el.innerHTML=`<svg viewBox="0 0 100 24" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${kind}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`}
function renderDonut(s){const total=s.total||1,pos=s.positive||0,neu=s.neutral||0,neg=s.negative||0,high=s.high_risk||0,med=s.medium_risk||0,low=s.low_risk||0;const np=neg/total*100,pp=pos/total*100;document.querySelector('#sentimentDonut').style.background=`conic-gradient(#ff3b30 0 ${np}%,#0a84ff ${np}% ${np+pp}%,#c7c7cc ${np+pp}% 100%)`;const rp=high/total*100,rm=med/total*100;document.querySelector('#riskDonut').style.background=`conic-gradient(#ff9f0a 0 ${rp}%,#ff3b30 ${rp}% ${rp+rm}%,#d8d8dc ${rp+rm}% 100%)`;[['mTotal',total],['mPos',pos],['mNeu',neu],['mNeg',neg],['mHigh',high],['mEng',fmt(s.total_engagements)],['lPos',pos],['lNeu',neu],['lNeg',neg],['rHigh',high],['rMed',med],['rLow',low]].forEach(([i,v])=>{if($(i))$(i).textContent=v});[['mPosPct',pos/total],['mNeuPct',neu/total],['mNegPct',neg/total],['lPosPct',pos/total],['lNeuPct',neu/total],['lNegPct',neg/total],['rHighPct',high/total],['rMedPct',med/total],['rLowPct',low/total]].forEach(([i,v])=>{if($(i))$(i).textContent=(v*100).toFixed(1)+'%'});if($('ringNeg'))$('ringNeg').textContent=(neg/total*100).toFixed(0)+'%';if($('ringHigh'))$('ringHigh').textContent=(high/total*100).toFixed(0)+'%'}
function renderCategories(cats){const top=(cats||[]).slice(0,7);const max=Math.max(...top.map(x=>x.count),1);const html=top.map(x=>`<div class="cat-col"><div class="cat-bar-wrap"><div class="cat-bar" style="height:${Math.max(4,x.count/max*100)}%" title="${esc(x.category)}：${x.count}"></div></div><b>${x.count}</b><span>${esc(x.category||'其他')}</span></div>`).join('')||'<div class="muted">暂无分类数据</div>';if($('categoryChart'))$('categoryChart').innerHTML=html}
function renderMonitorDonuts(s){
  const total=s.total||1,pos=s.positive||0,neu=s.neutral||0,neg=s.negative||0;
  const high=s.high_risk||0,med=s.medium_risk||0,low=s.low_risk||0;
  const pct=n=>total>0?(n/total*100).toFixed(1):'0.0';
  // 情感分布
  if($('lPos')){$('lPos').textContent=pos;$('lPosPct').textContent=pct(pos)+'%'}
  if($('lNeu')){$('lNeu').textContent=neu;$('lNeuPct').textContent=pct(neu)+'%'}
  if($('lNeg')){$('lNeg').textContent=neg;$('lNegPct').textContent=pct(neg)+'%'}
  if($('ringNeg'))$('ringNeg').textContent=neg;
  if($('sentimentDonut')){const dpct=pct(neg);$('sentimentDonut').style.background=`conic-gradient(#0a84ff 0% ${pct(pos)}%,#8e8e93 ${pct(pos)}% ${(pos+neu)/total*100}%,#ff3b30 ${(pos+neu)/total*100}% 100%)`}
  // 风险等级分布
  if($('rHigh')){$('rHigh').textContent=high;$('rHighPct').textContent=pct(high)+'%'}
  if($('rMed')){$('rMed').textContent=med;$('rMedPct').textContent=pct(med)+'%'}
  if($('rLow')){$('rLow').textContent=low;$('rLowPct').textContent=pct(low)+'%'}
  if($('ringHigh'))$('ringHigh').textContent=high;
  if($('riskDonut')){const hpct=pct(high),mpct=pct(med);$('riskDonut').style.background=`conic-gradient(#0a84ff 0% ${hpct}%,#ff3b30 ${hpct}% ${(high+med)/total*100}%,#ff9f0a ${(high+med)/total*100}% 100%)`}
}
function renderSparks(){const all=trend.map(x=>x.total),neg=trend.map(x=>x.negative),high=trend.map(x=>x.high),eng=trend.map(x=>x.total*1);spark(all,'sparkTotal','#0a84ff');spark(neg,'sparkNeg','#ff3b30');spark(high,'sparkHigh','#ff9f0a');spark(all.map(x=>Math.max(1,Math.round(x*.3))),'sparkPos','#34c759');spark(all.map(x=>Math.max(1,Math.round(x*.55))),'sparkNeu','#8e8e93');spark(eng,'sparkEng','#af52de')}

/* ===== 列表渲染 ===== */
function renderRisk(ns,targetId='riskList'){const el=$(targetId);if(!el)return;el.innerHTML=ns.length?ns.slice(0,8).map(n=>`<div class="risk-row" onclick='openNote(${JSON.stringify(n)})'><span class="risk-score ${esc(n.risk_level)}">${n.risk_level==='high'?'高风险':'中风险'} ${n.risk_score||0}</span><div><div class="risk-title">${esc(n.title||'无标题')}</div><div class="risk-desc">${esc(n.summary||n.ai_reason||'点击查看详情')}</div></div><div class="risk-meta">${esc(n.author_nickname||'匿名')} · ${fmt(n.likes)}赞 · ${fmt(n.comments)}评</div><span class="status-tag ${n.risk_level==='high'?'up':''}">${n.risk_level==='high'?'重点关注':'持续观察'}</span><span class="chev">›</span></div>`).join(''):'<div class="muted">暂无高/中风险内容</div>';if($('sideRisk'))$('sideRisk').textContent=ns.filter(x=>x.risk_level==='high').length}
function topicUrl(topic){return 'https://www.xiaohongshu.com/search_result?keyword='+encodeURIComponent('广州太古汇 '+topic)}
function renderTopics(items,targetId='topicList'){const el=$(targetId);if(!el)return;const list=(items||[]).slice(0,14);el.innerHTML=list.map((x,i)=>`<a class="topic-chip" href="javascript:void(0)" data-ti="${i}" title="查看系统收录的相关笔记案例"><i class="topic-dot ${esc(x.sentiment)}"></i><span>${esc(x.topic)}</span><b>${x.count}</b><span class="xhs">案例 ›</span></a>`).join('')||'<span class="muted">暂无热门话题</span>';el.querySelectorAll('.topic-chip').forEach(a=>{a.onclick=()=>{const x=list[parseInt(a.dataset.ti)];if(x)showNoteCases(x.topic,'keyword='+encodeURIComponent('广州太古汇 '+x.topic),topicUrl(x.topic))}})}
function renderEvents(es,targetId='eventList',limit=8){const el=$(targetId);if(!el)return;el.innerHTML=(es||[]).slice(0,limit).map(e=>{const state=(e.source_count||0)>=2?'多来源':(e.mention_count||0)>=3?'持续升温':e.fact_status==='confirmed'?'已核实':'待核实';const rvTag=e.negative_confirmed===1?'<span class="tag" style="background:#e8f9ee;color:#1a9e54">已确认负面</span>':e.negative_confirmed===2?'<span class="tag" style="background:#f0f0f0;color:#888">已驳回</span>':((e.risk_level==='high'||e.risk_level==='medium')?'<span class="tag" style="background:#fff4e5;color:#e08600">待二次确认</span>':'');return `<article class="event-card" onclick='openEvent(${JSON.stringify(e)})'><span class="event-severity ${esc(e.risk_level)}"></span><div><h4>${esc(e.title||'未命名事件')}</h4><p>${esc(e.summary||'等待更多来源与事实核验')}</p><div class="event-meta"><span class="tag">${state}</span>${rvTag}<span class="tag">${e.source_count||1} 类来源</span><span class="tag">${e.mention_count||0} 条提及</span></div></div><div class="event-right"><b>${e.risk_score||0}</b><span>风险分</span></div></article>`}).join('')||'<div class="muted">暂无事件信号</div>'}

/* ===== 事件中心：质量分级加载（重点事件 + 单篇泛化讨论折叠，可展开）===== */
async function loadEventsPage(){
  const list=$('eventList'), more=$('eventListMore');
  if(!list) return;
  try{
    const d=await api('/api/events');  // 默认 curated：重点事件
    const es=d.events||[];
    renderEvents(es,'eventList',50);
    if(!es.length) list.innerHTML='<div class="muted" style="padding:24px;text-align:center">当前无重点舆情事件</div>';
    if(more){
      const gc=d.generic_count||0;
      more.innerHTML = gc>0
        ? `<button id="eventMoreBtn" class="action secondary" style="width:100%;margin-top:10px;justify-content:center">▸ 另有 ${gc} 条单篇泛化讨论已折叠，点击展开</button>`
        : '';
      const btn=$('eventMoreBtn');
      if(btn) btn.onclick=async()=>{
        btn.disabled=true; btn.textContent='加载中…';
        try{
          const all=await api('/api/events?include=all');
          // 仅追加泛化/非重点（重点已在上方）
          const curIds=new Set(es.map(e=>e.id));
          const extra=(all.events||[]).filter(e=>!curIds.has(e.id));
          more.innerHTML = `<div class="muted" style="margin:12px 0 6px;font-size:12px">— 以下为单篇泛化讨论，供回溯 —</div>`
            + (extra.map(e=>{const state=e.fact_status==='confirmed'?'已核实':'待核实';
              return `<article class="event-card" style="opacity:.82" onclick='openEvent(${JSON.stringify(e)})'><span class="event-severity ${esc(e.risk_level||'low')}"></span><div><h4 style="font-weight:500">${esc(e.title||'未命名事件')}</h4><p>${esc(e.summary||'')}</p><div class="event-meta"><span class="tag">${state}</span><span class="tag">${e.mention_count||1} 条提及</span></div></div><div class="event-right"><b>${e.risk_score||0}</b><span>风险分</span></div></article>`;}).join('')||'<div class="muted">无更多</div>');
        }catch(err){btn.disabled=false;btn.textContent='加载失败，点击重试';toast('展开失败：'+err.message)}
      };
    }
  }catch(e){list.innerHTML='<div class="muted" style="padding:24px;text-align:center">事件加载失败：'+esc(e.message)+'</div>'}
}
function renderTrend(days){trend=days||[];const el=$('trendChart');if(!trend.length){if(el)el.innerHTML='<div class="muted">暂无趋势数据</div>';return}const max=Math.max(...trend.map(x=>Math.max(x.total,x.negative,x.high)),1);if(el)el.innerHTML=trend.map(x=>`<div class="bar-group"><div class="bar all" style="height:${Math.max(3,x.total/max*100)}%"></div><div class="bar neg" style="height:${Math.max(2,x.negative/max*100)}%"></div><div class="bar high" style="height:${Math.max(2,x.high/max*100)}%"></div><span class="bar-label">${esc(x.label)}</span></div>`).join('');renderSparks()}

/* ===== 日历 ===== */
let calendarData={};
async function loadCalendarData(){const y=calendarCursor.getFullYear(),m=calendarCursor.getMonth();const start=`${y}-${String(m+1).padStart(2,'0')}-01`,end=`${y}-${String(m+1).padStart(2,'0')}-${new Date(y,m+1,0).getDate()}`;try{const d=await api(`/api/notes?date_start=${start}&date_end=${end}&per_page=500`);calendarData={};(d.notes||[]).forEach(n=>{const dt=(n.publish_date||n.publish_datetime||n.collected_at||'').substring(0,10);if(dt){if(!calendarData[dt])calendarData[dt]={total:0,neg:0,high:0};calendarData[dt].total++;if(n.sentiment==='negative')calendarData[dt].neg++;if(n.risk_level==='high')calendarData[dt].high++}})}catch(e){console.warn('日历数据加载失败',e)}}
function renderCalendar(targetId='calendarGrid',titleId='calendarTitle'){const y=calendarCursor.getFullYear(),m=calendarCursor.getMonth();if($(titleId))$(titleId).textContent=`${y}年${m+1}月`;const first=new Date(y,m,1).getDay();const start=(first+6)%7;const days=new Date(y,m+1,0).getDate();let h=['一','二','三','四','五','六','日'].map(x=>`<div class="day-head">${x}</div>`).join('');for(let i=0;i<start;i++)h+='<div></div>';for(let d=1;d<=days;d++){const dt=`${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;const cd=calendarData[dt];const cnt=cd?.total||0;const cls=cnt>=8?'high':cnt>=4?'med':cnt>=1?'low':'';h+=`<div class="day ${cls}" onclick="openDayNotes('${dt}')" title="${dt}：${cnt}条笔记"><b>${d}</b>${cnt?`<span class="count">${cnt}条</span>`:''}</div>`}const el=$(targetId);if(el)el.innerHTML=h}
/* 进入日历页/翻月后统一刷新：先画空框→拉当月数据→重绘，保证每次进入都是最新 */
async function refreshCalendar(){renderCalendar();renderCalendar('calendarGrid2','calendarTitle2');try{await loadCalendarData()}catch(e){}renderCalendar();renderCalendar('calendarGrid2','calendarTitle2')}

/* ===== 详情弹窗 ===== */
async function openDayNotes(dateStr){try{const d=await api(`/api/notes?date_start=${dateStr}&date_end=${dateStr}&per_page=50`);const notes=d.notes||[];const pos=notes.filter(n=>n.sentiment==='positive').length,neg=notes.filter(n=>n.sentiment==='negative').length,high=notes.filter(n=>n.risk_level==='high').length;$('modalContent').innerHTML=`<div class="modal-eyebrow">舆情日历 · 当天笔记</div><h2 class="modal-title">${dateStr}</h2><div class="day-summary"><span>共 <b>${notes.length}</b> 条</span><span class="positive">正面 ${pos}</span><span class="neutral">中性 ${notes.length-pos-neg}</span><span class="negative">负面 ${neg}</span><span class="risk">高风险 ${high}</span></div><div class="note-day-list">${notes.length?notes.map(n=>`<div class="note-day-item" onclick='openNote(${JSON.stringify(n)})'><div class="note-day-title">${esc(n.title||'无标题')}</div><div class="note-day-meta"><span class="tag ${esc(n.sentiment||'neutral')}">${n.sentiment==='negative'?'负面':n.sentiment==='positive'?'正面':'中性'}</span><span class="tag ${esc(n.risk_level||'low')}">${n.risk_level==='high'?'高风险':n.risk_level==='medium'?'中风险':'低风险'}</span><span>${esc(n.author_nickname||'匿名')}</span><span>${fmt(n.likes)}赞 ${fmt(n.comments)}评</span></div></div>`).join(''):'<div class="muted">当天暂无有效笔记</div>'}</div>`;openModal()}catch(e){toast('加载当天笔记失败：'+e.message)}}
/* ===== 话题/品牌 → 已收录笔记案例下钻（一层级弹窗） ===== */
let _caseNotes=[];
async function showNoteCases(title, query, externalUrl, apiUrl){
  try{
    const d=await api(apiUrl || `/api/notes?per_page=50&${query||''}`);
    _caseNotes=d.notes||[];
    const pos=_caseNotes.filter(n=>n.sentiment==='positive').length;
    const neg=_caseNotes.filter(n=>n.sentiment==='negative').length;
    const list=_caseNotes.length?_caseNotes.map((n,i)=>`<div class="note-day-item" onclick="openNote(window._caseNotes[${i}])"><div class="note-day-title">${esc(n.title||'无标题')}</div><div class="note-day-meta"><span class="tag ${esc(n.sentiment||'neutral')}">${n.sentiment==='negative'?'负面':n.sentiment==='positive'?'正面':'中性'}</span><span class="tag ${esc(n.risk_level||'low')}">${n.risk_level==='high'?'高风险':n.risk_level==='medium'?'中风险':'低风险'}</span><span>${esc(n.author_nickname||'匿名')}</span><span>${fmt(n.likes)}赞 ${fmt(n.comments)}评</span></div></div>`).join(''):'<div class="muted">系统暂未收录相关笔记，可前往平台检索后补充入库</div>';
    $('modalContent').innerHTML=`<div class="modal-eyebrow">案例收录 · 相关笔记</div><h2 class="modal-title">${esc(title)}</h2><div class="day-summary"><span>系统收录 <b>${d.total||_caseNotes.length}</b> 条</span><span class="positive">正面 ${pos}</span><span class="neutral">中性 ${_caseNotes.length-pos-neg}</span><span class="negative">负面 ${neg}</span></div>${externalUrl?`<p style="margin:8px 0"><a href="${externalUrl}" target="_blank" rel="noopener">前往小红书检索更多 ›</a></p>`:''}<div class="note-day-list">${list}</div>`;
    openModal();
  }catch(e){toast('案例加载失败：'+e.message)}
}
function showCategoryCases(cat){ showNoteCases(cat+' · 业态收录笔记','category='+encodeURIComponent(cat)); }
function openNote(n){
  const bodyText=(n.content||n.body||'').trim();
  let mk=[];try{mk=JSON.parse(n.matched_keywords||'[]');if(!Array.isArray(mk))mk=[]}catch(_){mk=(n.matched_keywords||'').split(',').map(s=>s.trim()).filter(Boolean)}
  const SENT={negative:'负面',positive:'正面',neutral:'中性'},RISK={high:'高风险',medium:'中风险',low:'低风险'};
  const pub=(n.publish_date||n.publish_datetime||'').substring(0,10);
  $('modalContent').innerHTML=`<div class="modal-eyebrow">小红书笔记 · 详情分析</div>
  <h2 class="modal-title">${esc(n.title||'无标题')}</h2>
  <p class="big-summary">${esc(n.summary||n.ai_reason||'暂无摘要')}</p>
  ${bodyText?`<div class="note-body-block"><div class="modal-eyebrow" style="margin:10px 0 6px">笔记正文</div><div class="note-body-text">${esc(bodyText)}</div></div>`:'<p class="muted" style="font-size:12px;margin:6px 0">正文尚未抓取（详情页补抓后在此展示）</p>'}
  <div class="kv"><span>发布日期</span><b>${esc(pub||'未知')}</b></div>
  <div class="kv"><span>采集时间</span><span>${esc(n.collected_at||'—')}</span></div>
  <div class="kv"><span>作者</span><span>${esc(n.author_nickname||'匿名')}</span></div>
  <div class="kv"><span>情感 / 风险</span><b>${SENT[n.sentiment]||'中性'} · ${RISK[n.risk_level]||'低风险'} ${n.risk_score||0}</b></div>
  <div class="kv"><span>内容分类</span><span>${esc(n.category||'未分类')}</span></div>
  <div class="kv"><span>事实状态</span><span>${esc(n.verification_status||'待核实')} · 可信度 ${(Number(n.verification_confidence||0)*100).toFixed(0)}%</span></div>
  <div class="kv"><span>互动量</span><span>${fmt(n.likes)}赞 · ${fmt(n.comments)}评 · ${fmt(n.collects)}藏 · ${fmt(n.shares)}分享</span></div>
  ${(mk.length||n.source_keyword)?`<div class="kv"><span>命中关键词</span><span>${(mk.length?mk:[n.source_keyword]).filter(Boolean).map(k=>`<span class="tag">${esc(k)}</span>`).join(' ')}</span></div>`:''}
  <div class="kv"><span>研判依据</span><span>${esc(n.ai_reason||'规则引擎判断')}</span></div>
  ${n.ai_insight?`<div class="kv"><span>AI 洞察</span><span>${esc(n.ai_insight)}</span></div>`:''}
  ${n.url?`<p><a href="${esc(n.url)}" target="_blank" rel="noopener">打开小红书原文 ›</a></p>`:''}`;
  openModal()}
function openEvent(e){const FACT={unconfirmed:'待核实',confirmed:'已核实',verifying:'核实中','false':'不实信息',refuted:'已辟谣'};const IMPACT={negative:'偏负面',positive:'偏正面',neutral:'neutral',mixed:'多面'};const ESTATUS={active:'监测中',monitoring:'监测中',resolved:'已平息',closed:'已关闭'};const RISK={high:'高风险',medium:'中风险',low:'低风险'};let kws=[];try{kws=JSON.parse(e.keywords||'[]')}catch(_){kws=[]}if(!Array.isArray(kws))kws=[];const isNormDate=/^\d{4}-\d{2}-\d{2}$/.test(e.event_date||'');$('modalContent').innerHTML=`<div class="modal-eyebrow">舆情事件 · 聚合分析</div><h2 class="modal-title">${esc(e.title||'未命名事件')}</h2><p class="big-summary">${esc(e.summary||'暂无事件摘要，系统正在聚合更多来源并进行事实核验。')}</p><div class="kv"><span>发生日期</span><b>${isNormDate?esc(e.event_date):'待核实（将由关联笔记最早发布日期回填）'}</b></div><div class="kv"><span>事件状态</span><b>${esc(ESTATUS[e.status]||'监测中')}</b></div><div class="kv"><span>事实状态</span><b>${esc(FACT[e.fact_status]||'待核实')}</b></div><div class="kv"><span>影响方向</span><b>${esc(IMPACT[e.impact]||'中性')}</b></div><div class="kv"><span>风险等级</span><b>${esc(RISK[e.risk_level]||e.risk_level||'—')} · 风险分 ${e.risk_score||0}</b></div><div class="kv"><span>风险研判</span><span>${esc(e.risk_reason||'暂无')}</span></div><div class="kv"><span>建议动作</span><span>${esc(e.recommended_action||'持续观察，等待更多事实核验')}</span></div><div class="kv"><span>发现窗口</span><span>${esc(e.first_seen||'—')} → ${esc(e.last_seen||'—')}（系统采集发现，非发生日期）</span></div><div class="kv"><span>覆盖</span><span>${e.source_count||1} 类来源 · ${e.mention_count||1} 条提及</span></div>${kws.length?`<div class="kv"><span>关联关键词</span><span>${kws.map(k=>`<span class="tag">${esc(k)}</span>`).join(' ')}</span></div>`:''}<div class="kv"><span>负面二次确认</span><b id="evRvState">${e.negative_confirmed===1?'已确认负面':e.negative_confirmed===2?'已驳回（误报）':'待人工确认'}</b></div><div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap"><button class="action" id="evConfirmBtn" style="background:#34c759;color:#fff;border:none">确认负面</button><button class="action secondary" id="evRejectBtn">驳回 / 误报</button><button class="action secondary" id="eventCaseBtn">查看该事件相关笔记案例</button></div>`;openModal();const RVTXT={1:'已确认负面',2:'已驳回（误报）'};const doEventRv=async(st,btn)=>{btn.disabled=true;try{const r=await api(`/api/event-review/${e.id}/${st===1?'confirm':'reject'}`,{method:'POST'});if(r&&r.ok){e.negative_confirmed=st;const lab=$('evRvState');if(lab)lab.textContent=RVTXT[st];toast(st===1?(`已确认负面，事件从未办清单移除${r.notes_linked?`，并联动确认 ${r.notes_linked} 条关联负面笔记`:''}`):'已驳回，事件从未办清单移除')}else{toast((r&&r.error)||'操作失败');btn.disabled=false}}catch(err){toast('操作失败：'+err.message);btn.disabled=false}};const cfBtn=$('evConfirmBtn'),rjBtn=$('evRejectBtn');if(cfBtn)cfBtn.onclick=()=>doEventRv(1,cfBtn);if(rjBtn)rjBtn.onclick=()=>doEventRv(2,rjBtn);const btn=$('eventCaseBtn');if(btn)btn.onclick=()=>showNoteCases((e.title||'事件')+' · 相关笔记',null,null,'/api/events/'+e.id+'/notes');}
function openAIResult(d){$('modalContent').innerHTML=`<div class="modal-eyebrow">AI 接口测试</div><h2 class="modal-title">${esc(d.provider||'local_rule')}</h2><p class="big-summary">${esc(d.message||'')}</p><div class="kv"><span>模型</span><span>${esc(d.model||'—')}</span></div><div class="kv"><span>测试结果</span><span>${esc(d.reply||'—')}</span></div><div class="kv"><span>降级策略</span><span>AI 不可用时自动回退本地规则，不影响系统运行。</span></div>`;openModal()}

/* ===== 数据加载（使用合并API，减少并发请求，提高稳定性）===== */
async function load(){try{const d=await api('/api/dashboard/all');const s=d.stats||{},r=d.risk_alerts||[],e=d.events||[],t=d.hot_topics||[],o=d.overview||{},st=d.system_status||{};renderDonut(Object.assign({}, s.sentiment||{}, {total: s.total||1, high_risk: s.high_risk||0, medium_risk: s.medium_risk||0, low_risk: s.low_risk||0, total_engagements: s.total_engagements||0, total_comments: s.total_comments||0}));renderMonitorDonuts(s);renderCategories(s.categories||[]);renderRisk(r.notes||r||[]);renderRisk(r.notes||r||[],'riskListHome');renderEvents(e.events||e||[],'eventListHome',8);renderTopics(t.topics||t||[]);renderTopics(t.topics||t||[],'topicListHome');renderTrend(o.trend||[]);$('systemState').textContent=st.ai_enabled?'系统运行中':'系统运行中 · 本地分析';$('lastUpdate').textContent='最后更新：'+(st.last_collection?.finished_at||d.server_time||'—');$('versionText').textContent=st.version||'5.8.3';const aiSt=d.ai_status||{};$('aiStatusText').textContent=aiSt.enabled?(aiSt.ai_detail||'AI Provider 已连接'):'本地规则引擎已接管，可按需接入本地AI';$('progressBar').style.width='100%';renderAIStatusLite(aiSt);applyMergedAlerts(d.alerts||[],d.unread_alerts);applyPendingNegative(d.pending_negative);
/* v5.9.0 统一数据总线：主轮询数据广播给其他模块，替代它们各自独立轮询 */
window.__TAIKOO_POLL__=d;try{document.dispatchEvent(new CustomEvent('taikoo-poll',{detail:d}))}catch(_){}
// 舆情监测页补充categories数据（dashboard/all可能不含categories）
if(!s.categories||!s.categories.length){api('/api/stats').then(sd=>{if(sd.categories)renderCategories(sd.categories)}).catch(()=>{})}
updateCollectCard();
}catch(e){console.warn('合并API加载失败，回退独立API:',e.message);loadFallback()}}
async function loadFallback(){try{const [s,r,e,t,o,st]=await Promise.all([api('/api/stats'),api('/api/risk-alerts'),api('/api/events'),api('/api/hot-topics?limit=14'),api('/api/overview'),api('/api/status')]);renderDonut(s.stats||{});renderCategories(s.categories||[]);renderRisk(r.notes||[]);renderRisk(r.notes||[],'riskListHome');renderEvents(e.events||[],'eventListHome',8);renderTopics(t.topics||[]);renderTopics(t.topics||[],'topicListHome');renderTrend(o.trend||[]);$('systemState').textContent=st.ai_enabled?'系统运行中':'系统运行中 · 本地分析';$('lastUpdate').textContent='最后更新：'+(st.last_collection?.finished_at||st.server_time||'—');$('versionText').textContent=st.version||'5.8.3';$('aiStatusText').textContent=st.ai_enabled?(st.ai_detail||'AI Provider 已连接'):'本地规则引擎已接管，可按需接入本地AI';$('progressBar').style.width='100%'}catch(e){toast('读取数据失败：'+e.message)}}
/* ===== v5.9.0 合并轮询辅助：纯渲染，不再独立发请求 ===== */
function renderAIStatusLite(d){try{const live=$('aiLive');if($('aiProvider'))$('aiProvider').textContent=d.provider||'local_rule';if($('aiModel'))$('aiModel').textContent=d.model||'—';if($('aiRuntime'))$('aiRuntime').textContent=d.enabled?(d.runtime==='local'?'本地 AI 已连接':'云端 AI 已连接'):'本地规则引擎';if(live){live.innerHTML='<i></i>'+esc(d.enabled?'已连接':'规则模式');live.classList.toggle('off',!d.enabled)}if($('aiHints'))$('aiHints').innerHTML=(d.hints||[]).map(h=>`<span>${esc(h.detail)}</span>`).join('')}catch(e){}}
function applyMergedAlerts(alerts,unread){try{const n=(typeof unread==='number')?unread:alerts.length;const badge=$('alertBadge');if(badge){badge.textContent=n;badge.style.display=n>0?'flex':'none'}const side=$('sideAlertBadge');if(side){side.textContent=n;side.style.display=n>0?'flex':'none'}(alerts||[]).slice(0,3).forEach(a=>{if(!shownAlertIds.has(a.id)){shownAlertIds.add(a.id);showAlertPopup(a)}})}catch(e){}}
function applyPendingNegative(n){try{if(typeof n!=='number')return;document.querySelectorAll('[data-badge="pending-negative"]').forEach(b=>{b.textContent=n;b.style.display=n>0?'flex':'none'});if(window.BadgeManager&&typeof BadgeManager.setCount==='function')BadgeManager.setCount('negative',n)}catch(e){}}
async function loadAIStatus(){try{const d=await api('/api/ai/status');const live=$('aiLive');$('aiProvider').textContent=d.provider||'local_rule';$('aiModel').textContent=d.model||'—';$('aiRuntime').textContent=d.enabled?(d.runtime==='local'?'本地 AI 已连接':'云端 AI 已连接'):'本地规则引擎';live.innerHTML='<i></i>'+esc(d.enabled?'已连接':'规则模式');live.classList.toggle('off',!d.enabled);$('aiHints').innerHTML=(d.hints||[]).map(h=>`<span>${esc(h.detail)}</span>`).join('');return d}catch(e){toast('AI状态读取失败：'+e.message)}}
async function testAI(){try{const d=await api('/api/ai/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'请用一句话说明广州太古汇舆情监测系统的核心监测对象。'})});toast(d.message||'AI测试完成');if(d.reply)openAIResult(d);await loadAIStatus()}catch(e){toast(e.message)}}

/* ===== 笔记工作区 ===== */
async function explorer(tab='notes'){document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));const el=$('explorerContent');if(tab==='notes'){const d=await api('/api/notes?per_page=12');el.innerHTML=`<div class="rows">${(d.notes||[]).map(n=>`<div class="row" onclick='openNote(${JSON.stringify(n)})'><span>${esc(n.title||'无标题')}</span><span class="muted">${n.sentiment||'neutral'} · ${n.risk_level||'low'} ${n.risk_score||0}</span></div>`).join('')}</div>`}else if(tab==='web'){const d=await api('/api/web-mentions?limit=20');el.innerHTML=`<div class="rows">${(d.mentions||[]).map(n=>`<div class="row"><span>${esc(n.title||'无标题')}</span><span class="muted">${esc(n.source_platform||'web')} · ${n.sentiment||'neutral'}</span></div>`).join('')}</div>`}else if(tab==='history'){el.innerHTML='<div class="rows"><div class="row"><span>历史复核</span><span class="muted">保留完整审计轨迹，不直接删除原始笔记</span></div><div class="row"><span>主体校验</span><span class="muted">广州太古汇优先，其他城市同名场景默认排除</span></div><div class="row"><span>AI兜底</span><span class="muted">无外部AI时使用本地规则分析</span></div></div>'}else{el.innerHTML='<div class="report-grid"><div class="report-card"><b>日报</b><p>当天事件、风险与传播变化</p></div><div class="report-card"><b>周报</b><p>一周事件演化与重点信号</p></div><div class="report-card"><b>月报</b><p>月度趋势与重点话题</p></div><div class="report-card"><b>年报</b><p>长期结构与事件沉淀</p></div></div>'}}
document.querySelectorAll('.tab').forEach(x=>x.onclick=()=>explorer(x.dataset.tab));

/* ===== 数据更新卡片：真实调度状态（合并到主轮询，不独立定时）===== */
async function updateCollectCard(){
  const el=$('todayRuns'); if(!el) return;  // 卡片不存在则跳过
  try{
    const d=await api('/api/collect/schedule-status');
    if(!d||!d.ok) return;
    $('todayRuns').textContent=`${d.today_runs||0}/${d.max_daily_runs||12}`;
    $('manualLeft').textContent=`${d.manual_left??3}/${d.manual_total??3}`;
    $('autoLeft').textContent=`${d.auto_left??9}/${d.auto_total??9}`;
    // 今日实际入库 + 上次/下次采集
    const hours=$('collectHours');
    if(hours) hours.innerHTML=`<div class="collect-row"><span>今日入库</span><b>${d.today_inserted||0} 条</b></div>
      <div class="collect-row"><span>上次采集</span><b style="font-weight:500;font-size:11px">${esc(d.last_collect||'无')}</b></div>
      <div class="collect-row"><span>下次计划</span><b style="font-weight:500;font-size:11px">${esc(d.next_collect||'—')}</b></div>`;
    // 状态机 → 颜色与文案（0次采集不再显示绿色就绪）
    const st=$('collectState');
    if(st){
      const map={
        ok:['就绪 · 今日已采集','status-ready'],
        running:['采集中…','status-running'],
        cooldown:['冷却保护中','status-warn'],
        pending:['今日尚未采集','status-warn'],
        blocked:['采集受限·熔断','status-error'],
        no_cookie:['未配置登录态','status-error']
      };
      const [txt,cls]=map[d.state]||['未知','status-warn'];
      st.textContent=d.state==='cooldown'?(d.state_cn||txt):txt;
      st.className=cls;
      if(d.circuit&&d.circuit.open&&d.circuit.detail) st.title='熔断原因：'+d.circuit.detail+'，恢复：'+(d.circuit.resume_at||'');
    }
  }catch(e){/*静默，不影响主面板*/}
}

/* ===== 采集刷新 ===== */
async function refresh(){try{toast('开始从小红书采集新笔记（固定账号保护模式）…');$('progressBar').style.width='8%';const s=await api('/api/xhs/cookie/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_type:'manual',max_scroll:6})});if(!s.task_id)throw new Error(s.error||'采集任务未创建');const xres=await pollXhs(s.task_id);$('progressBar').style.width='60%';const d=await api('/api/intelligence/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:5000})});$('progressBar').style.width='75%';if(d.task_id){await poll(d.task_id);}else{$('progressBar').style.width='100%';load();}}catch(e){toast(e.message);}}
async function pollXhs(id){for(let i=0;i<160;i++){await new Promise(r=>setTimeout(r,3000));let t;try{const dd=await api('/api/xhs/cookie/sync/'+id);t=dd.task;}catch(_){continue;}if(!t)continue;if(t.progress)$('progressBar').style.width=Math.min(58,10+t.progress*0.45)+'%';if(t.status==='done'){const r=t.result||{};if(r.blocked){toast('采集被拦截：'+r.blocked);}else{toast('小红书采集完成：新增 '+(r.inserted||0)+' 条，更新 '+(r.updated||0)+' 条');}return r;}if(t.status==='error'){throw new Error(t.message||'小红书采集失败');}}throw new Error('小红书采集超时（超过8分钟）');}
async function poll(id){for(let i=0;i<120;i++){await new Promise(r=>setTimeout(r,2500));try{const d=await api('/api/collect/status/'+id);$('progressBar').style.width=Math.min(95,62+i*0.3)+'%';if(d.task?.status==='done'){toast('AI复核与事件聚合完成');$('progressBar').style.width='100%';load();return;}if(d.task?.status==='error'){toast('复核任务失败：'+(d.task.message||''));return;}}catch(e){return;}}}

/* ===== 事件绑定（全部加null保护，防止元素不存在导致JS中断） ===== */
if($('refreshBtn'))$('refreshBtn').onclick=refresh;
if($('quickRefresh'))$('quickRefresh').onclick=refresh;
if($('rednoteBtn'))$('rednoteBtn').onclick=collectRednote;
/* rednote 为备选采集方式：顶部不主显示，入口收至「系统设置」面板 */
function mountRednoteAlt(){
  const grid=document.querySelector('.settings-grid');
  if(grid&&!document.getElementById('rednoteAltEntry')){
    const d=document.createElement('div');
    d.id='rednoteAltEntry';
    d.innerHTML='<b>备选采集方式</b><button class="action secondary" id="rednoteAltBtn" style="margin-top:6px;padding:5px 12px;font-size:12px;">◎ rednote / CDP 采集</button>';
    grid.appendChild(d);
    const ab=d.querySelector('#rednoteAltBtn');
    if(ab)ab.onclick=collectRednote;
  }
}
mountRednoteAlt();
document.addEventListener('DOMContentLoaded',mountRednoteAlt);
if($('reviewBtn'))$('reviewBtn').onclick=async()=>{try{await api('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:5000})});toast('历史库复核完成');load()}catch(e){toast(e.message)}};
if($('reportBtn'))$('reportBtn').onclick=()=>navigateTo('reports');
if($('generateReport'))$('generateReport').onclick=async()=>{try{await api('/api/report/generate',{method:'POST'});toast('报告已生成');explorer('reports')}catch(e){toast(e.message)}};
if($('langBtn'))$('langBtn').onclick=()=>toast('语言入口已保留：中文 / English / 한국어');
if($('prevMonth'))$('prevMonth').onclick=()=>{calendarCursor.setMonth(calendarCursor.getMonth()-1);refreshCalendar()};
if($('nextMonth'))$('nextMonth').onclick=()=>{calendarCursor.setMonth(calendarCursor.getMonth()+1);refreshCalendar()};
if($('prevMonth2'))$('prevMonth2').onclick=$('prevMonth').onclick;
if($('nextMonth2'))$('nextMonth2').onclick=$('nextMonth').onclick;
const _backThisMonth=()=>{const n=new Date();calendarCursor=new Date(n.getFullYear(),n.getMonth(),1);refreshCalendar()};
if($('todayMonth2'))$('todayMonth2').onclick=_backThisMonth;
if($('todayMonth'))$('todayMonth').onclick=_backThisMonth;
if($('aiDetectBtn'))$('aiDetectBtn').onclick=loadAIStatus;
if($('aiTestBtn'))$('aiTestBtn').onclick=testAI;

/* 导航到预警页面时加载预警列表 */
const _origNavigate=navigateTo;
navigateTo=function(pageId){_origNavigate(pageId);if(pageId==='alerts')renderAlertsPage();if(pageId==='reports')loadReportPreview()};

/* ===== 初始化 ===== */
refreshCalendar();
load();loadAIStatus();explorer();
/* v5.9.0 统一主轮询：仅一个60秒 dashboard/all，AI状态/预警/待审由其合并字段驱动，不再并发独立轮询 */
setInterval(load,60000);

/* ===== v5.4 舆情预警弹窗通知 ===== */
let shownAlertIds = new Set();
async function loadAlerts(){try{const d=await api('/api/alerts?unread=1');const alerts=d.alerts||[];const badge=$('alertBadge');if(badge)badge.textContent=d.unread_count||0;if(badge)badge.style.display=d.unread_count>0?'flex':'none';const sideBadge=$('sideAlertBadge');if(sideBadge)sideBadge.textContent=d.unread_count||0;alerts.slice(0,3).forEach(a=>{if(!shownAlertIds.has(a.id)){shownAlertIds.add(a.id);showAlertPopup(a)}})}catch(e){console.warn('预警加载失败',e)}}
function showAlertPopup(alert){const container=$('alertContainer');if(!container)return;const typeLabel=alert.type==='risk'?'高风险':alert.type==='influence'?'高影响力':'上升过快';const typeClass=alert.type==='risk'?'risk':alert.type==='influence'?'influence':'rising';const el=document.createElement('div');el.className='alert-popup '+typeClass;el.innerHTML=`<div class="alert-icon">△</div><div class="alert-body"><div class="alert-title">${esc(typeLabel)}舆情预警</div><div class="alert-msg">${esc(alert.message||alert.title||'')}</div><div class="alert-meta">${esc(alert.created_at||'')} · 赞${fmt(alert.likes)} 评${fmt(alert.comments)}</div></div><button class="alert-close" data-id="${esc(alert.id)}" data-note="${esc(alert.note_id)}">✕</button>`;container.appendChild(el);setTimeout(()=>el.classList.add('show'),100);el.querySelector('.alert-close').onclick=(e)=>{e.stopPropagation();markAlertRead(alert.id,alert.note_id);el.classList.remove('show');setTimeout(()=>el.remove(),300)};el.onclick=()=>{if(alert.note_id){api('/api/note/'+alert.note_id).then(d=>{if(d.note)openNote(d.note)}).catch(()=>{});markAlertRead(alert.id,alert.note_id)}};setTimeout(()=>{if(el.parentNode){el.classList.remove('show');setTimeout(()=>el.remove(),300)}},15000)}
async function markAlertRead(alertId,noteId){try{await api('/api/alerts/read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({alert_id:alertId||noteId})});loadAlerts()}catch(e){console.warn('标记已读失败',e)}}
async function markAllAlertsRead(){try{await api('/api/alerts/read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({all:true})});toast('所有预警已标记为已读');loadAlerts()}catch(e){toast(e.message)}}
async function refreshAlerts(){try{const d=await api('/api/alerts/refresh',{method:'POST'});toast(`预警刷新完成，新增${d.new_alerts||0}条`);loadAlerts()}catch(e){toast(e.message)}}

/* ===== v5.4 报告导出（表格模式） ===== */
function exportReport(type){const date=prompt('请输入日期（YYYY-MM-DD），留空使用今天：','')||localDateStr();const url=`/api/report/export?type=${type}&date=${date}`;window.open(url,'_blank');toast(`${type==='daily'?'日报':type==='weekly'?'周报':type==='monthly'?'月报':'年报'}导出中...`)}

/* ===== v5.8.2 报告中心：默认自然周预览，可切换周期/日期 ===== */
async function loadReportPreview(){
  const body=$('reportPreviewBody'); if(!body)return;
  const period=($('rpPeriod')?.value)||'weekly';
  const date=($('rpDate')?.value)||'';
  body.innerHTML='<div class="muted">正在加载报告预览…</div>';
  try{
    const d=await api(`/api/export/preview?period=${period}${date?('&date='+date):''}`);
    if(!d.ok)throw new Error(d.error||'预览失败');
    const r=d.data||{}, sm=r.summary||{}, ev=r.period_events||[];
    const riskBadge=lv=>{const m={high:'risk',medium:'risk',low:''};return `<span class="sentiment-tag ${lv==='high'?'negative':lv==='medium'?'neutral':'positive'}">${{high:'高风险',medium:'中风险',low:'低风险'}[lv]||lv||'—'}</span>`};
    const stat=(label,val)=>`<div style="padding:10px 12px;background:#f8f9fa;border-radius:8px"><div style="font-size:11px;color:#888">${label}</div><b style="font-size:18px">${val??'—'}</b></div>`;
    let html='';
    html+=`<div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px"><b style="font-size:15px">${esc(r.date_range||'')}</b><span class="muted" style="font-size:12px">生成于 ${esc(r.generated_at||'')}</span></div>`;
    html+=`<div style="padding:12px 14px;background:linear-gradient(135deg,#eef4ff,#f6fbff);border-left:3px solid #4a7dff;border-radius:8px;margin-bottom:14px;line-height:1.6">${esc(r.conclusion||'本期无显著舆情。')}</div>`;
    html+=`<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:14px">`
      +stat('有效舆情笔记',sm.total)+stat('正面',sm.positive)+stat('中性',sm.neutral)+stat('负面',sm.negative)
      +stat('高风险',sm.high_risk)+stat('总互动量',fmt(sm.total_engagement))+stat('原始收录',r.raw_total??sm.total)+stat('剔除噪音',r.filtered_noise??0)
      +`</div>`;
    html+=`<h4 style="margin:6px 0 8px;font-size:14px">舆情事件分析</h4>`;
    if(ev.length){
      window.__rpEvents=ev;html+='<div style="display:flex;flex-direction:column;gap:8px;margin-bottom:10px">'+ev.map((e,i)=>`<div onclick='openEvent(window.__rpEvents[${i}])' style="padding:10px 12px;border:1px solid #eef0f4;border-radius:8px;cursor:pointer"><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><b style="font-size:13px">${esc(e.title||'未命名事件')}</b>${riskBadge(e.risk_level)}<span class="muted" style="font-size:12px">发生 ${esc(e.event_date||'待核')}</span><span class="muted" style="font-size:12px">提及 ${e.mention_count??1}</span></div><div class="muted" style="font-size:12px;margin-top:4px;line-height:1.5">${esc(e.summary||e.risk_reason||'')}</div></div>`).join('')+'</div>';
      if(r.period_events_minor>0)html+=`<div class="muted" style="font-size:12px;margin-bottom:10px">另有 ${r.period_events_minor} 起单篇低关注事件已归档，不计入重点分析。</div>`;
    }else{
      html+=`<div class="muted" style="padding:10px 12px;background:#fafbfc;border-radius:8px;margin-bottom:10px">本期无显著聚合舆情事件。</div>`;
    }
    const tops=r.top_engagement_notes||[];
    if(tops.length){
      window.__rpNotes=tops.slice(0,8);
      html+=`<h4 style="margin:6px 0 8px;font-size:14px">重点笔记（负面优先 · Top ${Math.min(8,tops.length)} · 点击查看详情分析）</h4><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px">`
        +tops.slice(0,8).map((n,i)=>{const neg=n.sentiment==='negative';const rc={negative:'var(--danger)',positive:'var(--success)',neutral:'var(--muted)'}[n.sentiment]||'var(--muted)';const cn={negative:'负面',positive:'正面',neutral:'中性'}[n.sentiment]||'';return `<div onclick='openNote(window.__rpNotes[${i}])' style="font-size:13px;display:flex;gap:8px;align-items:flex-start;padding:9px 11px;border:1px solid #eef0f4;border-radius:8px;cursor:pointer;${neg?'background:#fff7f7;border-color:#f3d4d4;font-weight:600':''}"><span class="muted">${i+1}.</span><span style="flex:1;color:${neg?'var(--danger)':'inherit'};line-height:1.45">${esc(n.title||'（无标题）')}</span><span style="white-space:nowrap;color:${rc};font-size:12px">${cn} · ${fmt((n.likes||0)+(n.comments||0)+(n.collects||0)+(n.shares||0))}</span></div>`}).join('')
        +`</div>`;
    }else{
      html+=`<h4 style="margin:6px 0 8px;font-size:14px">重点笔记</h4><div class="muted" style="padding:10px 12px;background:#fafbfc;border-radius:8px;margin-bottom:10px">本周期无负面重点笔记（无）。</div>`;
    }
    body.innerHTML=html;
  }catch(e){body.innerHTML=`<div class="muted">报告预览加载失败：${esc(e.message)}</div>`;console.warn('报告预览失败',e)}
}

/* ===== v5.4 rednote 采集 ===== */
async function collectRednote(){try{const keyword=prompt('搜索关键词：','广州太古汇')||'广州太古汇';const maxDetails=parseInt(prompt('采集详情数量（1-30）：','10'))||10;const d=await api('/api/rednote/collect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyword,max_details:maxDetails,max_scroll:3,persist:true,async:true})});toast(d.message||'rednote采集任务已启动');if(d.task_id)poll(d.task_id)}catch(e){toast(e.message)}}

/* ===== v5.4 预警页面渲染 ===== */
async function renderAlertsPage(){try{const d=await api('/api/alerts?unread=0');const el=$('alertsPageList');if(!el)return;const alerts=d.alerts||[];el.innerHTML=alerts.length?alerts.map(a=>`<div class="alert-row ${a.read?'read':''}" data-id="${esc(a.id)}" data-note="${esc(a.note_id)}"><span class="alert-type ${esc(a.type)}">${a.type==='risk'?'高风险':a.type==='influence'?'高影响力':'上升过快'}</span><div class="alert-info"><div class="alert-row-title">${esc(a.title||a.message||'')}</div><div class="alert-row-meta">${esc(a.created_at||'')} · 赞${fmt(a.likes)} 评${fmt(a.comments)} · 影响力${fmt(a.influence)}</div></div><span class="alert-status ${a.read?'read':'unread'}">${a.read?'已读':'未读'}</span><button class="alert-mark-read" data-id="${esc(a.id)}" data-note="${esc(a.note_id)}">${a.read?'':'标记已读'}</button></div>`).join(''):'<div class="muted">暂无预警通知</div>';el.querySelectorAll('.alert-row').forEach(row=>{row.onclick=(e)=>{if(e.target.classList.contains('alert-mark-read'))return;const noteId=row.dataset.note;if(noteId)api('/api/note/'+noteId).then(d=>{if(d.note)openNote(d.note)}).catch(()=>{})}});el.querySelectorAll('.alert-mark-read').forEach(btn=>{btn.onclick=(e)=>{e.stopPropagation();markAlertRead(btn.dataset.id,btn.dataset.note);renderAlertsPage()}})}catch(e){console.warn('预警页面加载失败',e)}}

/* ===== v5.9.0 预警不再独立定时轮询：未读预警由 60秒主轮询 dashboard/all 合并驱动；
   标记已读/手动刷新等动作后仍可单次调用 loadAlerts() ===== */

/* ===== v5.4 增项接口配置弹窗 ===== */
let currentConfigType = '';
function openConfigModal(type){
  currentConfigType = type;
  const mc = $('modalContent');
  if(type==='company_domain'){
    mc.innerHTML = `<h3>公司域名接入</h3><p style="color:var(--muted);margin-bottom:16px">配置公司域名，后期一键可用，系统自动适配</p><div class="form-group"><label>公司名称</label><input type="text" id="cfgCompanyName" placeholder="广州太古汇" value="广州太古汇"></div><div class="form-group"><label>公司域名</label><input type="text" id="cfgCompanyDomain" placeholder="taikoo-hui.com"></div><div class="form-actions"><button class="action primary" onclick="saveCompanyDomain()">保存配置</button><button class="action tertiary" onclick="deleteCompanyDomain()">删除配置</button></div>`;
    api('/api/config/company-domain').then(d=>{if(d.domain){$('cfgCompanyDomain').value=d.domain;$('cfgCompanyName').value=d.name||'广州太古汇'}}).catch(()=>{});
  } else if(type==='email_push'){
    mc.innerHTML = `<h3>推送邮箱管理</h3><p style="color:var(--muted);margin-bottom:16px">添加/删除日报推送邮箱，支持多邮箱</p><div class="form-group"><label>添加邮箱</label><div style="display:flex;gap:8px"><input type="email" id="cfgEmail" placeholder="example@company.com" style="flex:1"><button class="action primary" onclick="addEmail()">添加</button></div></div><div id="emailList" style="margin-top:16px"></div>`;
    loadEmailList();
  } else if(type==='run_code'){
    mc.innerHTML = `<h3>运行代码（热更新）</h3><p style="color:var(--muted);margin-bottom:16px">复制Python代码进去自动运行，测试OK直接更新系统</p><div class="form-group"><label>Python代码</label><textarea id="cfgCode" rows="12" style="width:100%;font-family:monospace;font-size:12px;padding:12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);resize:vertical" placeholder="# 示例：查询数据库\nresult = db.get_stats()\nprint(result)"></textarea></div><div class="form-actions"><button class="action primary" onclick="runCode()">运行代码</button><label style="display:flex;align-items:center;gap:6px;color:var(--muted);font-size:12px"><input type="checkbox" id="cfgAllowDangerous"> 允许危险操作</label></div><div id="codeResult" style="margin-top:16px;display:none"></div>`;
  } else if(type==='brand_directory'){
    mc.innerHTML = `<h3>场内品牌目录</h3><p style="color:var(--muted);margin-bottom:16px">198个品牌，8大业态，2026.08.20更新</p><div id="brandList" style="max-height:400px;overflow-y:auto"></div>`;
    api('/api/config/brand-directory').then(d=>{const el=$('brandList');if(el){const bs=d.brands||[];el.innerHTML=bs.map((b,i)=>`<div data-bi="${i}" style="padding:8px 4px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;cursor:pointer"><span><b>${esc(b.brand_cn||b.brand_en)}</b> <span style="color:var(--muted)">${esc(b.brand_en)}</span></span><span style="color:var(--muted)">${esc(b.category)} · ${esc(b.shop)} ›</span></div>`).join('');el.querySelectorAll('[data-bi]').forEach(row=>{row.onclick=()=>{const b=bs[+row.dataset.bi];const name=b.brand_cn||b.brand_en;showNoteCases(name+' · 相关收录笔记','keyword='+encodeURIComponent(name))}})}}).catch(()=>{});
  }
  openModal();
}
async function saveCompanyDomain(){try{const name=$('cfgCompanyName').value;const domain=$('cfgCompanyDomain').value;const d=await api('/api/config/company-domain',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,domain})});toast(d.message||'配置已保存');$('companyDomainStatus').textContent=domain?'已配置':'未配置';closeModal()}catch(e){toast(e.message)}}
async function deleteCompanyDomain(){if(!confirm('确定删除公司域名配置？'))return;try{const d=await api('/api/config/company-domain',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'delete'})});toast(d.message||'已删除');$('companyDomainStatus').textContent='未配置';closeModal()}catch(e){toast(e.message)}}
async function loadEmailList(){try{const d=await api('/api/config/emails');const el=$('emailList');if(!el)return;$('emailPushStatus').textContent=(d.count||0)+'个邮箱';el.innerHTML=d.emails.length?d.emails.map(e=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:var(--bg);border-radius:6px;margin-bottom:6px"><span>${esc(e)}</span><button class="action tertiary" style="padding:4px 10px;font-size:12px" onclick="deleteEmail('${esc(e)}')">删除</button></div>`).join(''):'<div style="color:var(--muted);text-align:center;padding:20px">暂无推送邮箱</div>'}catch(e){console.warn(e)}}
async function addEmail(){try{const email=$('cfgEmail').value.trim();if(!email){toast('请输入邮箱');return}const d=await api('/api/config/emails',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});toast(d.message||'邮箱已添加');$('cfgEmail').value='';loadEmailList()}catch(e){toast(e.message)}}
async function deleteEmail(email){try{const d=await api('/api/config/emails',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});toast(d.message||'已删除');loadEmailList()}catch(e){toast(e.message)}}
async function runCode(){try{const code=$('cfgCode').value;const allowDangerous=$('cfgAllowDangerous').checked;const d=await api('/api/config/run-code',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code,allow_dangerous:allowDangerous})});const el=$('codeResult');if(el){el.style.display='block';el.innerHTML=`<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--success)"><b>执行成功</b><pre style="margin-top:8px;white-space:pre-wrap;font-size:12px">${esc(d.result||d.message||'')}</pre></div>`}toast('代码执行成功')}catch(e){const el=$('codeResult');if(el){el.style.display='block';el.innerHTML=`<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--danger)"><b>执行失败</b><pre style="margin-top:8px;white-space:pre-wrap;font-size:12px;color:var(--danger)">${esc(e.message||'')}</pre></div>`}}}

/* ===== v5.8.2 日报弹窗：只推“昨天+当天发布”，一天两窗口，看过即归档 ===== */
let dailyReportShown = false;
async function checkDailyReportPopup(){
  if(dailyReportShown) return;
  const now = new Date();
  const today = now.toISOString().slice(0,10);
  const win = now.getHours() < 15 ? 'morning' : 'evening';  // 早间/晚间两窗口
  const key = 'daily_report_popup_' + today + '_' + win;
  if(localStorage.getItem(key) === 'read') return;          // 本窗口已看过则归档不再弹
  try{
    const d = await api('/api/report/daily?date=' + today);
    const r = d.report;
    if(!r || !r.stats || (r.stats.total||0) === 0){ localStorage.setItem(key,'read'); return; } // 无新内容不打扰
    dailyReportShown = true;
    localStorage.setItem(key, 'read');                     // 看过即归档
    const s = r.stats;
    const level = (s.negative||0) >= 3 ? '🔴 重大' : (s.negative||0) >= 1 ? '🟡 关注' : '🟢 平稳';
    const riskCN = {high:'高',medium:'中',low:'低'};
    const noteList = (r.notes||[]).slice(0,8).map(n=>{
      return `<li style="padding:6px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;gap:8px">
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--danger);font-weight:600">${esc(n.title||'无标题')}</span>
        <span style="color:var(--muted);font-size:12px;white-space:nowrap">${n.publish_date||''} · ${riskCN[n.risk_level]||''}风险 · ${n.engagement||0}互动</span></li>`;
    }).join('') || '<li style="padding:8px 0;color:var(--success)">昨日+今日未发现负面舆情笔记（无）</li>';
    const mc = $('modalContent');
    mc.innerHTML = `<h3>📊 日报速览（仅负面 · 昨日+今日新发布）</h3>
      <div style="text-align:center;padding:14px 0"><div style="font-size:30px;margin-bottom:6px">${level}</div><div style="color:var(--muted);font-size:13px">${esc(r.date_range||today)} · ${win==='morning'?'早间窗口':'晚间窗口'}</div></div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0">
        <div style="text-align:center;padding:10px;background:var(--bg);border-radius:8px"><div style="font-size:22px;font-weight:700">${s.total||0}</div><div style="color:var(--muted);font-size:12px">合计收录</div></div>
        <div style="text-align:center;padding:10px;background:var(--bg);border-radius:8px"><div style="font-size:22px;font-weight:700">${s.yesterday_count||0}</div><div style="color:var(--muted);font-size:12px">昨日</div></div>
        <div style="text-align:center;padding:10px;background:var(--bg);border-radius:8px"><div style="font-size:22px;font-weight:700;color:var(--danger)">${s.negative||0}</div><div style="color:var(--muted);font-size:12px">负面</div></div>
        <div style="text-align:center;padding:10px;background:var(--bg);border-radius:8px"><div style="font-size:22px;font-weight:700;color:var(--danger)">${s.pushed||0}</div><div style="color:var(--muted);font-size:12px">推送条数</div></div>
      </div>
      <div style="padding:12px;background:var(--bg);border-radius:8px;margin-bottom:12px;font-size:13px;line-height:1.6"><b>核心结论：</b>${esc(r.conclusion||'')}</div>
      <div style="max-height:220px;overflow:auto;margin-bottom:14px"><ul style="list-style:none;margin:0;padding:0;font-size:13px">${noteList}</ul></div>
      <div class="form-actions">
        <button class="action primary" onclick="navigateTo('reports');closeModal()">查看完整报告</button>
        <button class="action secondary" onclick="exportReport('daily')">导出日报</button>
        <button class="action tertiary" onclick="closeModal()">知道了，归档</button>
      </div>`;
    openModal();
  }catch(e){ console.log('日报弹窗：暂无昨今新发布', e.message); }
}
setTimeout(checkDailyReportPopup, 5000);

/* ===== v5.4 设置页面加载配置状态 ===== */
async function loadConfigStatus(){
  try{
    const d = await api('/api/config/company-domain');
    if(d.configured && $('companyDomainStatus')) $('companyDomainStatus').textContent = '已配置';
  }catch(e){}
  try{
    const d = await api('/api/config/emails');
    if($('emailPushStatus')) $('emailPushStatus').textContent = (d.count||0) + '个邮箱';
  }catch(e){}
}
setTimeout(loadConfigStatus, 2000);

/* ===== v5.4 品牌业态统计模块 ===== */
const CATEGORY_COLORS = {'女装':'#E91E63','男装':'#2196F3','餐饮':'#FF9800','珠宝钟表':'#9C27B0','美容护理':'#00BCD4','运动休闲':'#4CAF50','鞋包皮具':'#795548','童装玩具':'#FF5722','生活时尚':'#607D8B'};
const CATEGORY_ICONS = {'女装':'👗','男装':'👔','餐饮':'🍽️','珠宝钟表':'💎','美容护理':'💄','运动休闲':'🏃','鞋包皮具':'👜','童装玩具':'🧸','生活时尚':'🏠'};

async function renderBrandStatsPage(){
  // 品牌页已由 BrandIndustry 统一渲染（业态卡片→品牌两级下钻）；旧统计容器不存在时直接跳过，避免冗余请求
  if(!$('brandCategoryGrid') && !$('brandTopList') && !$('brandPieChart')) return;
  try{
    const d = await api('/api/brand-stats');
    // 业态卡片
    const grid = $('brandCategoryGrid');
    if(grid){
      grid.innerHTML = Object.entries(d.categories||{}).map(([cat,cs])=>{
        const color = CATEGORY_COLORS[cat]||'#666';
        const icon = CATEGORY_ICONS[cat]||'📦';
        const pct = d.pie_data?.find(p=>p.category===cat)?.percentage||0;
        return `<article class="metric-card glass-card" onclick="showCategoryCases('${esc(cat)}')" style="cursor:pointer;border-left:3px solid ${color}"><div class="metric-icon" style="background:${color}20;color:${color}">${icon}</div><div class="metric-label">${esc(cat)}</div><strong>${cs.note_count||0}</strong><div class="metric-sub">${cs.brand_count||0}个品牌 · ${pct}%</div></article>`;
      }).join('');
    }
    // 动态扇形图
    renderDynamicPieChart('brandPieChart', 'brandPieLegend', d.pie_data||[]);
    // 动态趋势图
    renderDynamicTrendChart('brandTrendChart', d.trend_data||[]);
    // 品牌TOP10
    const list = $('brandTopList');
    if(list){
      list.innerHTML = (d.top_brands||[]).map((b,i)=>{
        const color = CATEGORY_COLORS[b.category]||'#666';
        return `<div class="brand-row" onclick="filterByBrand('${esc(b.brand)}')" style="cursor:pointer"><span class="brand-rank" style="background:${color}">${i+1}</span><div class="brand-info"><div class="brand-name">${esc(b.brand)} <span style="color:var(--muted);font-size:12px">${esc(b.category)}</span></div><div class="brand-meta">${b.note_count}条笔记 · ${b.negative_count}条负面 · 互动${fmt(b.engagement)}</div></div><div class="brand-bar"><div style="width:${Math.min(100,b.note_count*10)}%;background:${color}"></div></div><span class="chev">›</span></div>`;
      }).join('') || '<div class="muted" style="text-align:center;padding:20px">暂无品牌数据</div>';
    }
  }catch(e){console.warn('品牌业态统计加载失败',e)}
}

function renderDynamicPieChart(chartId, legendId, data){
  const chart = $(chartId);
  const legend = $(legendId);
  if(!chart || !data.length) return;
  const total = data.reduce((s,d)=>s+(d.note_count||0),0);
  let cumulative = 0;
  const segments = data.filter(d=>d.note_count>0).map(d=>{
    const pct = total>0 ? (d.note_count/total)*100 : 0;
    const startAngle = cumulative*3.6;
    cumulative += pct;
    const endAngle = cumulative*3.6;
    const color = CATEGORY_COLORS[d.category]||'#666';
    return {category:d.category, count:d.note_count, pct, color, startAngle, endAngle};
  });
  // SVG扇形图
  const size = 240, cx=size/2, cy=size/2, r=100;
  let svg = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`;
  segments.forEach(seg=>{
    if(seg.pct >= 100){
      svg += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${seg.color}" class="pie-segment" data-category="${esc(seg.category)}" data-pct="${seg.pct}" data-count="${seg.count}" style="cursor:pointer"/>`;
    } else {
      const startRad = (seg.startAngle-90)*Math.PI/180;
      const endRad = (seg.endAngle-90)*Math.PI/180;
      const x1 = cx + r*Math.cos(startRad), y1 = cy + r*Math.sin(startRad);
      const x2 = cx + r*Math.cos(endRad), y2 = cy + r*Math.sin(endRad);
      const largeArc = seg.pct > 50 ? 1 : 0;
      svg += `<path d="M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z" fill="${seg.color}" class="pie-segment" data-category="${esc(seg.category)}" data-pct="${seg.pct.toFixed(1)}" data-count="${seg.count}" style="cursor:pointer;transition:opacity 0.2s"/>`;
    }
  });
  svg += `<circle cx="${cx}" cy="${cy}" r="55" fill="var(--bg)"/><text x="${cx}" y="${cy-5}" text-anchor="middle" style="font-size:24px;font-weight:700;fill:var(--text)">${total}</text><text x="${cx}" y="${cy+15}" text-anchor="middle" style="font-size:11px;fill:var(--muted)">总笔记</text>`;
  svg += '</svg>';
  chart.innerHTML = svg;
  // 点击事件
  chart.querySelectorAll('.pie-segment').forEach(seg=>{
    seg.onclick = ()=>{
      const cat = seg.dataset.category;
      const pct = seg.dataset.pct;
      const count = seg.dataset.count;
      toast(`${cat}：${count}条笔记，占比${pct}%`);
      showCategoryCases(cat);
    };
    seg.onmouseenter = ()=>{ seg.style.opacity = '0.7'; };
    seg.onmouseleave = ()=>{ seg.style.opacity = '1'; };
  });
  // 图例
  if(legend){
    legend.innerHTML = data.map(d=>{
      const color = CATEGORY_COLORS[d.category]||'#666';
      const pct = d.percentage||0;
      return `<div class="pie-legend-item" onclick="showCategoryCases('${esc(d.category)}')" style="cursor:pointer"><span class="legend-dot" style="background:${color}"></span><span class="legend-label">${esc(d.category)}</span><span class="legend-count">${d.note_count||0}</span><span class="legend-pct">${pct}%</span></div>`;
    }).join('');
  }
}

function renderDynamicTrendChart(chartId, data){
  const chart = $(chartId);
  if(!chart || !data.length) return;
  const maxVal = Math.max(...data.map(d=>Math.max(d.note_count||0,d.negative_count||0)),1);
  const w = chart.clientWidth || 700, h = 220, pad = {top:20,right:20,bottom:40,left:40};
  const chartW = w - pad.left - pad.right, chartH = h - pad.top - pad.bottom;
  const stepX = chartW / (data.length-1 || 1);
  const pointsAll = data.map((d,i)=>({x:pad.left+i*stepX, y:pad.top+chartH-(d.note_count||0)/maxVal*chartH, ...d}));
  const pointsNeg = data.map((d,i)=>({x:pad.left+i*stepX, y:pad.top+chartH-(d.negative_count||0)/maxVal*chartH, ...d}));
  const pathAll = pointsAll.map((p,i)=>`${i===0?'M':'L'} ${p.x} ${p.y}`).join(' ');
  const pathNeg = pointsNeg.map((p,i)=>`${i===0?'M':'L'} ${p.x} ${p.y}`).join(' ');
  const areaAll = pathAll + ` L ${pointsAll[pointsAll.length-1].x} ${pad.top+chartH} L ${pointsAll[0].x} ${pad.top+chartH} Z`;
  let svg = `<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">`;
  // 网格线
  for(let i=0;i<=4;i++){
    const y = pad.top + chartH*i/4;
    svg += `<line x1="${pad.left}" y1="${y}" x2="${w-pad.right}" y2="${y}" stroke="var(--border)" stroke-dasharray="3,3"/>`;
    svg += `<text x="${pad.left-8}" y="${y+4}" text-anchor="end" style="font-size:10px;fill:var(--muted)">${Math.round(maxVal*(1-i/4))}</text>`;
  }
  // 面积
  svg += `<path d="${areaAll}" fill="var(--primary)" opacity="0.1"/>`;
  // 线条
  svg += `<path d="${pathAll}" fill="none" stroke="var(--primary)" stroke-width="2"/>`;
  svg += `<path d="${pathNeg}" fill="none" stroke="var(--danger)" stroke-width="2"/>`;
  // 数据点（可点击）
  pointsAll.forEach((p,i)=>{
    svg += `<circle cx="${p.x}" cy="${p.y}" r="5" fill="var(--primary)" class="trend-point" data-date="${esc(p.date)}" data-count="${p.note_count}" data-negative="${p.negative_count}" style="cursor:pointer"/>`;
    svg += `<text x="${p.x}" y="${h-15}" text-anchor="middle" style="font-size:10px;fill:var(--muted)">${p.date.slice(5)}</text>`;
  });
  pointsNeg.forEach(p=>{
    svg += `<circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--danger)" class="trend-point" data-date="${esc(p.date)}" data-count="${p.note_count}" data-negative="${p.negative_count}" style="cursor:pointer"/>`;
  });
  svg += '</svg>';
  chart.innerHTML = svg;
  // 点击事件
  chart.querySelectorAll('.trend-point').forEach(pt=>{
    pt.onclick = ()=>{
      toast(`${pt.dataset.date}：${pt.dataset.count}条笔记，${pt.dataset.negative}条负面`);
    };
    pt.onmouseenter = ()=>{ pt.setAttribute('r','8'); };
    pt.onmouseleave = ()=>{ pt.setAttribute('r', pt.dataset.negative==='0'?'5':'4'); };
  });
}

function filterByCategory(category){
  navigateTo('monitor');
  setTimeout(()=>{
    const search = $('noteSearch');
    if(search){ search.value = category; search.dispatchEvent(new Event('input')); }
    toast(`已筛选业态：${category}`);
  }, 300);
}
function filterByBrand(brand){
  navigateTo('monitor');
  setTimeout(()=>{
    const search = $('noteSearch');
    if(search){ search.value = brand; search.dispatchEvent(new Event('input')); }
    toast(`已筛选品牌：${brand}`);
  }, 300);
}

// 导航到品牌业态页面时加载
const _origNavigate2 = navigateTo;
navigateTo = function(pageId){
  _origNavigate2(pageId);
  if(pageId==='brands') renderBrandStatsPage();
  if(pageId==='official') renderOfficialPage();
  if(pageId==='analysis'){
    // 重新渲染动态趋势图
    api('/api/stats').then(d=>{
      if(d.trend_data) renderDynamicTrendChart('trendChart', d.trend_data);
    }).catch(()=>{});
  }
};

/* ===== v5.4 官方动态模块 ===== */
let currentOfficialSource = 'all';
async function renderOfficialPage(){
  try{
    const d = await api('/api/official-info?source=' + currentOfficialSource + '&limit=30');
    const sourceList = $('officialSourceList');
    if(sourceList){
      const sources = [
        {key:'taikoo_official', name:'广州太古汇官网', icon:'🌐', color:'blue', desc:'官网活动、新闻、促销信息'},
        {key:'weibo_official', name:'官方微博', icon:'📱', color:'red', desc:'@太古汇TaiKooHui-广州 微博动态'},
        {key:'wechat_service', name:'微信服务号', icon:'💬', color:'green', desc:'TaikooHui-Guangzhou 服务号'},
        {key:'wechat_subscribe', name:'微信订阅号', icon:'📰', color:'amber', desc:'TaikooHui-GZ 订阅号'},
      ];
      sourceList.innerHTML = sources.map(s=>{
        const count = (d.items||[]).filter(i=>i.source===s.key).length;
        return `<div class="integration-item" onclick="filterOfficialSource('${s.key}')"><div class="integration-icon ${s.color}">${s.icon}</div><div class="integration-info"><h4>${s.name}</h4><p>${s.desc}</p></div><span class="integration-status">${count}条</span><span class="chev">›</span></div>`;
      }).join('');
    }
    const list = $('officialList');
    if(list){
      list.innerHTML = (d.items||[]).map(item=>{
        const sourceName = item.source_name || item.source;
        const sourceIcon = item.source==='taikoo_official'?'🌐':item.source==='weibo_official'?'📱':'💬';
        return `<div class="official-item" onclick="window.open('${item.url||'#'}','_blank')"><div class="official-source"><span class="official-icon">${sourceIcon}</span><span class="official-source-name">${esc(sourceName)}</span><span class="official-date">${esc(item.publish_date||item.collected_at||'')}</span></div><div class="official-title">${esc(item.title||'')}</div>${item.description?`<div class="official-desc">${esc(item.description.slice(0,150))}</div>`:''}</div>`;
      }).join('') || '<div class="muted" style="text-align:center;padding:40px">暂无官方动态，点击右上角"采集官方动态"按钮获取</div>';
    }
    document.querySelectorAll('#officialFilterTabs .filter-tab').forEach(tab=>{
      tab.onclick = ()=>{
        document.querySelectorAll('#officialFilterTabs .filter-tab').forEach(t=>t.classList.remove('active'));
        tab.classList.add('active');
        currentOfficialSource = tab.dataset.source;
        renderOfficialPage();
      };
    });
  }catch(e){console.warn('官方动态加载失败',e)}
}
function filterOfficialSource(source){
  currentOfficialSource = source;
  document.querySelectorAll('#officialFilterTabs .filter-tab').forEach(t=>{
    t.classList.toggle('active', t.dataset.source===source);
  });
  renderOfficialPage();
}
async function collectOfficialInfo(){
  try{
    toast('正在采集官方动态...');
    const d = await api('/api/official-info/collect',{method:'POST'});
    toast(d.message||'采集完成');
    renderOfficialPage();
  }catch(e){toast(e.message||'采集失败')}
}

/* ===== v5.4 品牌进场退场管理 ===== */
let brandManagerPage = 1;
let brandManagerKeyword = '';
let brandManagerCategory = '';
async function openBrandManager(){
  const mc = $('modalContent');
  mc.innerHTML = `<h3>场内品牌管理（进场/退场）</h3>
    <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">
      <input type="text" id="brandSearch" placeholder="搜索品牌名..." style="flex:1;min-width:150px;padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text)">
      <select id="brandCategoryFilter" style="padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text)"><option value="">全部业态</option></select>
      <button class="action primary" onclick="showAddBrandForm()">+ 品牌进场</button>
    </div>
    <div id="addBrandForm" style="display:none;padding:14px;background:var(--bg);border-radius:10px;margin-bottom:16px;border:1px solid var(--border)">
      <h4 style="margin:0 0 10px">新增品牌（进场）</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div><label style="font-size:12px;color:var(--muted)">品牌英文名 *</label><input type="text" id="newBrandEn" style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)"></div>
        <div><label style="font-size:12px;color:var(--muted)">品牌中文名</label><input type="text" id="newBrandCn" style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)"></div>
        <div><label style="font-size:12px;color:var(--muted)">业态分类 *</label><select id="newBrandCategory" style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)"><option value="">请选择</option><option>女装</option><option>男装</option><option>餐饮</option><option>珠宝钟表</option><option>美容护理</option><option>运动休闲</option><option>鞋包皮具</option><option>童装玩具</option><option>生活时尚</option></select></div>
        <div><label style="font-size:12px;color:var(--muted)">铺位号</label><input type="text" id="newBrandShop" placeholder="如 L101" style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)"></div>
        <div><label style="font-size:12px;color:var(--muted)">楼层</label><input type="text" id="newBrandFloor" placeholder="如 L1" style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)"></div>
      </div>
      <div style="margin-top:10px;display:flex;gap:8px"><button class="action primary" onclick="submitAddBrand()">确认进场</button><button class="action tertiary" onclick="document.getElementById('addBrandForm').style.display='none'">取消</button></div>
    </div>
    <div id="brandManagerList" style="max-height:400px;overflow-y:auto"></div>
    <div id="brandManagerPagination" style="margin-top:12px;text-align:center"></div>`;
  openModal();
  // 绑定搜索
  $('brandSearch').oninput = (e)=>{ brandManagerKeyword = e.target.value; brandManagerPage=1; loadBrandManagerList(); };
  $('brandCategoryFilter').onchange = (e)=>{ brandManagerCategory = e.target.value; brandManagerPage=1; loadBrandManagerList(); };
  loadBrandManagerList();
}
async function loadBrandManagerList(){
  try{
    let url = '/api/brands?page=' + brandManagerPage + '&per_page=20';
    if(brandManagerKeyword) url += '&keyword=' + encodeURIComponent(brandManagerKeyword);
    if(brandManagerCategory) url += '&category=' + encodeURIComponent(brandManagerCategory);
    const d = await api(url);
    // 填充业态筛选
    const catSelect = $('brandCategoryFilter');
    if(catSelect && d.categories){
      const current = catSelect.value;
      catSelect.innerHTML = '<option value="">全部业态</option>' + d.categories.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
      catSelect.value = current;
    }
    const list = $('brandManagerList');
    if(list){
      list.innerHTML = (d.brands||[]).map(b=>`
        <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-bottom:1px solid var(--border)">
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;font-size:14px">${esc(b.brand_cn||b.brand_en)} <span style="color:var(--muted);font-size:12px;font-weight:normal">${esc(b.brand_en)}</span></div>
            <div style="font-size:12px;color:var(--muted)">${esc(b.category||'')} · ${esc(b.shop||'')} · ${esc(b.floor||'')}</div>
          </div>
          <button class="action tertiary" style="padding:4px 10px;font-size:12px" onclick="editBrand('${esc(b.brand_en)}')">编辑</button>
          <button class="action" style="padding:4px 10px;font-size:12px;background:var(--danger);color:#fff" onclick="deleteBrand('${esc(b.brand_en)}','${esc(b.brand_cn||b.brand_en)}')">退场</button>
        </div>`).join('') || '<div style="text-align:center;padding:30px;color:var(--muted)">暂无品牌</div>';
    }
    // 分页
    const pag = $('brandManagerPagination');
    if(pag && d.total > 20){
      const totalPages = Math.ceil(d.total/20);
      pag.innerHTML = `<span style="color:var(--muted);font-size:12px">共${d.total}个品牌 · 第${brandManagerPage}/${totalPages}页</span>
        <button class="action tertiary" style="padding:4px 10px;font-size:12px;margin-left:10px" ${brandManagerPage<=1?'disabled':''} onclick="brandManagerPage--;loadBrandManagerList()">上一页</button>
        <button class="action tertiary" style="padding:4px 10px;font-size:12px" ${brandManagerPage>=totalPages?'disabled':''} onclick="brandManagerPage++;loadBrandManagerList()">下一页</button>`;
    }
    // 更新状态
    if($('brandManagerStatus')) $('brandManagerStatus').textContent = (d.total||0) + '个品牌';
  }catch(e){console.warn('品牌列表加载失败',e)}
}
function showAddBrandForm(){ $('addBrandForm').style.display='block'; }
async function submitAddBrand(){
  const brand_en = $('newBrandEn').value.trim();
  const brand_cn = $('newBrandCn').value.trim();
  const category = $('newBrandCategory').value;
  const shop = $('newBrandShop').value.trim();
  const floor = $('newBrandFloor').value.trim();
  if(!brand_en){ toast('品牌英文名不能为空'); return; }
  if(!category){ toast('请选择业态分类'); return; }
  try{
    const d = await api('/api/brands',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({brand_en,brand_cn,category,shop,floor})});
    toast(d.message||'品牌进场成功');
    $('addBrandForm').style.display='none';
    $('newBrandEn').value=''; $('newBrandCn').value=''; $('newBrandShop').value=''; $('newBrandFloor').value='';
    loadBrandManagerList();
  }catch(e){toast(e.message||'添加失败')}
}
async function deleteBrand(brand_en, brand_name){
  if(!confirm(`确认将「${brand_name}」标记为退场？此操作会从品牌目录中移除。`)) return;
  try{
    const d = await api('/api/brands/' + encodeURIComponent(brand_en),{method:'DELETE'});
    toast(d.message||'品牌已退场');
    loadBrandManagerList();
  }catch(e){toast(e.message||'删除失败')}
}
async function editBrand(brand_en){
  const new_name = prompt('修改品牌中文名（留空不修改）：','');
  if(new_name === null) return;
  const new_shop = prompt('修改铺位号（留空不修改）：','');
  if(new_shop === null) return;
  try{
    const body = {};
    if(new_name) body.brand_cn = new_name;
    if(new_shop) body.shop = new_shop;
    if(Object.keys(body).length === 0){ toast('未修改任何内容'); return; }
    const d = await api('/api/brands/' + encodeURIComponent(brand_en),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    toast(d.message||'修改成功');
    loadBrandManagerList();
  }catch(e){toast(e.message||'修改失败')}
}

/* ===== v5.4 全网舆情案例库（模块二） ===== */
let caseManagerPage = 1;
let caseManagerKeyword = '';
let caseManagerCategory = '';
let caseManagerLevel = '';
async function renderCasePage(){
  try{
    let url = '/api/cases?page=' + caseManagerPage + '&per_page=15';
    if(caseManagerKeyword) url += '&keyword=' + encodeURIComponent(caseManagerKeyword);
    if(caseManagerCategory) url += '&category=' + encodeURIComponent(caseManagerCategory);
    if(caseManagerLevel) url += '&level=' + encodeURIComponent(caseManagerLevel);
    const d = await api(url);
    // 填充分类筛选
    const catSelect = $('caseCategoryFilter');
    if(catSelect && d.categories){
      const current = catSelect.value;
      catSelect.innerHTML = '<option value="">全部分类</option>' + d.categories.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
      catSelect.value = current;
    }
    const list = $('caseList');
    if(list){
      list.innerHTML = (d.cases||[]).map(c=>`
        <div class="case-item" onclick="openCaseDetail('${esc(c.id)}')">
          <div class="case-header">
            <span class="case-id">${esc(c.id)}</span>
            <span class="case-level">${esc(c.level||'')}</span>
            <span class="case-category">${esc(c.category||'')}</span>
          </div>
          <div class="case-title">${esc(c.title||'')}</div>
          <div class="case-meta">${esc(c.location||'')} · ${esc(c.time||'')}</div>
          <div class="case-event">${esc((c.event||'').slice(0,100))}${(c.event||'').length>100?'...':''}</div>
          <div class="case-insight"><b>对太古汇启示：</b>${esc((c.taikoo_insight||'').slice(0,80))}${(c.taikoo_insight||'').length>80?'...':''}</div>
        </div>`).join('') || '<div style="text-align:center;padding:30px;color:var(--muted)">暂无案例</div>';
    }
    // 分页
    const pag = $('casePagination');
    if(pag && d.total > 15){
      const totalPages = Math.ceil(d.total/15);
      pag.innerHTML = `<span style="color:var(--muted);font-size:12px">共${d.total}个案例 · 第${caseManagerPage}/${totalPages}页</span>
        <button class="action tertiary" style="padding:4px 10px;font-size:12px;margin-left:10px" ${caseManagerPage<=1?'disabled':''} onclick="caseManagerPage--;renderCasePage()">上一页</button>
        <button class="action tertiary" style="padding:4px 10px;font-size:12px" ${caseManagerPage>=totalPages?'disabled':''} onclick="caseManagerPage++;renderCasePage()">下一页</button>`;
    }
    // 绑定筛选
    $('caseSearch').oninput = (e)=>{ caseManagerKeyword = e.target.value; caseManagerPage=1; renderCasePage(); };
    $('caseCategoryFilter').onchange = (e)=>{ caseManagerCategory = e.target.value; caseManagerPage=1; renderCasePage(); };
    $('caseLevelFilter').onchange = (e)=>{ caseManagerLevel = e.target.value; caseManagerPage=1; renderCasePage(); };
  }catch(e){console.warn('案例库加载失败',e)}
}
async function openCaseDetail(case_id){
  try{
    const d = await api('/api/cases/' + case_id);
    if(!d.case) return;
    const c = d.case;
    const mc = $('modalContent');
    mc.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
        <span class="case-id" style="font-size:14px">${esc(c.id)}</span>
        <span class="case-level" style="font-size:18px">${esc(c.level||'')}</span>
        <span class="case-category">${esc(c.category||'')}</span>
      </div>
      <h3 style="margin:0 0 8px">${esc(c.title||'')}</h3>
      <div style="color:var(--muted);font-size:13px;margin-bottom:16px">${esc(c.location||'')} · ${esc(c.time||'')}</div>
      <div class="case-detail-section"><h4>📌 事件经过</h4><p>${esc(c.event||'')}</p></div>
      <div class="case-detail-section"><h4>📈 传播路径</h4><p>${esc(c.spread_path||'')}</p></div>
      <div class="case-detail-section"><h4>💬 官方回应</h4><p>${esc(c.response||'')}</p></div>
      <div class="case-detail-section"><h4>📊 处理效果</h4><p>${esc(c.effect||'')}</p></div>
      <div class="case-detail-section" style="background:var(--bg);padding:12px;border-radius:8px;border-left:3px solid var(--primary)"><h4 style="color:var(--primary)">💡 对太古汇启示</h4><p>${esc(c.taikoo_insight||'')}</p></div>
      ${c.reply_formula?`<div class="case-detail-section"><h4>📝 回复公式</h4><p>${esc(c.reply_formula)}</p></div>`:''}
      ${c.taboo?`<div class="case-detail-section" style="color:var(--danger)"><h4>⚠️ 禁忌</h4><p>${esc(c.taboo)}</p></div>`:''}
      <div style="margin-top:16px;display:flex;gap:8px"><button class="action primary" onclick="closeModal()">关闭</button></div>`;
    openModal();
  }catch(e){toast(e.message||'加载失败')}
}
function showAddCaseForm(){ $('addCaseForm').style.display='block'; }
async function submitAddCase(){
  const title = $('newCaseTitle').value.trim();
  const location = $('newCaseLocation').value.trim();
  const category = $('newCaseCategory').value;
  const level = $('newCaseLevel').value;
  const event = $('newCaseEvent').value.trim();
  const response = $('newCaseResponse').value.trim();
  const taikoo_insight = $('newCaseInsight').value.trim();
  if(!title){ toast('案例标题不能为空'); return; }
  if(!category){ toast('请选择场景分类'); return; }
  try{
    const d = await api('/api/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,location,category,level,event,response,taikoo_insight})});
    toast(d.message||'案例收录成功');
    $('addCaseForm').style.display='none';
    $('newCaseTitle').value=''; $('newCaseLocation').value=''; $('newCaseEvent').value=''; $('newCaseResponse').value=''; $('newCaseInsight').value='';
    renderCasePage();
  }catch(e){toast(e.message||'收录失败')}
}

// 导航到案例库页面时加载
const _origNavigate3 = navigateTo;
navigateTo = function(pageId){
  _origNavigate3(pageId);
  if(pageId==='cases') renderCasePage();
};

/* ===== v5.4 舆情事件专报自动生成（交互优化） ===== */
async function generateSpecialReport(keyword, note_id){
  try{
    toast('正在生成舆情专报...');
    const body = {};
    if(keyword) body.keyword = keyword;
    if(note_id) body.note_id = note_id;
    const d = await api('/api/special-report/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(d.report){
      showSpecialReportModal(d.report);
    }
  }catch(e){toast(e.message||'生成失败')}
}

function showSpecialReportModal(report){
  const mc = $('modalContent');
  mc.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
      <span style="font-size:24px">${esc(report.level)}</span>
      <h3 style="margin:0">${esc(report.report_title)}</h3>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:16px">
      <div style="text-align:center;padding:10px;background:var(--bg);border-radius:8px"><div style="font-size:20px;font-weight:700">${report.current_volume}</div><div style="font-size:11px;color:var(--muted)">相关笔记</div></div>
      <div style="text-align:center;padding:10px;background:var(--bg);border-radius:8px"><div style="font-size:20px;font-weight:700;color:var(--danger)">${report.negative_count}</div><div style="font-size:11px;color:var(--muted)">负面笔记</div></div>
      <div style="text-align:center;padding:10px;background:var(--bg);border-radius:8px"><div style="font-size:20px;font-weight:700">${report.max_engagement}</div><div style="font-size:11px;color:var(--muted)">最高互动</div></div>
    </div>
    <div class="case-detail-section"><h4>📌 一、事件概述</h4><p><b>事件名称：</b>${esc(report.event_name)}</p><p><b>首发平台：</b>${esc(report.first_platform)} · <b>首发时间：</b>${esc(report.first_date)}</p><p><b>当前声量：</b>${report.current_volume}条 · <b>最高互动：</b>${report.max_engagement}</p></div>
    <div class="case-detail-section"><h4>📈 二、传播路径</h4><p>${esc(report.spread_path)}</p></div>
    <div class="case-detail-section" style="background:var(--bg);padding:12px;border-radius:8px;border-left:3px solid var(--primary)"><h4 style="color:var(--primary)">⭐ 三、案例对标（点击跳转案例库）</h4>${(report.matched_cases||[]).map(c=>`<div style="padding:8px 0;border-bottom:1px solid var(--border);cursor:pointer" onclick="closeModal();setTimeout(()=>{navigateTo('cases');setTimeout(()=>openCaseDetail('${esc(c.id)}'),300)},200)"><span class="case-id" style="font-size:11px">${esc(c.id)}</span> <span class="case-level">${esc(c.level)}</span> <span style="font-weight:600">${esc(c.title)}</span><div style="font-size:12px;color:var(--muted);margin-top:4px">${esc(c.insight||'')}</div></div>`).join('') || '<p style="color:var(--muted)">暂无匹配案例</p>'}</div>
    <div class="case-detail-section"><h4>👥 四、toC影响</h4><p><b>影响程度：</b>${esc(report.toc_impact)}</p><p>${esc(report.toc_detail)}</p></div>
    <div class="case-detail-section"><h4>🏢 五、toB影响</h4><p><b>影响程度：</b>${esc(report.tob_impact)}</p><p>${esc(report.tob_detail)}</p></div>
    <div class="case-detail-section"><h4>🎯 六、综合评级</h4><p style="font-size:18px;font-weight:700">${esc(report.comprehensive_level)}</p></div>
    <div class="case-detail-section"><h4>💡 七、应对策略（参考案例库启示）</h4><ol style="margin:0;padding-left:20px">${(report.strategies||[]).map(s=>`<li style="margin-bottom:6px">${esc(s)}</li>`).join('')}</ol></div>
    <div class="case-detail-section" style="color:var(--danger)"><h4>⚠️ 八、风险预警</h4><ul style="margin:0;padding-left:20px">${(report.risk_warnings||[]).map(w=>`<li style="margin-bottom:4px">${esc(w)}</li>`).join('')}</ul></div>
    <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap"><button class="action primary" onclick="closeModal()">关闭</button><button class="action tertiary" onclick="exportSpecialReport()">导出专报</button></div>`;
  openModal();
}

function exportSpecialReport(){
  toast('专报导出功能开发中...');
}

/* ===== v5.4 专报触发检查 ===== */
async function checkSpecialReportTrigger(){
  try{
    const d = await api('/api/special-report/check-trigger');
    if(d.triggered){
      console.log('专报触发条件:', d.triggers);
    }
    return d;
  }catch(e){return null}
}

/* ===== v5.4 品牌官网采集（交互优化） ===== */
async function collectBrandWebsites(){
  try{
    toast('正在采集场内品牌官网信息...');
    const d = await api('/api/official-info/collect',{method:'POST'});
    toast(d.message||'采集完成');
    renderOfficialPage();
  }catch(e){toast(e.message||'采集失败')}
}

// 页面加载时检查专报触发
setTimeout(checkSpecialReportTrigger, 10000);

/* ===== v5.5 各页面动态渲染函数 ===== */
async function renderBrandPage(){
  const el=$('brandPageContent');
  if(!el) return;
  el.innerHTML='<div class="muted" style="padding:40px;text-align:center">加载品牌业态数据中...</div>';
  try{
    const d = await api('/api/stats');
    const cats = d.categories || [];
    const total = d.stats?.total || 0;
    const neg = d.stats?.negative || 0;
    const html = `
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">BRAND MATRIX</span><h3>场内品牌及8大业态统计</h3><p>198个场内品牌 + 广州太古汇主体，点击业态卡片查看详情</p></div></div>
        <div class="brand-grid">
          ${cats.map(c=>`
            <div class="brand-card" onclick="toast('${esc(c.category)}：${c.count}条笔记，点击查看品牌列表')">
              <div class="brand-card-head"><h4>${esc(c.category||'其他')}</h4><span class="brand-count">${c.count}</span></div>
              <div class="brand-bar"><div class="brand-bar-fill" style="width:${Math.min(100,c.count/total*100*3)}%"></div></div>
              <div class="brand-meta">占比 ${(c.count/total*100).toFixed(1)}% · 负面 ${Math.round(c.count*neg/total)} 条</div>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">BRAND LIST</span><h3>场内品牌列表</h3><p>共198个品牌，支持进场/退场管理</p></div><button class="action secondary" onclick="openBrandManager()">品牌管理</button></div>
        <div class="muted" style="padding:20px">品牌详细列表请在「系统设置 → 场内品牌管理」中查看和编辑。</div>
      </div>`;
    el.innerHTML = html;
  }catch(e){ el.innerHTML='<div class="muted" style="padding:40px;text-align:center">品牌数据加载失败：'+esc(e.message)+'</div>' }
}

async function renderReportsPage(){
  const el=$('reportsPageContent');
  if(!el) return;
  try{
    const d = await api('/api/stats');
    const total = d.stats?.total || 0;
    const neg = d.stats?.negative || 0;
    const html = `
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">REPORT CENTER</span><h3>报告导出中心</h3><p>日报/周报/月报/年报，按客户汇报模板导出CSV表格</p></div></div>
        <div class="report-grid">
          <div class="report-card" onclick="exportReport('daily')">
            <div class="report-icon blue">日</div>
            <h4>舆情日报</h4>
            <p>当日数据概览、负面TOP3、分业态分布、应对动作</p>
            <span class="report-tag">每天9点自动生成</span>
          </div>
          <div class="report-card" onclick="exportReport('weekly')">
            <div class="report-icon green">周</div>
            <h4>舆情周报</h4>
            <p>一周趋势、重点事件演化、风险信号、案例对标</p>
            <span class="report-tag">每周一自动生成</span>
          </div>
          <div class="report-card" onclick="exportReport('monthly')">
            <div class="report-icon purple">月</div>
            <h4>舆情月报</h4>
            <p>月度趋势、业态结构变化、重点话题沉淀、改进建议</p>
            <span class="report-tag">每月1号自动生成</span>
          </div>
          <div class="report-card" onclick="exportReport('yearly')">
            <div class="report-icon amber">年</div>
            <h4>舆情年报</h4>
            <p>年度结构、重大事件复盘、品牌口碑变化、来年规划</p>
            <span class="report-tag">每年1月生成</span>
          </div>
        </div>
      </div>
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">REPORT TEMPLATE</span><h3>汇报模板说明</h3><p>严格按照太古汇客户汇报模板输出，不是网站内容一股脑导出</p></div></div>
        <div style="font-size:13px;line-height:1.8;color:var(--text)">
          <p><b>报告结构：</b>核心结论 → 数据概览（含环比） → 分业态舆情分布 → 重点负面帖清单 → 舆情归因 → 应对动作&下一步</p>
          <p><b>舆情等级：</b>🔴重大 / 🟡关注 / 🟢平稳，根据负面量、互动量、扩散速度自动判定</p>
          <p><b>推送配置：</b>在「系统设置 → 推送邮箱管理」中添加邮箱，报告生成后自动推送</p>
        </div>
      </div>`;
    el.innerHTML = html;
  }catch(e){ el.innerHTML='<div class="muted" style="padding:40px;text-align:center">报告数据加载失败</div>' }
}

async function renderAnalysisPage(){
  const el=$('analysisPageContent');
  if(!el) return;
  try{
    const [s, o] = await Promise.all([api('/api/stats'), api('/api/overview')]);
    const stats = s.stats || {};
    const trend = o.trend || [];
    const html = `
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">DATA ANALYSIS</span><h3>舆情数据分析</h3><p>趋势、情感、风险、互动多维度分析</p></div></div>
        <div class="analysis-stats">
          <div class="analysis-stat"><b>${stats.total||0}</b><span>总笔记</span></div>
          <div class="analysis-stat positive"><b>${stats.positive||0}</b><span>正面</span></div>
          <div class="analysis-stat neutral"><b>${stats.neutral||0}</b><span>中性</span></div>
          <div class="analysis-stat negative"><b>${stats.negative||0}</b><span>负面</span></div>
          <div class="analysis-stat risk"><b>${stats.high_risk||0}</b><span>高风险</span></div>
          <div class="analysis-stat"><b>${fmt(stats.total_engagements||0)}</b><span>总互动</span></div>
        </div>
      </div>
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">TREND</span><h3>舆情趋势</h3><p>点击柱状图查看当天详情</p></div></div>
        <div id="analysisTrend" class="trend-chart">${trend.length?trend.map(x=>`<div class="bar-group" onclick="openDayNotes('${esc(x.label)}')"><div class="bar all" style="height:${Math.max(3,(x.total/Math.max(...trend.map(t=>t.total),1))*100)}%"></div><div class="bar neg" style="height:${Math.max(2,(x.negative/Math.max(...trend.map(t=>t.total),1))*100)}%"></div><span class="bar-label">${esc(x.label)}</span></div>`).join(''):'<div class="muted">暂无趋势数据</div>'}</div>
      </div>
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">CATEGORY</span><h3>内容分类分布</h3><p>点击分类柱查看该类笔记</p></div></div>
        <div id="analysisCategory" class="category-chart">${(s.categories||[]).map(c=>`<div class="cat-col"><div class="cat-bar-wrap"><div class="cat-bar" style="height:${Math.max(4,c.count/Math.max(...(s.categories||[]).map(x=>x.count),1)*100)}%"></div></div><b>${c.count}</b><span>${esc(c.category||'其他')}</span></div>`).join('')}</div>
      </div>`;
    el.innerHTML = html;
  }catch(e){ el.innerHTML='<div class="muted" style="padding:40px;text-align:center">分析数据加载失败：'+esc(e.message)+'</div>' }
}

async function renderMonitorPage(){
  const el=$('monitorPageContent');
  if(!el) return;
  try{
    const st = await api('/api/status');
    const html = `
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">LIVE MONITOR</span><h3>实时舆情监测</h3><p>固定账号Cookie保护模式，8:05–23:05错峰自动采集、冷却1小时</p></div><button class="action primary" onclick="refresh()">一键更新</button></div>
        <div class="monitor-status">
          <div class="monitor-item"><span class="monitor-label">采集状态</span><b class="${st.ai_enabled?'ok':'warn'}">${st.ai_enabled?'运行中':'待启动'}</b></div>
          <div class="monitor-item"><span class="monitor-label">最后更新</span><b>${esc(st.last_collection?.finished_at||st.server_time||'—')}</b></div>
          <div class="monitor-item"><span class="monitor-label">自动采集</span><b>每日约9次·8:05–23:05错峰·冷却1h</b></div>
          <div class="monitor-item"><span class="monitor-label">数据源</span><b>固定账号Cookie保护（主） · rednote/CDP（备选）</b></div>
          <div class="monitor-item"><span class="monitor-label">CDP模式</span><b id="cdpStatusText2">${st.cdp_connected?'已连接':'未连接'}</b></div>
          <div class="monitor-item"><span class="monitor-label">系统版本</span><b>${esc(st.version||'5.8.3')}</b></div>
        </div>
      </div>
      <div class="panel glass-card">
        <div class="panel-head"><div><span class="eyebrow">COLLECTION PIPELINE</span><h3>采集链路</h3><p>搜索发现 → 详情补全 → 互动数据 → 评论采集 → 数据质量评分 → 主体校验 → 入库</p></div></div>
        <div class="pipeline">
          <div class="pipeline-step"><div class="pipeline-num">1</div><div class="pipeline-info"><h5>搜索发现</h5><p>固定账号关键词检索（rednote/CDP 备选）</p></div><div class="pipeline-status ok">✓</div></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><div class="pipeline-num">2</div><div class="pipeline-info"><h5>详情补全</h5><p>正文/发布时间/作者</p></div><div class="pipeline-status ok">✓</div></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><div class="pipeline-num">3</div><div class="pipeline-info"><h5>互动数据</h5><p>点赞/收藏/评论/分享</p></div><div class="pipeline-status ok">✓</div></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><div class="pipeline-num">4</div><div class="pipeline-info"><h5>评论采集</h5><p>cursor分页抓取</p></div><div class="pipeline-status ok">✓</div></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><div class="pipeline-num">5</div><div class="pipeline-info"><h5>质量评分</h5><p>完整度/主体校验</p></div><div class="pipeline-status ok">✓</div></div>
          <div class="pipeline-arrow">→</div>
          <div class="pipeline-step"><div class="pipeline-num">6</div><div class="pipeline-info"><h5>入库分析</h5><p>SQLite + AI情感分析</p></div><div class="pipeline-status ok">✓</div></div>
        </div>
      </div>`;
    el.innerHTML = html;
  }catch(e){ el.innerHTML='<div class="muted" style="padding:40px;text-align:center">监测状态加载失败</div>' }
}

/* ===== v5.5 诺米浮动AI助手 ===== */
let nomiChatOpen = false;
let nomiContext = { systemInfo: null, stats: null };

function toggleNomiChat(){
  nomiChatOpen = !nomiChatOpen;
  const modal = $('nomiChatModal');
  if(nomiChatOpen){
    modal.classList.add('open');
    setTimeout(()=>$('nomiInput')?.focus(),300);
    if(!nomiContext.systemInfo) loadNomiContext();
  } else {
    modal.classList.remove('open');
  }
}

async function loadNomiContext(){
  try{
    const [s, st] = await Promise.all([
      api('/api/stats').catch(()=>null),
      api('/api/status').catch(()=>null)
    ]);
    nomiContext.stats = s?.stats || null;
    nomiContext.systemInfo = st || null;
  }catch(e){ console.warn('诺米上下文加载失败', e) }
}

function nomiQuickAsk(q){
  $('nomiInput').value = q;
  sendNomiMsg();
}

function appendNomiMsg(text, isUser=false){
  const container = $('nomiMessages');
  const msg = document.createElement('div');
  msg.className = 'nomi-msg ' + (isUser ? 'nomi-msg-user' : 'nomi-msg-bot');
  msg.innerHTML = `<div class="nomi-msg-avatar">${isUser?'我':'N'}</div><div class="nomi-msg-bubble">${esc(text).replace(/\n/g,'<br>')}</div>`;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
  return msg;
}

function appendNomiTyping(){
  const container = $('nomiMessages');
  const msg = document.createElement('div');
  msg.className = 'nomi-msg nomi-msg-bot';
  msg.id = 'nomiTyping';
  msg.innerHTML = `<div class="nomi-msg-avatar">N</div><div class="nomi-msg-bubble nomi-msg-typing"><span></span><span></span><span></span></div>`;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function removeNomiTyping(){
  const t = $('nomiTyping');
  if(t) t.remove();
}

async function sendNomiMsg(){
  const input = $('nomiInput');
  const text = input.value.trim();
  if(!text) return;
  input.value = '';
  appendNomiMsg(text, true);
  appendNomiTyping();
  const btn = $('nomiSendBtn');
  btn.disabled = true;

  try{
    // 先检查是否是系统数据查询
    const dataAnswer = tryAnswerFromData(text);
    if(dataAnswer){
      removeNomiTyping();
      appendNomiMsg(dataAnswer, false);
      btn.disabled = false;
      return;
    }

    // 调用本地AI
    const systemPrompt = buildSystemPrompt();
    const d = await api('/api/ai/test',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text: systemPrompt + '\n\n用户问题：' + text})
    });
    removeNomiTyping();
    if(d.reply){
      appendNomiMsg(d.reply, false);
    } else if(d.message){
      appendNomiMsg(d.message, false);
    } else {
      appendNomiMsg('抱歉，我暂时无法回答这个问题。你可以试试问我舆情数据、风险预警、系统功能等。', false);
    }
  }catch(e){
    removeNomiTyping();
    appendNomiMsg('连接本地AI失败：' + e.message + '。请检查Ollama是否在运行。', false);
  }
  btn.disabled = false;
}

function tryAnswerFromData(q){
  const s = nomiContext.stats;
  if(!s) return null;
  const ql = q.toLowerCase();

  if(ql.includes('概况') || ql.includes('总') || ql.includes('多少条') || ql.includes('数据')){
    return `当前系统舆情概况：\n• 总相关笔记：${s.total} 条\n• 正面：${s.positive} 条\n• 中性：${s.neutral} 条\n• 负面：${s.negative} 条（占比 ${(s.negative/s.total*100).toFixed(1)}%）\n• 高风险：${s.high_risk} 条\n• 中风险：${s.medium_risk} 条\n• 总互动量：${fmt(s.total_engagements)}\n• 总评论数：${fmt(s.total_comments)}\n\n如需更详细的分析，可以点击左侧「舆情总览」查看。`;
  }
  if(ql.includes('风险') || ql.includes('预警') || ql.includes('高风险')){
    return `当前风险状况：\n• 高风险笔记：${s.high_risk} 条\n• 中风险笔记：${s.medium_risk} 条\n• 负面笔记：${s.negative} 条\n\n建议立即查看「风险预警」页面，重点关注高风险笔记的传播趋势和评论区情绪。如发现单条互动超过500或负面集中爆发，系统会自动触发专报。`;
  }
  if(ql.includes('日报') || ql.includes('导出') || ql.includes('报告')){
    return `日报/周报/月报/年报导出方法：\n1. 点击左侧「报告导出」模块\n2. 选择报告类型（日报/周报/月报/年报）\n3. 选择日期范围\n4. 点击导出，系统会生成CSV表格\n\n报告内容包括：数据概览、分业态分布、重点负面帖清单、舆情归因、应对动作建议，完全按照客户汇报模板输出。\n\n每天早上9点系统会自动生成前一天的日报，并可推送到配置的邮箱。`;
  }
  if(ql.includes('采集') || ql.includes('更新') || ql.includes('采集')||ql.includes('自动') || ql.includes('自动')){
    return `采集与更新配置：\n• 实时更新：点击顶部「一键更新」按钮立即采集\n• 自动采集：8:05–23:05整点错峰，每日约9次，每次后冷却1小时；手动一键每日3次\n• 数据源：固定账号Cookie保护模式为主，rednote/CDP 为备选采集\n• 采集内容：搜索发现→详情页→发布时间→互动数据→评论\n• 数据质量：每条笔记都有完整度评分和主体校验\n\n如需调整采集频率或关键词，可在「设置」中配置。CDP模式下可直接连接已登录的Edge浏览器。`;
  }
  if(ql.includes('品牌') || ql.includes('业态')){
    return `场内品牌监测：\n• 系统内置198个场内品牌+广州太古汇主体，共200个监测对象\n• 覆盖8大业态：零售、餐饮、商场服务、活动展览、环境设施、安全事件等\n• 每条笔记自动匹配品牌和业态分类\n• 品牌官网信息已接入，可辅助判断是否为场内品牌\n\n在「品牌业态」模块可以查看各品牌的笔记数量、情感分布和风险等级。`;
  }
  if(ql.includes('案例') || ql.includes('公关') || ql.includes('话术')){
    return `舆情案例库：\n系统内置全网重大舆情案例库，涵盖服务态度、活动安全、食品安全、内容审核、价格规则等场景。每个案例包含：事件→传播→回应→效果→对太古汇启示。\n\n当系统检测到重大舆情时，会自动匹配同类案例，参考处置方式和恢复周期。公关话术按业态分类，包括活动排队、停车会员、餐饮服务、专柜品牌等场景。\n\n在「案例库」模块可以浏览全部案例。`;
  }
  return null;
}

function buildSystemPrompt(){
  const s = nomiContext.stats;
  const info = nomiContext.systemInfo;
  let prompt = `你是广州太古汇舆情监测系统的智能助手"诺米"。你的职责是帮助用户理解舆情数据、操作系统功能、回答关于系统架构的问题。

系统架构：
- 前端：单页应用，左侧导航，模块点击跳转新页面
- 后端：Python Flask + SQLite
- 采集：固定账号Cookie保护（主）+ rednote/CDP（备选）
- AI：本地Ollama（qwen2.5-coder:7b），不可用时回退规则引擎
- 自动采集：8:05–23:05错峰约9次/天，冷却1小时；手动一键3次/天
- 报告：日报/周报/月报/年报，CSV导出，可邮件推送

核心模块：
1. 舆情总览 - 数据概览、趋势图、情感分布、风险分布
2. 笔记工作区 - 全部笔记、网页提及、历史复核、报告导出
3. 风险预警 - 高/中风险笔记，实时弹窗通知
4. 舆情事件 - 事件聚类、传播路径、影响评估
5. 热门话题 - 正面/负面话题，点击跳转小红书搜索
6. 品牌业态 - 198个场内品牌+8大业态统计
7. 案例库 - 全网舆情案例，公关话术
8. 专报中心 - 重大事件自动生成专报
9. 设置 - 公司域名、推送邮箱、品牌管理、运行代码

`;
  if(s){
    prompt += `当前实时数据：
- 总笔记：${s.total}，正面${s.positive}，中性${s.neutral}，负面${s.negative}
- 高风险${s.high_risk}，中风险${s.medium_risk}，低风险${s.low_risk}
- 总互动${fmt(s.total_engagements)}，总评论${fmt(s.total_comments)}

`;
  }
  prompt += `回答要求：
1. 简洁明了，重点突出
2. 涉及数据时使用具体数字
3. 给出可操作的建议
4. 不确定时如实说明，不编造
5. 语气友好专业，像一个贴心的助手`;
  return prompt;
}

// 诺米机器人入场动画
window.addEventListener('load',()=>{
  const nomi = $('nomiFloat');
  if(nomi){
    nomi.style.opacity = '0';
    nomi.style.transform = 'scale(0.5)';
    nomi.style.transition = 'all 0.5s cubic-bezier(0.34,1.56,0.64,1)';
    setTimeout(()=>{
      nomi.style.opacity = '1';
      nomi.style.transform = 'scale(1)';
    },800);
  }
});

/* ===== 导出报告菜单 ===== */
function toggleExportMenu(){
  const menu=document.getElementById('exportMenu');
  if(!menu)return;
  menu.classList.toggle('show');
  // 点击外部关闭
  if(menu.classList.contains('show')){
    setTimeout(()=>{
      document.addEventListener('click',function closeExport(e){
        if(!e.target.closest('.export-dropdown')){
          menu.classList.remove('show');
          document.removeEventListener('click',closeExport);
        }
      });
    },10);
  }
}

async function exportReportWithVerify(type,format){
  type=type||'daily';
  format=format||'xlsx';
  const menu=document.getElementById('exportMenu');
  if(menu)menu.classList.remove('show');
  toast('正在生成'+(type==='daily'?'日报':type==='weekly'?'周报':type==='monthly'?'月报':'年报')+'...');
  try{
    const url='/api/export/report?type='+type+'&format='+format;
    const resp=await fetch(url,{headers:{'Authorization':'Basic '+btoa('Zachary:ID082610')}});
    if(!resp.ok){
      const err=await resp.json().catch(()=>({error:'导出失败'}));
      toast(err.error||'导出失败');
      return;
    }
    const blob=await resp.blob();
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    const ts=localDateStr();
    a.download='太古汇舆情'+(type==='daily'?'日报':type==='weekly'?'周报':type==='monthly'?'月报':'年报')+'_'+ts+'.'+format;
    document.body.appendChild(a);a.click();document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
    toast('报告已下载');
  }catch(e){toast('导出失败：'+e.message)}
}


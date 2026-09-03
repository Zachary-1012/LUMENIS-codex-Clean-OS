// v5.3.2 - Local authenticated Xiaohongshu search bridge
// Cookie is read locally from XHS_COOKIES_JSON / XHS_COOKIE_HEADER or a private file.
// It is NEVER written to output JSON, logs, or source code.
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const PROFILE = process.env.XHS_PROFILE_DIR || path.join(os.homedir(), '.skills-router', 'rednote', 'instances', 'taikoo');
const COOKIE_FILE = process.env.XHS_COOKIE_FILE || path.join(process.cwd(), 'data', 'private', 'xhs_cookie_header.txt');

function args() {
  const a = process.argv.slice(2), r = { keyword:'', output:'', maxScroll:6 };
  for (let i=0;i<a.length;i++) {
    if (a[i]==='--keyword') r.keyword=a[++i] || '';
    else if (a[i]==='--output') r.output=a[++i] || '';
    else if (a[i]==='--max-scroll') r.maxScroll=Math.max(1, Math.min(20, Number(a[++i] || 6)));
  }
  return r;
}

function cookieHeader() {
  if (process.env.XHS_COOKIE_HEADER) return process.env.XHS_COOKIE_HEADER.trim();
  if (process.env.XHS_COOKIES_JSON) {
    try {
      const arr=JSON.parse(process.env.XHS_COOKIES_JSON);
      return arr.map(x=>`${x.name}=${x.value}`).join('; ');
    } catch { throw new Error('XHS_COOKIES_JSON 不是有效 JSON 数组'); }
  }
  if (fs.existsSync(COOKIE_FILE)) return fs.readFileSync(COOKIE_FILE,'utf8').trim();
  return '';
}

function parseCookieHeader(raw) {
  return raw.split(';').map(x=>x.trim()).filter(Boolean).map(pair=>{
    const i=pair.indexOf('=');
    if (i<=0) return null;
    return { name:pair.slice(0,i).trim(), value:pair.slice(i+1).trim(), domain:'.xiaohongshu.com', path:'/' };
  }).filter(Boolean);
}

function normalize(item) {
  const card=item.note_card || {}, user=card.user || {}, interact=card.interact_info || {}, cover=card.cover || {};
  const noteId=item.id || '';
  const token=item.xsec_token || '';
  const url=token ? `https://www.xiaohongshu.com/explore/${noteId}?xsec_token=${encodeURIComponent(token)}` : `https://www.xiaohongshu.com/explore/${noteId}`;
  const raw=card.time ?? card.display_time ?? item.time ?? item.create_time ?? '';
  let publishDate='';
  const s=String(raw);
  if (/^\d{10}$/.test(s)) publishDate=new Date(Number(s)*1000).toISOString().slice(0,10);
  else if (/^\d{13}$/.test(s)) publishDate=new Date(Number(s)).toISOString().slice(0,10);
  else if (/^\d{4}-\d{2}-\d{2}/.test(s)) publishDate=s.slice(0,10);
  else if (/^\d{1,2}-\d{1,2}/.test(s)) publishDate=`${new Date().getFullYear()}-${s.slice(0,5)}`;
  else if (s.includes('昨天')) { const d=new Date(); d.setDate(d.getDate()-1); publishDate=d.toISOString().slice(0,10); }
  else if (s.includes('前天')) { const d=new Date(); d.setDate(d.getDate()-2); publishDate=d.toISOString().slice(0,10); }
  else if (/(\d+)天前/.test(s)) { const d=new Date(); d.setDate(d.getDate()-Number(s.match(/(\d+)天前/)[1])); publishDate=d.toISOString().slice(0,10); }
  else if (s.includes('小时前') || s.includes('分钟前') || s.includes('刚刚')) publishDate=new Date().toISOString().slice(0,10);
  if (!publishDate && noteId.length>=8) {
    const ts=parseInt(noteId.slice(0,8),16);
    if (ts>1000000000 && ts<2000000000) publishDate=new Date(ts*1000).toISOString().slice(0,10);
  }
  return {
    note_id:noteId,
    title:card.display_title || card.title || '',
    content:'',
    url, cover:cover.url_default || cover.url_pre || cover.url || '',
    author_id:user.user_id || '', author_nickname:user.nickname || user.nick_name || '', author_avatar:user.avatar || '',
    likes:Number(interact.liked_count||0), comments:Number(interact.comment_count||0), collects:Number(interact.collected_count||0), shares:Number(interact.shared_count||0),
    note_type:card.type || item.model_type || 'normal', xsec_token:token, publish_date:publishDate,
    source_platform:'xiaohongshu'
  };
}

async function main() {
  const {keyword,output,maxScroll}=args();
  if (!keyword) throw new Error('--keyword 必填');
  const raw=cookieHeader();
  const cdpUrl=process.env.XHS_CDP_URL||'';
  let browser=null, context=null, page=null, isCdp=false;
  if (cdpUrl) {
    try {
      browser=await chromium.connectOverCDP(cdpUrl,{timeout:12000});
      context=browser.contexts()[0] || await browser.newContext();
      // 自愈：关闭此前异常残留的搜索结果 tab（不触碰 explore 等用户/保活页面）
      for (const op of context.pages()) { try { if (op.url().includes('search_result')) await op.close(); } catch {} }
      page=await context.newPage();
      isCdp=true;
    } catch(e) {
      process.stderr.write('[xhs-cookie-search] CDP connect fail, fallback headless: '+String(e&&e.message).slice(0,120)+'\n');
      try{ if(browser) await browser.close(); }catch{}
      browser=null; context=null; page=null; isCdp=false;
    }
  }
  if(!isCdp){
    context=await chromium.launchPersistentContext(PROFILE,{headless:true,args:['--disable-blink-features=AutomationControlled']});
    if (raw) await context.addCookies(parseCookieHeader(raw));
    page=context.pages()[0] || await context.newPage();
  }
  const notes=new Map(); let apiCalls=0; let apiErrorCode='', apiErrorMsg='';
  page.on('response', async response=>{
    try {
      const req=response.request();
      if (req.method().toLowerCase()!=='post' || response.status()!==200) return;
      if (!response.url().includes('/api/sns/web/v1/search/notes') && !response.url().includes('search/notes')) return;
      const ct=response.headers()['content-type']||''; if (!ct.includes('json')) return;
      const data=await response.json(); apiCalls++;
      // 捕获业务层错误码（如 300012 IP 风险），避免把接口报错当成“0 条正常”
      if (data && (data.error_code || data.code) && data.success===false) {
        apiErrorCode=String(data.error_code||data.code||''); apiErrorMsg=String(data.msg||data.message||'').slice(0,120);
      }
      for (const item of data?.data?.items || []) {
        if (item?.model_type==='note' && item.id) notes.set(item.id,normalize(item));
      }
    } catch {}
  });
  // 冷导航预热（对齐 Python CDP 采集实践）：直冷导航 search_result 易挂起，先稳落 explore 再进搜索页
  if (isCdp) {
    try { await page.goto('https://www.xiaohongshu.com/explore',{waitUntil:'domcontentloaded',timeout:20000}); await page.waitForTimeout(1500); }
    catch(e){ process.stderr.write('[xhs-cookie-search] explore warmup fail: '+String(e&&e.message).slice(0,100)+'\n'); }
  }
  const url=`https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(keyword)}&source=web_explore_feed`;
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
  await page.waitForTimeout(3500);
  for (let i=0;i<maxScroll;i++) { await page.evaluate(()=>window.scrollBy(0,900)); await page.waitForTimeout(1800); }
  try {
    const dom=await page.evaluate(()=>Array.from(document.querySelectorAll('a[href*="/explore/"]')).map(a=>({note_id:(a.href.match(/\/explore\/([A-Za-z0-9_-]+)/)||[])[1],url:a.href})).filter(x=>x.note_id));
    for (const x of dom) if (!notes.has(x.note_id)) notes.set(x.note_id,{note_id:x.note_id,title:'',content:'',url:x.url,cover:'',author_id:'',author_nickname:'',author_avatar:'',likes:0,comments:0,collects:0,shares:0,note_type:'normal',xsec_token:'',publish_date:'',source_platform:'xiaohongshu'});
  } catch {}
  // ===== 六态状态机：SUCCESS / EMPTY / BLOCKED / AUTH_FAILED / CAPTCHA / NETWORK_ERROR =====
  // 关键：被拦截绝不输出成“0 条正常”，items 语义由 state 决定
  let blockedReason='', pageHint='', state='SUCCESS';
  try {
    const fu=page.url(); let pt='';
    try { pt=await page.title(); } catch {}
    pageHint=`${pt}|${fu}`.slice(0,200);
    const isCaptcha=/redcaptcha|captcha\.html|verify_(?:slide|human)|人机验证|验证码/i.test(fu+' '+pt);
    const isIpRisk=/website-login\/error|安全限制|error_code=300012|IP存在风险|300012/i.test(fu+' '+pt) || apiErrorCode==='300012';
    const isLogin=/website-login|\/login/.test(fu) && !/search_result/.test(fu);
    if (isCaptcha) { state='CAPTCHA'; blockedReason='CAPTCHA'; }
    else if (isIpRisk) { state='BLOCKED'; blockedReason='IP_RISK_OR_CAPTCHA'; }
    else if (isLogin) { state='AUTH_FAILED'; blockedReason='LOGIN_REQUIRED'; }
    else if (apiErrorCode) { state='BLOCKED'; blockedReason='API_'+apiErrorCode; }
    else if (apiCalls===0 && notes.size===0) { state='NETWORK_ERROR'; blockedReason='EMPTY_NO_API'; }
    else if (notes.size===0) { state='EMPTY'; blockedReason=''; }  // 接口正常返回，确实 0 条
    else { state='SUCCESS'; }
  } catch {}
  // CDP 模式只关闭本任务打开的标签页并断开调试连接，绝不关闭常驻浏览器；独立模式才关闭整个 context
  try { await page.close(); } catch {}
  if (isCdp) { try { await browser.disconnect(); } catch {} }
  else { try { await context.close(); } catch {} }
  const result={keyword,fetched_at:new Date().toISOString(),state,total:notes.size,api_calls:apiCalls,
    error_code:apiErrorCode,error_msg:apiErrorMsg,
    blocked_reason:blockedReason, page_hint:pageHint,
    notes:[...notes.values()]};
  if (output) { fs.mkdirSync(path.dirname(output),{recursive:true}); fs.writeFileSync(output,JSON.stringify(result,null,2),'utf8'); }
  process.stdout.write(JSON.stringify(result));
  // connectOverCDP 可能残留连接句柄使事件循环不空，写完即干净退出（catch 路径已 process.exit(1)）
  process.exit(0);
}
main().catch(e=>{ // 导航/网络层失败：结构化输出 NETWORK_ERROR，不抛裸异常
  const result={keyword:'',fetched_at:new Date().toISOString(),state:'NETWORK_ERROR',total:0,api_calls:0,
    error_code:'NAV_FAILED',error_msg:(e&&e.message||'').slice(0,160),blocked_reason:'NETWORK_ERROR',page_hint:'',notes:[]};
  if (typeof output==='string'&&output){ try{fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(result,null,2),'utf8');}catch{} }
  console.error('[xhs-cookie-search]',e.message); process.exit(1); });

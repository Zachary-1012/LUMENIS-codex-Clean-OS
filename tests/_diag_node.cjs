const { chromium } = require('playwright');
const T0 = Date.now();
const log = m => process.stderr.write(`[+${((Date.now()-T0)/1000).toFixed(1)}s] ${m}\n`);
(async () => {
  log('start');
  const BASE = 'http://127.0.0.1:9222';
  let r = await fetch(BASE + '/json/list'); let list = await r.json();
  log('list: ' + list.map(x => x.type + ':' + x.url.slice(0, 30)).join(' | '));
  // 新开空白保底，再关闭所有重页面与 service worker（sw 拦截同域导航，卡死时会让 goto 挂起）
  await fetch(BASE + '/json/new?about:blank', { method: 'PUT' }).catch(()=>{});
  await new Promise(r=>setTimeout(r,600));
  r = await fetch(BASE + '/json/list'); list = await r.json();
  for (const x of list) {
    const keep = x.type==='page' && x.url.includes('about:blank');
    if (!keep) { await fetch(BASE + '/json/close/' + x.id).catch(e=>log('close err '+e.message)); log('closed target ['+x.type+'] ' + x.url.slice(0,30)); }
  }
  await new Promise(r=>setTimeout(r,600));
  log('reset done');
  const b = await chromium.connectOverCDP(BASE, { timeout: 15000 }); log('CONNECTED');
  const ctx = b.contexts()[0];
  // 关键：关闭所有既有页（可能僵死），新建干净工作页
  for (const old of ctx.pages()) { try { await old.close(); log('closed old page'); } catch(e){log('close old err '+e.message);} }
  const pg = await ctx.newPage(); log('NEW work page created, pages=' + ctx.pages().length);
  await pg.goto('about:blank',{timeout:10000}).catch(e=>log('blank err '+e.message)); log('goto about:blank ok');
  const url = 'https://www.xiaohongshu.com/search_result?keyword=' + encodeURIComponent('广州太古汇十五周年') + '&source=web_explore_feed';
  await pg.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(e=>log('GOTO ERR: '+e.message));
  log('after xhs goto, readyState=' + await pg.evaluate(()=>document.readyState).catch(e=>'eval err '+e.message));
  await pg.waitForTimeout(3500);
  let n = await pg.evaluate(()=>document.querySelectorAll('a[href*="/explore/"]').length).catch(()=>-1);
  log('explore initial=' + n);
  for (let i=0;i<3;i++){ await pg.evaluate(()=>window.scrollBy(0,1000)).catch(()=>{}); await pg.waitForTimeout(2500); }
  n = await pg.evaluate(()=>document.querySelectorAll('a[href*="/explore/"]').length).catch(()=>-1);
  log('explore after scroll=' + n);
  const head = await pg.evaluate(()=>document.body.innerText.slice(0,150)).catch(e=>'err '+e.message);
  log('body: ' + JSON.stringify(head));
  await pg.goto('about:blank',{timeout:5000}).catch(()=>{});
  await b.close(); log('CLOSED OK');
  process.exit(0);
})().catch(e=>{ process.stderr.write('FATAL: '+e.message+'\n'); process.exit(1); });

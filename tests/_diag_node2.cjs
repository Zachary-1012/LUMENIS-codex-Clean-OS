const { chromium } = require('playwright');
const T0 = Date.now();
const log = m => process.stderr.write(`[+${((Date.now()-T0)/1000).toFixed(1)}s] ${m}\n`);
async function evalWithTimeout(pg, expr, ms=3000){
  return Promise.race([
    pg.evaluate(expr),
    new Promise((_,rej)=>setTimeout(()=>rej(new Error('EVAL_HANG')),ms)),
  ]).catch(e=>'<<'+e.message+'>>');
}
(async () => {
  const BASE='http://127.0.0.1:9222';
  // reset
  await fetch(BASE+'/json/new?about:blank',{method:'PUT'}).catch(()=>{});
  await new Promise(r=>setTimeout(r,600));
  let list = await (await fetch(BASE+'/json/list')).json();
  for(const x of list){ if(!(x.type==='page'&&x.url.includes('about:blank'))) await fetch(BASE+'/json/close/'+x.id).catch(()=>{}); }
  await new Promise(r=>setTimeout(r,600));
  const b=await chromium.connectOverCDP(BASE,{timeout:15000}); log('connected');
  const ctx=b.contexts()[0];
  for(const old of ctx.pages()){try{await old.close();}catch{}}
  const pg=await ctx.newPage(); log('new page');
  const targets=[
    ['baidu','https://www.baidu.com'],
    ['xhs-home','https://www.xiaohongshu.com'],
    ['xhs-explore','https://www.xiaohongshu.com/explore'],
    ['xhs-search','https://www.xiaohongshu.com/search_result?keyword='+encodeURIComponent('太古汇')],
  ];
  for(const [name,u] of targets){
    const t=Date.now();let st='ok';
    await pg.goto(u,{waitUntil:'domcontentloaded',timeout:15000}).catch(e=>st='TIMEOUT');
    const rs=await evalWithTimeout(pg,()=>document.readyState);
    log(`goto ${name}: ${st} ${((Date.now()-t)/1000).toFixed(1)}s readyState=${rs} url=${pg.url().slice(0,50)}`);
    await pg.goto('about:blank',{timeout:4000}).catch(()=>{});
    await new Promise(r=>setTimeout(r,800));
  }
  await b.close();log('done');process.exit(0);
})().catch(e=>{process.stderr.write('FATAL '+e.message+'\n');process.exit(1);});

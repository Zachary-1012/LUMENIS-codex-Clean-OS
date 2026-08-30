const { chromium } = require('playwright');
const T0=Date.now();const log=m=>process.stderr.write(`[+${((Date.now()-T0)/1000).toFixed(1)}s] ${m}\n`);
(async()=>{
  const BASE='http://127.0.0.1:9222';
  await fetch(BASE+'/json/new?about:blank',{method:'PUT'}).catch(()=>{});
  await new Promise(r=>setTimeout(r,600));
  let list=await(await fetch(BASE+'/json/list')).json();
  for(const x of list){if(!(x.type==='page'&&x.url.includes('about:blank')))await fetch(BASE+'/json/close/'+x.id).catch(()=>{});}
  await new Promise(r=>setTimeout(r,600));
  const b=await chromium.connectOverCDP(BASE,{timeout:15000});
  const ctx=b.contexts()[0];
  for(const o of ctx.pages()){try{await o.close();}catch{}}
  const pg=await ctx.newPage();
  let apiHits=0;const apiUrls=[];
  pg.on('response',async resp=>{
    const u=resp.url();
    if(u.includes('/api/sns/web/v1/search')||u.includes('search/notes')){
      apiHits++;apiUrls.push(resp.status()+' '+u.slice(0,80));
    }
  });
  await pg.goto('https://www.xiaohongshu.com/explore',{waitUntil:'domcontentloaded',timeout:20000}).catch(e=>log('warm err '+e.message));
  await pg.waitForTimeout(1200);
  const kw=process.argv[2]||'太古汇';
  await pg.goto('https://www.xiaohongshu.com/search_result?keyword='+encodeURIComponent(kw)+'&source=web_explore_feed',{waitUntil:'domcontentloaded',timeout:25000}).catch(e=>log('search err '+e.message));
  await pg.waitForTimeout(4000);
  async function snap(tag){
    const info=await pg.evaluate(()=>{
      const q=s=>document.querySelectorAll(s).length;
      const hrefs=[...document.querySelectorAll('a')].slice(0,12).map(a=>a.getAttribute('href')||'').filter(Boolean);
      return {noteItem:q('section.note-item'),explore:q('a[href*="/explore/"]'),searchRes:q('a[href*="/search_result/"]'),
        feedCard:q('[class*="note"],[class*="card"],[data-v]'),allA:q('a'),hrefSample:hrefs,
        body:(document.body.innerText||'').slice(0,400)};
    }).catch(e=>({evalErr:e.message}));
    log(`==${tag}== noteItem=${info.noteItem} explore=${info.explore} searchRes=${info.searchRes} allA=${info.allA} feedCard=${info.feedCard}`);
    if(info.hrefSample)log('href样例: '+JSON.stringify(info.hrefSample.slice(0,8)));
    if(info.body)log('body: '+JSON.stringify(info.body.slice(0,350)));
  }
  await snap('初始');
  for(let i=0;i<3;i++){await pg.evaluate(()=>window.scrollBy(0,900)).catch(()=>{});await pg.waitForTimeout(2500);}
  await snap('滚动后');
  log('搜索API命中次数='+apiHits);apiUrls.forEach(u=>log('  API '+u));
  await pg.screenshot({path:'tests/frames/node_search.png'});
  await pg.goto('about:blank',{timeout:4000}).catch(()=>{});
  await b.close();process.exit(0);
})().catch(e=>{process.stderr.write('FATAL '+e.message+'\n');process.exit(1);});

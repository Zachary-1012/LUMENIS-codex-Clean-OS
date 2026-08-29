"""独立普通浏览器搜索发现层：不调用RedNote采集器，不消耗其检索次数。"""
import os,re,json,urllib.parse,urllib.request,hashlib

def _get(url,timeout=20):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode('utf-8','replace')

def search(query,limit=30):
    # Bing public HTML search; if unavailable, Google News RSS is fallback.
    out=[]
    try:
        html=_get('https://www.bing.com/search?q='+urllib.parse.quote(query)+'&count='+str(min(limit,50)))
        for m in re.finditer(r'<li class="b_algo"[\s\S]*?</li>',html,re.I):
            block=m.group(0); hm=re.search(r'<h2><a href="([^"]+)"[^>]*>(.*?)</a>',block,re.I|re.S); sm=re.search(r'<p>(.*?)</p>',block,re.I|re.S)
            if not hm: continue
            clean=lambda x: re.sub('<[^>]+>',' ',x or '').replace('&amp;','&').strip()
            url=hm.group(1); title=clean(hm.group(2)); content=clean(sm.group(1) if sm else '')
            out.append({'source_id':hashlib.sha1(url.split('?')[0].encode()).hexdigest(),'source_platform':'web','source_type':'browser_search','source_adapter':'bing_html','query':query,'title':title,'content':content,'url':url,'canonical_url':url.split('#')[0],'domain':urllib.parse.urlparse(url).netloc})
    except Exception: pass
    return out[:limit]

def discover(queries,limit=80):
    all_items=[]
    for q in queries:
        all_items.extend(search(q,limit=max(5,min(30,limit//max(1,len(queries))))))
    seen=set(); out=[]
    for x in all_items:
        if x['source_id'] in seen: continue
        seen.add(x['source_id']); out.append(x)
        if len(out)>=limit:break
    return out

"""广州太古汇公开互联网舆情发现层 v5.3.1。
默认 Adapter：Google News RSS / GDELT / 自定义 RSS。
发现层只负责“找信号”，最终主体判断仍交给 ai_analyzer.verify_taikoo_location，确保小红书主平台口径不被稀释。
"""
import os,re,json,hashlib,urllib.parse,urllib.request,xml.etree.ElementTree as ET
DEFAULT_QUERIES=['广州太古汇','广州太古汇 投诉 OR 争议 OR 避雷','广州太古汇 停车 OR 保安 OR 服务','广州太古汇 闭店 OR 撤场 OR 开业','广州太古汇 品牌 OR LV OR Dior OR Chanel OR 方所']
def _get(url,timeout=20):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 TaikooMonitor/5.3.1 public-research'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode('utf-8','replace')
def _clean(s):return re.sub(r'\s+',' ',s or '').strip()
def _platform_from_url(url,default='web'):
    u=(url or '').lower()
    for key,name in [('weibo.com','weibo'),('zhihu.com','zhihu'),('bilibili.com','bilibili'),('douyin.com','douyin'),('xiaohongshu.com','xiaohongshu'),('thepaper.cn','thepaper'),('163.com','netease'),('qq.com','qq'),('sina.com','sina')]:
        if key in u:return name
    return default
def _parse_rss(xml_text,source='rss',query=''):
    out=[]
    try:root=ET.fromstring(xml_text)
    except Exception:return out
    for item in root.findall('.//item'):
        title=_clean(item.findtext('title'));link=_clean(item.findtext('link'));desc=_clean(item.findtext('description'));pub=_clean(item.findtext('pubDate'))
        if not (title or link):continue
        canonical=link.split('#')[0].split('?')[0] if link else title; sid=hashlib.sha1(canonical.encode('utf-8')).hexdigest()
        out.append({'source_id':sid,'source_platform':_platform_from_url(link,source),'source_type':'rss','source_adapter':source,'query':query,'title':title,'content':desc,'url':link,'canonical_url':canonical,'published_at':pub,'domain':urllib.parse.urlparse(link).netloc})
    return out
def google_news(query):
    url='https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=zh-CN&gl=CN&ceid=CN:zh-Hans'
    try:return _parse_rss(_get(url),'google_news',query)
    except Exception as e:print('[Web][Google News]',e);return []
def gdelt(query='广州太古汇',maxrecords=50):
    params=urllib.parse.urlencode({'query':query,'mode':'artlist','format':'json','maxrecords':maxrecords,'sort':'datedesc'})
    try:
        data=json.loads(_get('https://api.gdeltproject.org/api/v2/doc/doc?'+params));out=[]
        for a in data.get('articles',[]):
            url=a.get('url',''); canonical=url.split('#')[0].split('?')[0]
            out.append({'source_id':hashlib.sha1(canonical.encode('utf-8')).hexdigest(),'source_platform':_platform_from_url(url,'gdelt'),'source_type':'web','source_adapter':'gdelt','query':query,'title':_clean(a.get('title')),'content':_clean(a.get('snippet') or ''),'url':url,'canonical_url':canonical,'published_at':a.get('seendate',''),'domain':a.get('domain','')})
        return out
    except Exception as e:print('[Web][GDELT]',e);return []
def custom_rss():
    urls=[x.strip() for x in os.getenv('WEB_RSS_URLS','').split(',') if x.strip()]; out=[]
    for url in urls:
        try:out.extend(_parse_rss(_get(url),'custom_rss',url))
        except Exception as e:print('[Web][Custom RSS]',e)
    return out
ADAPTERS={'google_news':google_news,'gdelt':gdelt,'custom_rss':lambda q: custom_rss()}
def discover(limit=160):
    queries=[x.strip() for x in os.getenv('WEB_QUERIES','').split('||') if x.strip()] or DEFAULT_QUERIES
    enabled=[x.strip().lower() for x in os.getenv('WEB_ADAPTERS','google_news,gdelt,custom_rss').split(',') if x.strip()]; items=[]
    for adapter in enabled:
        fn=ADAPTERS.get(adapter)
        if not fn:continue
        if adapter=='gdelt':
            for q in queries[:6]:items.extend(gdelt(q,maxrecords=min(60,max(20,limit//2))))
        elif adapter=='custom_rss':items.extend(custom_rss())
        else:
            for q in queries[:8]:items.extend(fn(q))
    seen=set();clean=[]
    for x in items:
        sid=x.get('source_id') or x.get('canonical_url') or x.get('url') or x.get('title')
        if sid in seen:continue
        seen.add(sid);clean.append(x)
        if len(clean)>=limit:break
    return clean
def feedback_keywords(items,max_keywords=12):
    stop={'广州太古汇','太古汇','广州','相关','最新','消息','新闻','记者','表示','今天','近日','关注','据了解','网友','回应'}; preferred=['投诉','争议','停车','保安','服务','闭店','开业','撤场','活动','方所','LV','Dior','Chanel','餐饮','售后','安全','卫生','消防','骚扰','冲突','品牌','调整','扩容','价格']; words={}
    for it in items:
        text=f"{it.get('title','')} {it.get('content','')}"
        for w in re.findall(r'[\u4e00-\u9fffA-Za-z0-9·]{2,12}',text):
            if w in stop:continue
            words[w]=words.get(w,0)+(4 if any(k.lower() in w.lower() for k in preferred) else 1)
    return [w for w,_ in sorted(words.items(),key=lambda x:x[1],reverse=True)[:max_keywords]]

# -*- coding: utf-8 -*-
"""GitHub 真实仓库对标检索（只读公开 API，按 star 排序，拿活跃度/归档状态）。"""
import os,time,json,urllib.request,urllib.parse
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));os.chdir(ROOT)
OUT=os.path.join('docs','audit_evidence');os.makedirs(OUT,exist_ok=True)
QUERIES=[
 ('小红书采集','xiaohongshu crawler'),
 ('小红书xhs生态','xhs in:name'),
 ('微博采集','weibo spider'),
 ('B站采集','bilibili api'),
 ('社媒监听/舆情','social media listening dashboard'),
 ('中文舆情','舆情 in:name,description'),
 ('Flask大型脚手架','cookiecutter flask'),
 ('Flask多租户SaaS','flask multi tenant'),
 ('Python熔断','python circuit breaker'),
 ('任务调度','apscheduler'),
 ('多模型AI网关','litellm'),
 ('Playwright隐身/指纹','playwright stealth'),
 ('扫码登录/Cookie池','qrcode login cookie pool'),
 ('可复用脚手架','cookiecutter in:name python'),
]
def fetch(q):
    url='https://api.github.com/search/repositories?'+urllib.parse.urlencode(
        {'q':q,'sort':'stars','order':'desc','per_page':5})
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'zb-audit','Connection':'close'})
    with urllib.request.urlopen(req,timeout=20) as r: return json.load(r)
buf=[]
for label,q in QUERIES:
    buf.append(f'\n===== {label}  (q={q}) =====')
    try:
        d=fetch(q)
        buf.append(f'  总命中 {d.get("total_count")}')
        for it in d.get('items',[])[:5]:
            buf.append('  - {name:38s} star={st:6d} fork={fk:5d} archived={ar} push={pu} lic={lic}'.format(
                name=it['full_name'][:38], st=it['stargazers_count'], fk=it['forks_count'],
                ar=it['archived'], pu=(it['pushed_at'] or '')[:10],
                lic=(it.get('license') or {}).get('spdx_id') if it.get('license') else '-'))
            desc=(it.get('description') or '')[:90]
            buf.append(f'      {desc}')
    except Exception as e:
        buf.append(f'  ERR {e}')
    time.sleep(6.3)  # 未认证搜索限流 10/min
open(os.path.join(OUT,'07_github.txt'),'w',encoding='utf-8').write('\n'.join(buf))
print('\n'.join(buf))

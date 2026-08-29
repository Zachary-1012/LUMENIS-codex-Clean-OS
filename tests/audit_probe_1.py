# -*- coding: utf-8 -*-
"""只读审计探查 1：架构/蓝图/路由/启动/产品线。不 import app，纯静态扫描。"""
import os, re, glob, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'audit_evidence'); os.makedirs(OUT, exist_ok=True)
buf=[]
def p(s=''): buf.append(str(s))

p('# 取证1 架构 / 蓝图 / 路由 / 启动')
# ---- app.py 蓝图注册 ----
app_py=os.path.join(ROOT,'app.py'); src=open(app_py,encoding='utf-8',errors='ignore').read(); lines=src.split('\n')
p('\n## app.py 中 register_blueprint / Blueprint import')
for i,l in enumerate(lines,1):
    if 'register_blueprint' in l or re.search(r'import\s+\w+_?(module|api|blueprint|bp)', l) or ('Blueprint' in l and 'import' not in l and '=' in l):
        p(f'{i}: {l.strip()[:130]}')

# ---- 各蓝图文件 Blueprint 定义 ----
p('\n## 各文件 Blueprint() 定义')
for f in glob.glob(os.path.join(ROOT,'*.py')):
    t=open(f,encoding='utf-8',errors='ignore').read()
    for m in re.finditer(r'Blueprint\(\s*[\'"]([^\'"]+)[\'"]', t):
        ln=t[:m.start()].count('\n')+1
        p(f'{os.path.basename(f)}:{ln}  name={m.group(1)}')

# ---- 路由统计：app.py ----
routes_app=re.findall(r'@app\.route\(\s*[\'"]([^\'"]+)[\'"]\s*(?:,\s*methods=\[([^\]]*)\])?', src)
p(f'\n## app.py @app.route 数量: {len(routes_app)}')
# 各蓝图文件路由数
p('\n## 各蓝图/模块文件路由数 (xxx.route)')
for f in sorted(glob.glob(os.path.join(ROOT,'*.py'))):
    t=open(f,encoding='utf-8',errors='ignore').read()
    n=len(re.findall(r'\.route\(', t))
    if n: p(f'  {os.path.basename(f):38s} {n}')

# ---- 启动方式 ----
p('\n## 启动 / WSGI / debug / reloader / waitress')
for i,l in enumerate(lines,1):
    if re.search(r'app\.run\(|waitress|serve\(|use_reloader|debug\s*=|threaded\s*=|__main__', l):
        p(f'app.py:{i}: {l.strip()[:120]}')
for f in ['run_production.py']:
    fp=os.path.join(ROOT,f)
    if os.path.exists(fp):
        p(f'--- {f} ---')
        for i,l in enumerate(open(fp,encoding='utf-8',errors='ignore').read().split('\n'),1):
            if re.search(r'serve|waitress|host|port|app',l,re.I) and l.strip(): p(f'{i}: {l.strip()[:120]}')

# ---- 调度器启动 ----
p('\n## APScheduler / 后台线程 start 点 (app.py)')
for i,l in enumerate(lines,1):
    if re.search(r'\.start\(\)|BackgroundScheduler|Thread\(|start_monitoring|scheduler\.add_job', l):
        p(f'{i}: {l.strip()[:120]}')

# ---- 产品线/密钥门 ----
p('\n## 产品线隔离 / ZBMP / 密钥门 证据')
hit=False
for f in glob.glob(os.path.join(ROOT,'**','*.py'),recursive=True):
    if '.venv' in f or 'node_modules' in f: continue
    t=open(f,encoding='utf-8',errors='ignore').read()
    for kw in ['zbmp','Z-Brand','ZBRAND','사랑해','product_profile','RELEASE_PROFILE','customer_release']:
        if kw.lower() in t.lower():
            ln=t.lower()[:t.lower().find(kw.lower())].count('\n')+1
            p(f'{os.path.relpath(f,ROOT)}:{ln}  hit={kw}'); hit=True
if not hit: p('  (无任何产品线/密钥门源码证据)')
p('\n## products / core 目录是否存在: '+str([d for d in ['products','core','zbmp'] if os.path.exists(os.path.join(ROOT,d))]) or '(不存在)')

# ---- 启动脚本 ----
p('\n## 启动脚本清单 (.bat/.vbs/.ps1) 数量与名称')
bats=glob.glob(os.path.join(ROOT,'*.bat'))+glob.glob(os.path.join(ROOT,'*.vbs'))+glob.glob(os.path.join(ROOT,'*.ps1'))
p(f'共 {len(bats)} 个: '+', '.join(os.path.basename(b) for b in bats))

open(os.path.join(OUT,'01_arch.txt'),'w',encoding='utf-8').write('\n'.join(buf))
print('written 01_arch.txt lines=',len(buf))

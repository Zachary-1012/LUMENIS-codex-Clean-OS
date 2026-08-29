# -*- coding: utf-8 -*-
import os,re,glob
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));os.chdir(ROOT)
OUT=os.path.join(ROOT,'docs','audit_evidence');os.makedirs(OUT,exist_ok=True)
buf=[];p=buf.append
# SPA 视图机制
idx=open('templates/index.html',encoding='utf-8',errors='ignore').read()
p('## index.html 中视图/页面容器 (class/id 含 view/page/section/tab)')
for m in set(re.findall(r'id=["\']([^"\']*(?:view|page|pane|section|tab)[^"\']*)["\']',idx,re.I)): p('  id='+m)
for m in set(re.findall(r'data-(?:page|view|target)=["\']([^"\']+)',idx)): p('  data='+m)
# app.js 中视图名
if os.path.exists('static/js/app.js'):
    aj=open('static/js/app.js',encoding='utf-8',errors='ignore').read()
    vw=set(re.findall(r"(?:showView|switchView|navigateTo|loadPage|showPage)\(['\"]([\w-]+)",aj))
    p(f'\n## app.js 视图切换函数目标 {len(vw)}: {sorted(vw)}')
    # 菜单/导航条目
    nav=set(re.findall(r'data-(?:page|view|nav)=["\']([\w-]+)',aj))
    p(f'  app.js data-page/nav: {sorted(nav)}')
# 所有 JS 里出现的页面模块名（中文菜单）
p('\n## 侧边菜单中文名 (index.html)')
for m in re.findall(r'>\s*([一-龥][一-龥A-Za-z0-9·/]{1,10})\s*<',idx)[:40]: p('  '+m)
# 独立话题监测页路由
ap=open('app.py',encoding='utf-8',errors='ignore').read()
p('\n## 独立页面路由 (render_template)')
for i,l in enumerate(ap.split('\n'),1):
    if 'render_template' in l: p(f'  {i}: {l.strip()[:100]}')
# 登录页/手机验证码
p('\n## 登录双方式/手机验证码/三级权限/RBAC 证据')
for kw in ['手机验证','sms','send_code','verify_code','role','is_admin','permission','RBAC','安全问答','security_question','login.html']:
    hits=[]
    for f in ['app.py']+glob.glob('templates/**/*.html',recursive=True):
        t=open(f,encoding='utf-8',errors='ignore').read()
        if kw.lower() in t.lower(): hits.append(f)
    p(f'  {kw}: {sorted(set(hits))[:5] or "无"}')
# CHANGELOG 头部
p('\n## CHANGELOG 最新版本')
for c in ['CHANGELOG.md','CHANGELOG.txt','docs/CHANGELOG.md']:
    if os.path.exists(c):
        head=open(c,encoding='utf-8',errors='ignore').read().split('\n')[:14]
        p(f'--- {c} ---'); [p('  '+x) for x in head]; break
else: p('  无 CHANGELOG')
# requirements
p('\n## requirements.txt')
if os.path.exists('requirements.txt'):
    [p('  '+l.strip()) for l in open('requirements.txt',encoding='utf-8',errors='ignore').read().split('\n') if l.strip() and not l.startswith('#')][:40]
open(os.path.join(OUT,'06_spa_misc.txt'),'w',encoding='utf-8').write('\n'.join(buf))
print('written 06 lines',len(buf))

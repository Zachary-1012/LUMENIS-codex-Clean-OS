# -*- coding: utf-8 -*-
"""只读审计探查5：前端SPA/移动端/Zachary/守护三模块/通知/测试/版本。"""
import os,re,glob
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));os.chdir(ROOT)
OUT=os.path.join(ROOT,'docs','audit_evidence');os.makedirs(OUT,exist_ok=True)
buf=[];p=buf.append
# 1 templates 页面
p('## 1 templates 页面清单')
tpl=sorted(glob.glob('templates/**/*.html',recursive=True))
for t in tpl: p('  '+t+f'  ({os.path.getsize(t)//1024}KB)')
# SPA viewId / data-view
base=open('templates/base.html',encoding='utf-8',errors='ignore').read() if os.path.exists('templates/base.html') else ''
views=set(re.findall(r'data-view=["\']([^"\']+)',base))|set(re.findall(r'viewId[=:]\s*["\']?(\d+)',base))
p(f'  base.html 中 data-view/viewId 数: {len(views)}; 样例 {sorted(views)[:20]}')
# 2 base.html 引用 JS
p('\n## 2 base.html 引用的本地 JS')
for m in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',base):
    if 'cdn' not in m and 'http' not in m: p('  '+m)
p('  CDN: '+', '.join(sorted(set(re.findall(r'src=["\'](https?://[^"\']+)',base)))[:12]))
# 3 移动端响应式
p('\n## 3 移动端 viewport / @media / 断点')
p('  base viewport: '+(re.search(r'<meta[^>]+name=["\']viewport["\'][^>]*>',base).group(0)[:120] if re.search(r'viewport',base) else '无'))
media={}
for css in glob.glob('static/**/*.css',recursive=True):
    t=open(css,encoding='utf-8',errors='ignore').read()
    bp=re.findall(r'@media[^{]*?(\d{3,4})px',t)
    if bp: media[css]=sorted(set(int(x) for x in bp))
for c,b in list(media.items())[:12]: p(f'  {c}: 断点{sorted(b)}')
# 4 Zachary
p('\n## 4 Zachary 机器人证据')
for f in glob.glob('static/**/*.js',recursive=True)+glob.glob('templates/**/*.html',recursive=True):
    t=open(f,encoding='utf-8',errors='ignore').read()
    n=len(re.findall(r'[Zz]achary|robot|Robot',t))
    if n: p(f'  {f}: zachary/robot 命中{n}')
for img in glob.glob('static/img/*robot*')+glob.glob('static/**/*robot*',recursive=True): p('  img: '+img)
# 5 守护三模块
p('\n## 5 system_guardian/auto_recovery/data_feedback_loop 是否被 import/启动')
for mod in ['system_guardian','auto_recovery','data_feedback_loop']:
    hits=[]
    for f in glob.glob('*.py'):
        t=open(f,encoding='utf-8',errors='ignore').read()
        for i,l in enumerate(t.split('\n'),1):
            if re.search(rf'\b{mod}\b',l) and f!=mod+'.py': hits.append(f'{f}:{i}:{l.strip()[:80]}')
    exist=os.path.exists(mod+'.py')
    p(f'  {mod}.py 存在={exist}; 外部引用: '+(str(hits[:4]) if hits else '无(未接入)'))
# 6 微信通知
p('\n## 6 wechat_notifier 配置/启用')
if os.path.exists('wechat_notifier.py'):
    t=open('wechat_notifier.py',encoding='utf-8',errors='ignore').read().split('\n')
    for i,l in enumerate(t,1):
        if re.search(r'APPID|APP_SECRET|TEMPLATE|enabled|os.getenv|def send|class ',l): p(f'  {i}: {l.strip()[:90]}')
        if i>120: break
# app 是否 import wechat
for f in ['app.py']:
    t=open(f,encoding='utf-8',errors='ignore').read()
    p('  app.py 引用 wechat_notifier: '+('是' if 'wechat_notifier' in t else '否(未接入)'))
# 7 测试
p('\n## 7 tests 正式测试文件')
tl=[f for f in glob.glob('tests/test_*.py')]
for t in sorted(tl):
    n=len(re.findall(r'def test_',open(t,encoding='utf-8',errors='ignore').read()))
    p(f'  {t}  用例{n}')
p(f'  正式 test 文件 {len(tl)} 个')
# 8 版本号
p('\n## 8 版本号出现位置')
for f in ['app.py']:
    for i,l in enumerate(open(f,encoding='utf-8',errors='ignore').read().split('\n'),1):
        if re.search(r'APP_VERSION|VERSION\s*=\s*["\']',l): p(f'  {f}:{i}:{l.strip()[:80]}')
for f in glob.glob('templates/**/*.html',recursive=True):
    t=open(f,encoding='utf-8',errors='ignore').read()
    for m in re.finditer(r'v?5\.8\.\d',t):
        p(f'  {f}: {m.group(0)}'); break
# 9 AI 解耦：ai_analyzer/intelligence 是否 import 云端
p('\n## 9 ai_analyzer/intelligence/ai_filter 是否依赖云端 ark/requests-llm')
for f in ['ai_analyzer.py','intelligence.py','ai_filter.py','local_ai_client.py']:
    if not os.path.exists(f): continue
    t=open(f,encoding='utf-8',errors='ignore').read()
    dep=[l.strip()[:90] for l in t.split('\n') if re.search(r'import ark|ark_llm|requests\.post.*ark|volces|openai|api\.',l,re.I)]
    p(f'  {f}: '+(str(dep[:3]) if dep else '无云端依赖(本地规则)'))
open(os.path.join(OUT,'05_frontend_ops.txt'),'w',encoding='utf-8').write('\n'.join(buf))
print('written 05 lines',len(buf))

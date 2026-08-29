# -*- coding: utf-8 -*-
"""只读审计探查3：采集状态机/Auth/风控/二维码/登录跳转/采集器清单。"""
import os,re,glob
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
OUT=os.path.join(ROOT,'docs','audit_evidence'); os.makedirs(OUT,exist_ok=True)
buf=[];p=buf.append
def scan(exts, patterns, label, maxhit=10, skip=('.venv','node_modules','__pycache__','audit_evidence','_zbmp_docs')):
    p(f'\n## {label}')
    regs=[(name,re.compile(rx)) for name,rx in patterns]
    total=0
    for f in glob.glob('**/*',recursive=True):
        if not os.path.isfile(f): continue
        if any(s in f.replace('\\','/') for s in skip): continue
        ext=os.path.splitext(f)[1].lower()
        if ext not in exts: continue
        try: t=open(f,encoding='utf-8',errors='ignore').read()
        except: continue
        for i,l in enumerate(t.split('\n'),1):
            for name,rx in regs:
                if rx.search(l):
                    p(f'  {f}:{i} [{name}] {l.strip()[:110]}'); total+=1
                    if total>=maxhit: p('   ...(截断)'); return
CODE={'.py','.js','.cjs','.html'}
# 1 六态/统一状态枚举
scan(CODE,[('NO_NEW',r'NO_NEW_DATA'),('AUTH_REQ',r'AUTH_REQUIRED|SESSION_EXPIRED|QR_REQUIRED|AUTH_RECOVER'),
           ('VERIFY',r'NEED_VERIFY|CAPTCHA'),('BLOCK',r'\bBLOCKED\b|IP_RISK|300012'),
           ('COOL',r'COOLING_DOWN|PARTIAL_SUCCESS|COLLECT_ERROR|RISK_WARNING')], '1 采集/Auth 状态枚举出现位置',24)
# 2 熔断/冷却/健康检查
scan(CODE,[('circuit',r'circuit|breaker|熔断'),('cooldown',r'cooldown|冷却'),('health',r'health.?check|健康检查')], '2 熔断/冷却/健康检查',18)
# 3 300012
scan(CODE,[('300012',r'300012')], '3 300012 识别点',10)
# 4 跳转登录旧逻辑 / 401 / login_required
scan(CODE,[('redirect_login',r"redirect\(['\"].*login"),('abort401',r'abort\(401|401'),('login_req',r'login_required|@auth|requires_auth'),('www-authenticate',r'WWW-Authenticate|Basic')], '4 登录跳转/鉴权旧逻辑',16)
# 5 二维码/扫码
scan(CODE,[('qr',r'qrcode|QRCode|get_qr|二维码|扫码|qr_code|login_qr')], '5 二维码/扫码能力',16)
# 6 Auth Recovery 前端弹窗
scan(CODE,[('recovery',r'auth.?recovery|authRecovery|恢复弹窗|RecoveryModal|recovery-modal')], '6 统一Auth Recovery弹窗',10)
# 7 采集器文件清单
p('\n## 7 采集器/平台适配文件清单')
for f in sorted(glob.glob('*.py')+glob.glob('*.js')+glob.glob('*.cjs')):
    if re.search(r'collect|crawler|spider|xhs|rednote|weibo|bili|web_monitor|browser_disc|doubao|adapter|cdp',f,re.I):
        sz=os.path.getsize(f)//1024
        # 统计其中 def/class 数
        t=open(f,encoding='utf-8',errors='ignore').read()
        nd=len(re.findall(r'^\s*def ',t,re.M)); nc=len(re.findall(r'^\s*class ',t,re.M))
        p(f'  {f:36s} {sz:5d}KB def={nd} class={nc}')
# 8 平台 adapter 是否有统一基类
scan({'.py'},[('adapter',r'class .*Adapter|PlatformAdapter|BaseCollector|register_adapter|ADAPTERS')],'8 平台适配器抽象',12)
# 9 微博/B站 强制扫码
scan({'.py'},[('wbscan',r'weibo.*扫码|扫码.*weibo|qrcode.*weibo|force.*login|必须.*扫码'),('blscan',r'bili.*扫码')],'9 微博/B站扫码强制',10)
open(os.path.join(OUT,'03_collector_auth.txt'),'w',encoding='utf-8').write('\n'.join(buf))
print('written 03, lines',len(buf))

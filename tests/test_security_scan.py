# -*- coding: utf-8 -*-
"""Release Gate · Security Scan：断言
1) 被 git 跟踪的源码不含真实 Cookie/Session 票据；
2) .env / 生产库 / 私有状态目录被 .gitignore 忽略；
3) 源码不再硬编码超管密码；
4) 内置 SecurityScanner 敏感信息扫描（排除 IDE 内置目录后）无高危命中。
不打印任何真实凭证值。"""
import io, os, sys, re, subprocess
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
GIT = r'C:\Program Files\Git\cmd\git.exe'
fail = []

tracked = subprocess.run([GIT, 'ls-files'], capture_output=True, text=True, encoding='utf-8').stdout.splitlines()

# 1) 真实票据
pat = re.compile(r'(web_session=[0-9a-zA-Z%]{20,}|sessionid=[0-9a-f]{20,}|"sessionid"\s*:\s*"[0-9a-f]{20,}|a1=[0-9a-f]{20,}|xhsappsecapi=[0-9a-f]{20,})')
ticket_hits = []
for t in tracked:
    if not (t.endswith('.py') or t.endswith('.js')) or not os.path.exists(t):
        continue
    txt = io.open(t, 'r', encoding='utf-8', errors='ignore').read()
    if pat.search(txt):
        ticket_hits.append(t)
print('真实票据入库命中 =', ticket_hits or 'NONE')
if ticket_hits: fail.append('tracked_ticket:' + ','.join(ticket_hits))

# 2) 敏感产物被忽略
ign = subprocess.run([GIT, 'check-ignore', '.env', 'data/monitor.db', 'data/private/xhs_circuit.json'],
                     capture_output=True, text=True, encoding='utf-8').stdout.splitlines()
print('被忽略敏感产物 =', ign)
for need in ('.env', 'data/monitor.db', 'data/private/xhs_circuit.json'):
    if need not in ign: fail.append('not_ignored:' + need)

# 3) 无硬编码超管密码
pwd_hits = []
for t in tracked:
    if not t.endswith('.py') or not os.path.exists(t):
        continue
    txt = io.open(t, 'r', encoding='utf-8', errors='ignore').read()
    if os.environ.get('LUMENIS_TEST_AUTH_PASS') and re.search(r"(AUTH_PASSWORD|PASSWORD)\s*=\s*['\"]" + re.escape(os.environ['LUMENIS_TEST_AUTH_PASS']) + r"['\"]", txt):
        pwd_hits.append(t)
print('硬编码超管密码命中 =', pwd_hits or 'NONE')
if pwd_hits: fail.append('hardcoded_pwd:' + ','.join(pwd_hits))

# 4) 内置扫描器：统计源码（排除 .trae-cn IDE 目录）高危命中数
from security_scanner import SecurityScanner
res = SecurityScanner().scan_sensitive_info()
real = [f for f in res.get('findings', []) if '.trae-cn' not in f['file'] and 'verify_system.py' not in f['file']]
print('源码高危敏感命中(排除IDE/检测逻辑自身) =', len(real))
for f in real[:20]:
    print('  ', f['file'], 'L'+str(f['line']), f['issue'])
if real: fail.append('scanner_findings:%d' % len(real))

print('\nSECURITY_SCAN RESULT:', 'ALL_PASS' if not fail else f'FAIL {fail}')
sys.exit(1 if fail else 0)

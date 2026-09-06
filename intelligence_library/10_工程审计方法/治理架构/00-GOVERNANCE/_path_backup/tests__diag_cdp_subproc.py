# -*- coding: utf-8 -*-
import os, sys, io, subprocess, json
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = r'D:\Taikoo-monitor-new'
cjs = os.path.join(ROOT, 'rednote_collector.cjs')
out = os.path.join(ROOT, 'data', f'_diag_{datetime.now():%H%M%S}.json')
env = os.environ.copy(); env['XHS_CDP_URL'] = 'http://127.0.0.1:9222'
cmd = ['node', cjs, '--keyword', '广州太古汇', '--output', out, '--max-scroll', '1', '--max-details', '2']
print('cmd node 解析:', subprocess.run(['where','node'],capture_output=True,text=True).stdout.strip())
print('cjs存在:', os.path.exists(cjs))
p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300, env=env)
print('returncode=', p.returncode)
print('--- stdout 尾1200 ---'); print((p.stdout or '')[-1200:])
print('--- stderr 尾800 ---'); print((p.stderr or '')[-800:])
print('out文件存在:', os.path.exists(out), out)

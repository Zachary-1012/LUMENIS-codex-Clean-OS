# -*- coding: utf-8 -*-
"""classify_collect_state 六态归一化单测：空结果/登录/验证/IP熔断/网络严格区分。"""
import io, os, sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import collector
f = collector.classify_collect_state
fails = []
def ck(desc, got, expect):
    ok = got == expect
    print(('PASS' if ok else 'FAIL'), desc, '->', got)
    if not ok: fails.append((desc, got, expect))

ck('有内容无错误', f('', '', 5), 'SUCCESS')
ck('无内容无错误=EMPTY(不是风控)', f('', '', 0), 'EMPTY')
ck('IP风险300012', f('IP_RISK_OR_300012', '', 0), 'BLOCKED')
ck('NEED_VERIFY文本', f('NEED_VERIFY', '', 0), 'CAPTCHA')
ck('guard熔断cooldown', f('', 'cooldown', 0), 'BLOCKED')
ck('guard暂停paused', f('', 'paused', 0), 'BLOCKED')
ck('guard需验证', f('', 'need_verify', 0), 'CAPTCHA')
ck('guard登录失效', f('', 'auth_required', 0), 'AUTH_REQUIRED')
ck('中文安全验证', f('请完成安全验证', '', 0), 'CAPTCHA')
ck('超时=网络错误(不弹登录)', f('Timeout', '', 0), 'NETWORK_ERROR')
ck('解析失败=网络错误', f('CDP结果解析失败: xx', '', 0), 'NETWORK_ERROR')
ck('中文未登录', f('当前未登录', '', 0), 'AUTH_REQUIRED')
ck('session英文失效', f('invalid session', '', 0), 'AUTH_REQUIRED')

print('\n六态归一化:', '全部通过' if not fails else f'{len(fails)}失败 {fails}')
sys.exit(1 if fails else 0)

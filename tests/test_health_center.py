# -*- coding: utf-8 -*-
"""全局平台健康状态中心单测：三类分清 / 平台隔离 / 未启用≠0条 / 不伪装。纯内存不触网。"""
import io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from platform_adapters.health_center import build_platform_health, IDLE, DISABLED
from platform_adapters.scheduling import PlatformSchedulePlanner
from platform_adapters.scheduling import state_map as sm

_fails, _total = [], 0
def check(name, cond):
    global _total
    _total += 1
    print(('  OK ' if cond else 'FAIL ') + name)
    if not cond:
        _fails.append(name)

def find(h, key):
    return next(p for p in h['platforms'] if p['platform'] == key)

def health(last=None, circuit=None, session=True):
    rt = {'circuit': circuit or {}, 'last': last, 'session_valid': session, 'session_msg': ''}
    return build_platform_health(runtime_provider=lambda k: rt, planner=PlatformSchedulePlanner())

# 1. 待命：启用但无记录 = IDLE（非异常非0条）；未启用槽位 = DISABLED
h = health()
xhs, dy, wb = find(h, 'xhs'), find(h, 'douyin'), find(h, 'weibo')
check('1a xhs启用且待命IDLE', xhs['status'] == IDLE and xhs['enabled'])
check('1b 抖音SECONDARY禁用且非0条', dy['status'] == DISABLED and not dy['enabled'])
check('1c 共7个平台槽位', len(h['platforms']) == 7)

# 2. 成功
h = health(last={'state': 'SUCCESS', 'notes': 5, 'msg': '', 'at': 't'})
check('2 成功态OK', find(h, 'xhs')['status'] == sm.CS.SUCCESS and find(h, 'xhs')['triage'] == 'OK')

# 3. 空批 = NO_NEW_DATA（接口正常无新内容，区别于风控空）
h = health(last={'state': 'EMPTY', 'notes': 0, 'msg': '', 'at': 't'})
check('3 EMPTY归一NO_NEW_DATA', find(h, 'xhs')['status'] == sm.CS.NO_NEW_DATA)

# 4. 熔断 = COOLING_DOWN 且必须停请求
h = health(circuit={'open': True, 'state': 'circuit', 'resume_at': '2026-08-30 19:00:00'})
x = find(h, 'xhs')
check('4 熔断COOLING且stop', x['status'] == sm.CS.COOLING_DOWN and x['stop_request'] and not x['needs_human'])

# 5. 登录失效 = SESSION_EXPIRED / A类 / 需人工 / 弹Auth
h = health(last={'state': 'AUTH_FAILED', 'notes': None, 'msg': '登录失效', 'at': 't'})
x = find(h, 'xhs')
check('5a AUTH_FAILED归SESSION_EXPIRED', x['status'] == sm.CS.SESSION_EXPIRED)
check('5b A类且需人工', x['triage'] == sm.CLASS_A_AUTH and x['needs_human'])
check('5c overall升级到登录失效', h['overall'] == sm.CS.SESSION_EXPIRED and h['needs_human'])

# 6. 平台隔离：xhs 登录失效不影响抖音/微博槽位显示
check('6 平台隔离不连带', find(h, 'douyin')['status'] == DISABLED and find(h, 'weibo')['status'] == DISABLED)

# 7. 人机验证 = NEED_VERIFY / B类 / 停请求 / 需人工（不绕过）
h = health(last={'state': 'CAPTCHA', 'notes': None, 'msg': '安全验证', 'at': 't'})
x = find(h, 'xhs')
check('7 CAPTCHA归NEED_VERIFY/B类/停请求', x['status'] == sm.CS.NEED_VERIFY and
      x['triage'] == sm.CLASS_B_VERIFY and x['stop_request'] and x['needs_human'])

# 8. 300012 IP风控 = C类熔断
h = health(last={'state': 'BLOCKED', 'notes': None, 'msg': 'IP_RISK_OR_300012', 'at': 't'})
x = find(h, 'xhs')
check('8 BLOCKED为C类且停请求', x['triage'] == sm.CLASS_C_RISK and x['stop_request'])

# 9. 会话本地即判失效（无last）
h = health(session=False)
check('9 无记录但会话失效=SESSION_EXPIRED', find(h, 'xhs')['status'] == sm.CS.SESSION_EXPIRED)

print(f'\n总计 {_total} 项，失败 {len(_fails)} 项')
if _fails:
    print('FAILED:', _fails); sys.exit(1)
print('ALL_HEALTH_CENTER_TESTS_PASS')

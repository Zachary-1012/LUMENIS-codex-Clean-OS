# -*- coding: utf-8 -*-
import io, os, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from collector_guard.risk_engine import RiskEngine, BAND_TO_STATE
from collector_guard.state import CollectState

fails = []
def check(name, cond, extra=''):
    print(('PASS' if cond else 'FAIL'), name, extra)
    if not cond: fails.append(name)

# 1 初始正常
r = RiskEngine()
s, b, st = r.snapshot()['risk_score'], r.snapshot()['band'], r.snapshot()['state']
check('初始 NORMAL/healthy', b == 'NORMAL' and st == CollectState.HEALTHY, f'{s}/{b}')

# 2 单个 empty_result=10 -> NORMAL
r.record_failure('empty_result')
check('empty_result=10 NORMAL', r.band_of() == 'NORMAL', f'score={r.score}')

# 3 abnormal(15) 且第二次连续失败 +continuous20 => 10+15+20=45 WATCH
r.record_failure('abnormal_response')
check('累计45 WATCH', r.score == 45 and r.band_of() == 'WATCH', f'score={r.score} band={r.band_of()}')

# 4 再一次连续失败 http(10)+20=75 -> COOLDOWN
r.record_failure('http_error')
check('累计75 COOLDOWN', r.band_of() == 'COOLDOWN', f'score={r.score} band={r.band_of()}')

# 5 硬信号 security_page 即使低分也直接熔断
r2 = RiskEngine()
score, band, state = r2.record_failure('security_page')
check('安全页硬熔断', band == 'CIRCUIT_OPEN' and state == CollectState.PAUSED, f'{score}/{band}/{state}')

# 6 硬信号 rate_limited -> COOLDOWN
r3 = RiskEngine()
_, b3, st3 = r3.record_failure('rate_limited')
check('限流硬冷却', b3 == 'COOLDOWN' and st3 == CollectState.COOLDOWN, b3)

# 7 login_error 硬熔断（登录失效，转 Auth，不伪装0条）
r4 = RiskEngine()
_, b4, st4 = r4.record_failure('login_error')
check('登录失效硬熔断', b4 == 'CIRCUIT_OPEN' and st4 == CollectState.PAUSED, b4)

# 8 成功衰减恢复
r5 = RiskEngine()
r5.record_failure('continuous_failure'); r5.record_failure('continuous_failure')
before = r5.score
for _ in range(6):
    r5.record_success()
check('成功后回落 NORMAL', r5.band_of() == 'NORMAL' and r5.score < before, f'{before}->{r5.score}')

# 9 时间自然衰减：把 last_update 回拨 40s（4个10s步 * decay3=12）
r6 = RiskEngine(decay_per_10s=3)
r6.score = 50
r6.last_update = time.time() - 40
r6._time_decay(time.time())
check('40s自然衰减12', r6.score == 38, f'score={r6.score}')

# 10 封顶100
r7 = RiskEngine()
for _ in range(10):
    r7.record_failure('security_page')
check('风险分封顶100', r7.score == 100 and r7.band_of() == 'CIRCUIT_OPEN', f'score={r7.score}')

print('\n风险引擎单测结果:', '全部通过' if not fails else f'{len(fails)} 项失败 {fails}')
sys.exit(1 if fails else 0)

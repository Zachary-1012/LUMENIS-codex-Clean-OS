# -*- coding: utf-8 -*-
"""Team2 采集韧性恢复测试：BEEP协议 + 自适应限速 + 状态机 + 失败分类"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")

print("=" * 60)
print("Team2 采集韧性恢复测试")
print("=" * 60)

# ===== 1. BEEP 执行协议 =====
print("\n[1] BEEPExecutor 有限重试 + 证据链")
from lumenis.system.browser.runtime.contract import (
    BEEPExecutor, BEEPTrace, FailureClass, BrowserContract, MAX_RETRY,
)

beep = BEEPExecutor(max_retry=3)

# 成功路径
call_count = [0]
def success_action():
    call_count[0] += 1
    return {"ok": True, "data": "test"}
trace = beep.run("test_action", success_action, verify_fn=lambda r: r.get("ok") is True)
check("BEEP 成功返回 SUCCESS", trace.result == "SUCCESS")
check("BEEP 重试次数=1", trace.retry_count == 1)
check("BEEP 有 EVIDENCE 步骤", any(s["step"] == "evidence" for s in trace.steps))
check("BEEP 有 DECISION 步骤", any(s["step"] == "decision" for s in trace.steps))
check("BEEP to_evidence 不含密钥", "cookie" not in str(trace.to_evidence()).lower()
      and "token" not in str(trace.to_evidence()).lower())

# 失败重试（最终失败）
fail_count = [0]
def always_fail():
    fail_count[0] += 1
    raise RuntimeError("connection timeout")
trace2 = beep.run("fail_action", always_fail, retry_safe=True)
check("BEEP 失败重试达上限", fail_count[0] == 3, f"got {fail_count[0]}")
check("BEEP 最终 VERIFY_FAILED", trace2.result in ("VERIFY_FAILED", "FAILED"))
check("BEEP 错误被记录", trace2.error is not None and trace2.failure_class == FailureClass.TRANSIENT)

# verify 失败触发重试
verify_count = [0]
def verify_fail_then_pass(result):
    verify_count[0] += 1
    return verify_count[0] >= 2
trace3 = beep.run("verify_retry", lambda: {"ok": True}, verify_fn=verify_fail_then_pass, retry_safe=True)
check("BEEP verify失败后重试成功", trace3.result == "SUCCESS")
check("BEEP verify重试2次", trace3.retry_count == 2, f"got {trace3.retry_count}")

# Precondition 失败直接跳过
trace4 = beep.run("skip_action", lambda: "should not run", precondition_fn=lambda: False)
check("BEEP precondition=False 跳过", trace4.result == "SKIP_PRECONDITION")

# MAX_RETRY 常量
check("MAX_RETRY=3（禁止无限重试）", MAX_RETRY == 3)

# ===== 2. 失败分类 =====
print("\n[2] BrowserContract.classify_failure 六类分类")
cf = BrowserContract.classify_failure
check("timeout→TRANSIENT", cf("connection timeout") == FailureClass.TRANSIENT)
check("network error→TRANSIENT", cf("network unreachable") == FailureClass.TRANSIENT)
check("session expired→SESSION", cf("session expired") == FailureClass.SESSION)
check("unauthorized→SESSION", cf("401 unauthorized") == FailureClass.SESSION)
check("selector not found→PAGE_CHANGED", cf("no such element") == FailureClass.PAGE_CHANGED)
check("forbidden→PERMISSION", cf("403 forbidden") == FailureClass.PERMISSION)
check("captcha→PLATFORM_RISK", cf("captcha required") == FailureClass.PLATFORM_RISK)
check("blocked→PLATFORM_RISK", cf("ip blocked") == FailureClass.PLATFORM_RISK)
check("safe_stop→PLATFORM_RISK", cf("policy safe_stop") == FailureClass.PLATFORM_RISK)
check("unknown→UNKNOWN", cf("something weird") == FailureClass.UNKNOWN)

# ===== 3. 自适应限速器 =====
print("\n[3] AdaptiveRateLimiter 指数退避 + 冷却恢复")
from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
from lumenis.system.collector.guard.state import CollectState

rl = AdaptiveRateLimiter(base_interval=10, min_interval=5, fail_threshold=3, cooldown_seconds=60, enabled=True)
check("初始 HEALTHY", rl.state == CollectState.HEALTHY)
check("初始间隔=base", rl.interval == 10)

# 成功：间隔缩小
rl.on_success()
check("成功后间隔缩小", rl.interval < 10)
check("成功后仍 HEALTHY", rl.state == CollectState.HEALTHY)

# 失败1次：WARNING
rl.on_failure()
check("1次失败→WARNING", rl.state == CollectState.WARNING)
check("失败后间隔翻倍", rl.interval >= 10)

# 失败2次
rl.on_failure()
check("2次失败仍 WARNING", rl.state == CollectState.WARNING)

# 失败3次：COOLDOWN
rl.on_failure()
check("3次失败→COOLDOWN", rl.state == CollectState.COOLDOWN)
check("冷却截止时间已设置", rl.cooldown_until > time.time())

# 冷却中 can_run 应为 False
check("冷却中 can_run=False", rl.can_run() is False)

# An unrelated success must not erase an active local/server cooldown.
active_deadline = rl.cooldown_until
rl.on_success()
check("未到期成功不解除 COOLDOWN", rl.state == CollectState.COOLDOWN)
check("未到期成功不清除截止时间", rl.cooldown_until == active_deadline)
check("未到期成功后仍禁止请求", rl.can_run() is False)

# Advance both wall and monotonic clocks; only an expired half-open probe may recover.
from unittest.mock import patch
future_wall = time.time() + 61
future_monotonic = time.monotonic() + 61
with patch("lumenis.system.collector.guard.rate_limiter.time.time", return_value=future_wall), \
        patch("lumenis.system.collector.guard.rate_limiter.time.monotonic", return_value=future_monotonic):
    check("冷却到期允许 half-open", rl.can_run() is True)
    rl.on_success()
    check("成功后恢复 HEALTHY", rl.state == CollectState.HEALTHY)
    check("冷却清除", rl.cooldown_until == 0.0)

# force_pause（外部 Auth/验证码触发）
rl.force_pause(state=CollectState.AUTH_REQUIRED, cooldown_seconds=120)
check("force_pause→AUTH_REQUIRED", rl.state == CollectState.AUTH_REQUIRED)
check("AUTH_REQUIRED 在 STOP_REQUEST", rl.state in CollectState.STOP_REQUEST)

# ===== 4. 状态机 STOP_REQUEST 红线 =====
print("\n[4] CollectState 停止请求红线")
check("COOLDOWN 停止请求", CollectState.COOLDOWN in CollectState.STOP_REQUEST)
check("PAUSED 停止请求", CollectState.PAUSED in CollectState.STOP_REQUEST)
check("AUTH_REQUIRED 停止请求", CollectState.AUTH_REQUIRED in CollectState.STOP_REQUEST)
check("NEED_VERIFY 停止请求", CollectState.NEED_VERIFY in CollectState.STOP_REQUEST)
check("HEALTHY 不停止", CollectState.HEALTHY not in CollectState.STOP_REQUEST)
check("WARNING 不停止", CollectState.WARNING not in CollectState.STOP_REQUEST)
check("NETWORK_ERROR 不停止（可退避重试）", CollectState.NETWORK_ERROR not in CollectState.STOP_REQUEST)

# ===== 5. CollectorGuard 显式风控码映射 =====
print("\n[5] CollectorGuard 显式风控码映射")
from lumenis.system.collector.guard.guard import _EXPLICIT
check("IP_RISK_OR_300012→COOLDOWN", _EXPLICIT.get("IP_RISK_OR_300012")[0] == CollectState.COOLDOWN)
check("NEED_VERIFY→NEED_VERIFY", _EXPLICIT.get("NEED_VERIFY")[0] == CollectState.NEED_VERIFY)
check("AUTH_REQUIRED→AUTH_REQUIRED", _EXPLICIT.get("AUTH_REQUIRED")[0] == CollectState.AUTH_REQUIRED)

# ===== 6. BrowserState 状态机序列 =====
print("\n[6] BrowserState 成功路径序列")
from lumenis.system.browser.runtime.contract import BrowserState
seq = BrowserContract.state_sequence()
check("状态序列含 INIT", "INIT" in seq)
check("状态序列含 SESSION_VALID", "SESSION_VALID" in seq)
check("状态序列含 SUCCESS", "SUCCESS" in seq)
check("状态序列含 VERIFY_FAILED（失败态）", hasattr(BrowserState, "VERIFY_FAILED"))
check("状态序列含 CLASSIFY_FAILURE", hasattr(BrowserState, "CLASSIFY_FAILURE"))

# ===== 7. 状态映射三类分清 =====
print("\n[7] state_map 三类分清（A Auth / B Verify / C Risk）")
from lumenis.system.collector.adapters.scheduling.state_map import (
    CS, incident_class, CLASS_A_AUTH, CLASS_B_VERIFY, CLASS_C_RISK,
    is_stop_request, needs_human, is_ok, to_canonical
)
check("SESSION_EXPIRED=A类(Auth)", incident_class(CS.SESSION_EXPIRED) == CLASS_A_AUTH)
check("NEED_VERIFY=B类(Verify)", incident_class(CS.NEED_VERIFY) == CLASS_B_VERIFY)
check("BLOCKED=C类(Risk)", incident_class(CS.BLOCKED) == CLASS_C_RISK)
check("COOLING_DOWN=C类(Risk)", incident_class(CS.COOLING_DOWN) == CLASS_C_RISK)
check("RISK_WARNING=C类(Risk)", incident_class(CS.RISK_WARNING) == CLASS_C_RISK)
check("SUCCESS=OK", incident_class(CS.SUCCESS) == "OK")
check("A类需人工", needs_human(CS.SESSION_EXPIRED) is True)
check("B类需人工", needs_human(CS.NEED_VERIFY) is True)
check("C类不需人工（自动冷却）", needs_human(CS.BLOCKED) is False)
check("A类停止请求", is_stop_request(CS.SESSION_EXPIRED) is True)
check("B类停止请求", is_stop_request(CS.NEED_VERIFY) is True)
check("C类停止请求", is_stop_request(CS.BLOCKED) is True)
check("SUCCESS 不停止", is_stop_request(CS.SUCCESS) is False)
check("SUCCESS ok", is_ok(CS.SUCCESS) is True)
check("NO_NEW_DATA ok（不是风控空）", is_ok(CS.NO_NEW_DATA) is True)

# XHS 显式错误码映射
check("XHS IP_RISK→BLOCKED", to_canonical("", xhs_code="IP_RISK_OR_300012") == CS.BLOCKED)
check("XHS NEED_VERIFY→NEED_VERIFY", to_canonical("", xhs_code="NEED_VERIFY") == CS.NEED_VERIFY)
check("XHS AUTH_REQUIRED→SESSION_EXPIRED", to_canonical("", xhs_code="AUTH_REQUIRED") == CS.SESSION_EXPIRED)

# ===== 汇总 =====
print("\n" + "=" * 60)
print(f"测试结果: {PASS} PASS, {FAIL} FAIL, 共 {PASS+FAIL} 项")
print("=" * 60)
if FAIL > 0:
    sys.exit(1)
print("全部通过 ✓")
sys.exit(0)

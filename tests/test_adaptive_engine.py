"""测试自动调节引擎"""
from adaptive_engine import adaptive_engine, StrategyLevel, RiskLevel

print("=== 测试自动调节引擎 ===")
print()

# 1. 初始状态
print("1. 初始状态:")
status = adaptive_engine.get_status()
print(f"   当前策略: {status['current_strategy']}")
print(f"   风险等级: {status['risk_level']}")
params = adaptive_engine.get_current_params()
print(f"   请求间隔: {params['request_delay']}s")
print(f"   最大重试: {params['max_retries']}次")
print(f"   最大并发: {params['max_concurrent']}")
print(f"   暂停时间: {params['pause_minutes']}分钟")
print()

# 2. 测试可以采集
print("2. 测试可以采集:")
can_collect, reason = adaptive_engine.can_collect_now()
print(f"   可以采集: {can_collect}, 原因: {reason}")
print()

# 3. 模拟采集成功
print("3. 模拟采集成功:")
params = adaptive_engine.report_collection_result(success=True, notes_count=10, duration=30)
print(f"   采集成功后策略: {adaptive_engine.get_current_strategy()}")
print(f"   请求间隔: {params['request_delay']}s")
print()

# 4. 模拟连续失败触发风控
print("4. 模拟连续失败触发风控:")
for i in range(5):
    params = adaptive_engine.report_collection_result(success=False, notes_count=0, duration=10, error='验证码频繁')
    print(f"   第{i+1}次失败后: 策略={adaptive_engine.get_current_strategy()}, 风险={adaptive_engine.get_risk_level()}, 成功率={adaptive_engine.get_metrics()['recent_success_rate']}%")
print()

# 5. 测试暂停策略下是否可以采集
print("5. 测试暂停策略下是否可以采集:")
can_collect, reason = adaptive_engine.can_collect_now()
print(f"   可以采集: {can_collect}, 原因: {reason}")
print()

# 6. 重置为正常策略
print("6. 重置为正常策略:")
adaptive_engine.reset_to_normal()
print(f"   重置后策略: {adaptive_engine.get_current_strategy()}")
print(f"   重置后风险: {adaptive_engine.get_risk_level()}")
print()

print("测试完成")

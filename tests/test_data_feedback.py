"""测试数据闭环引擎"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from data_feedback_loop import data_feedback_loop

print("=== 测试数据闭环引擎 ===")
print()

# 1. 分析报告异常
print("1. 分析报告异常:")
anomalies = data_feedback_loop.analyze_report_anomalies()
print(f"   发现异常数: {len(anomalies)}")
for i, anomaly in enumerate(anomalies):
    print(f"   [{i+1}] {anomaly['type']} ({anomaly['severity']}): {anomaly['description']}")
    print(f"       建议: {anomaly['suggestion']}")
print()

# 2. 生成策略建议
print("2. 生成策略建议:")
suggestions = data_feedback_loop.generate_strategy_suggestions(anomalies)
print(f"   生成建议数: {len(suggestions)}")
for i, suggestion in enumerate(suggestions):
    print(f"   [{i+1}] 优先级: {suggestion['priority']}")
    print(f"       行动项: {len(suggestion['action_items'])}个")
    for j, action in enumerate(suggestion['action_items'][:3]):
        print(f"         - {action}")
print()

# 3. 运行完整反馈周期
print("3. 运行完整反馈周期:")
result = data_feedback_loop.run_feedback_cycle()
print(f"   状态: {result['status']}")
print(f"   异常数: {len(result.get('anomalies', []))}")
print(f"   建议数: {len(result.get('suggestions', []))}")
print(f"   已应用: {result.get('applied_count', 0)}")
print()

# 4. 获取统计信息
print("4. 统计信息:")
stats = data_feedback_loop.get_stats()
for key, value in stats.items():
    print(f"   {key}: {value}")
print()

# 5. 获取待处理反馈
print("5. 待处理反馈:")
pending = data_feedback_loop.get_pending_feedback()
print(f"   待处理数: {len(pending)}")
for i, f in enumerate(pending[-3:]):
    print(f"   [{i+1}] {f['timestamp']} - {f['anomaly_type']} - {f['status']}")

print("\n测试完成")

"""测试自动修复引擎"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from auto_recovery import recovery_engine

print("=== 测试自动修复引擎 ===")
health = recovery_engine.health_check()
print("健康检查结果:")
print(f"  系统端口: {health['system_port']}")
print(f"  CDP端口: {health['cdp_port']}")
print(f"  数据库: {health['database']}")
print(f"  问题数: {len(health['issues'])}")
print(f"  需要修复: {health['needs_fix']}")
print()

stats = recovery_engine.get_stats()
print(f"修复统计:")
print(f"  总检查: {stats['total_checks']}")
print(f"  总修复: {stats['total_fixes']}")
print(f"  成功: {stats['successful_fixes']}")
print(f"  失败: {stats['failed_fixes']}")
print(f"  人工介入: {stats['manual_interventions']}")
print()

print("=== 活跃告警 ===")
alerts = recovery_engine.get_active_alerts()
print(f"  活跃告警数: {len(alerts)}")
for alert in alerts[-5:]:
    print(f"    [{alert['level']}] {alert['module']}: {alert['message']}")

print("\n测试完成")

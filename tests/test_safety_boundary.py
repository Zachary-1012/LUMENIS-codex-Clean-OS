"""测试边界控制引擎"""
from safety_boundary import boundary_control_engine, OperationType, SafetyLevel

print("=== 测试边界控制引擎 ===")
print()

# 1. 测试安全级别判断
print("1. 安全级别判断:")
test_operations = [
    (OperationType.READ, "读取数据"),
    (OperationType.RESTART, "重启进程"),
    (OperationType.RETRY, "重试操作"),
    (OperationType.DATA_MODIFY, "修改数据"),
    (OperationType.DATA_DELETE, "删除数据"),
    (OperationType.RULE_CHANGE, "改变规则"),
    (OperationType.SCHEMA_CHANGE, "改变数据库结构"),
    (OperationType.CONFIG_CHANGE, "修改配置"),
    (OperationType.BULK_OPERATION, "批量操作")
]
for op_type, desc in test_operations:
    safety = boundary_control_engine.get_safety_level(op_type)
    can_auto, reason = boundary_control_engine.can_auto_execute(op_type)
    print(f"   {desc}: 安全级别={safety.value}, 可自动={can_auto}, 原因={reason}")
print()

# 2. 测试请求人工确认
print("2. 测试请求人工确认:")
confirmation = boundary_control_engine.request_confirmation(
    OperationType.DATA_MODIFY,
    "批量更新笔记的品牌标签",
    affected_items=["100条笔记"],
    risk_assessment="中等风险，可能影响报告统计"
)
print(f"   确认ID: {confirmation['id']}")
print(f"   操作类型: {confirmation['operation_type']}")
print(f"   描述: {confirmation['description']}")
print(f"   状态: {confirmation['status']}")
print()

# 3. 测试待确认列表
print("3. 待确认列表:")
pending = boundary_control_engine.get_pending_confirmations()
print(f"   待确认数: {len(pending)}")
for p in pending:
    print(f"     [{p['id']}] {p['operation_type']}: {p['description']}")
print()

# 4. 测试批准确认
print("4. 测试批准确认:")
if pending:
    result = boundary_control_engine.approve_confirmation(pending[0]['id'], confirmed_by='test_user')
    print(f"   批准结果: {result}")
    pending_after = boundary_control_engine.get_pending_confirmations()
    print(f"   批准后待确认数: {len(pending_after)}")
print()

# 5. 测试文件完整性
print("5. 测试文件完整性:")
baseline = boundary_control_engine.baseline_file_integrity(['app.py', 'database.py'])
print(f"   基线文件数: {len(baseline)}")
for name, info in baseline.items():
    print(f"     {name}: 大小={info['size']}字节, 哈希={info['hash'][:16]}...")

integrity = boundary_control_engine.check_file_integrity()
print(f"   完整性检查: {integrity['status']}, 检查文件数={integrity.get('checked_files', 0)}, 问题数={len(integrity.get('issues', []))}")
print()

# 6. 统计信息
print("6. 统计信息:")
stats = boundary_control_engine.get_stats()
for key, value in stats.items():
    print(f"   {key}: {value}")

print("\n测试完成")

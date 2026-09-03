# 数据 → 函数计算 → 表格 → 可视化动态表最终执行规范

**Status:** FINAL / implementation authority
**Date:** 2026-09-04

## 核心原则

所有进入可视化层的数据，不允许“原始数据直接画图”。必须经过确定性的程序计算与结构化表格层。

```text
Raw Input
  ↓
Ingestion / Parse
  ↓
Validation
  ↓
Normalization
  ↓
Function Calculation
  ↓
Canonical Table / DataFrame
  ↓
Table Validation
  ↓
Visualization Adapter
  ↓
Dynamic Table / Chart / View
```

## 每一层职责

### 1. Raw Input
保存原始输入，不覆盖、不篡改。

必须保留来源、时间、批次、原始字段和原始值。

### 2. Validation
检查：
- 字段是否存在
- 类型是否正确
- 时间格式是否统一
- 数值是否可计算
- 主键/唯一标识是否冲突
- 缺失值是否符合规则
- 重复数据是否存在

验证失败的数据不得静默进入可视化层。

### 3. Normalization
统一字段名、时间、单位、枚举、空值表达和数据类型。

原始值与标准值必须可追溯。

### 4. Function Calculation
所有派生指标必须通过显式、可测试的函数计算。

例如：

```text
count()
sum()
avg()
rate()
change()
growth_rate()
rank()
rolling()
score()
aggregate()
```

禁止在前端模板中重新计算核心业务指标。

同一指标必须只有一个权威计算函数。

### 5. Canonical Table
函数计算后的结果必须先形成标准表格结构。

最少包含：

```text
record_id
source_id
metric
value
unit
time
category
calculation_version
source_timestamp
```

实际业务表可以扩展字段，但必须保证每个可视化指标能够回溯到表格记录。

### 6. Table Validation
进入可视化前再次检查：

- 行数
- 列名
- 数据类型
- 空值
- 数值范围
- 时间排序
- 聚合口径
- 总量与分项是否一致
- 计算版本

### 7. Visualization Adapter
可视化层只读取标准表格/标准数据对象，不直接理解原始采集结构。

Adapter 负责：

```text
Table
 ↓
View Model
 ↓
Dynamic Table / Chart
```

图表不得自行改变业务数据。

## 数值准确性原则

页面显示值必须满足：

`Visualization Value = Canonical Table Value`

不得出现：

```text
Raw Data → Frontend JS → 隐式计算 → Chart
```

正确方式：

```text
Raw Data
→ Backend/Calculation Function
→ Canonical Table
→ Validated View Model
→ Visualization
```

## 动态表规则

动态表允许排序、筛选、分页、聚合展示，但：

- 排序不能改变原始值
- 筛选不能改变指标定义
- 分页不能重新计算总量
- 前端格式化不能改变真实数值
- 显示四舍五入不能影响底层计算

## 可视化规则

所有 Chart/Table 必须能够回答：

```text
这个数字从哪里来？
用了哪个函数？
函数版本是什么？
计算时间是什么？
原始来源是什么？
```

## 审计字段

建议每条派生指标保留：

```text
source_id
source_type
calculation_function
calculation_version
input_snapshot
calculated_at
validation_status
```

## 禁止

- 前端偷偷计算业务指标
- 图表组件自己聚合原始数据
- 多处复制同一个公式
- 直接把 API 原始响应喂给 Chart
- 为了视觉效果修改真实数据
- 四舍五入后再参与下一步计算
- 用估算值冒充真实采集值

## 验收

任何动态数据组件完成前必须验证：

```text
[ ] 原始数据可追溯
[ ] 数据已验证
[ ] 数据已标准化
[ ] 派生指标由显式函数计算
[ ] 已形成 Canonical Table
[ ] Table 已再次验证
[ ] Visualization 只消费标准数据
[ ] 前端无隐藏业务计算
[ ] 数值与表格一致
[ ] 时间与单位一致
[ ] 可回溯 calculation_version
```

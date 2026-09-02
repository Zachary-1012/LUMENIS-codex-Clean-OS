# 数据质量门 DataQualityGate · 2026-09-03

> 研究来源：**OpenDQV/OpenDQV**（MIT，2026-03，contract-driven data quality validation）。
> 范式：Write-time enforcement——写入前校验，坏记录 422 拒绝（per-field errors），不存 payload；
> Contract YAML 声明式规则，severity=error(阻止)/warning(标记放行)。
> 哲学：A 422 at the point of write is cheaper than a data incident three weeks later.

## 一、为什么

ZBC「数据零丢失」之外还需「数据真」：坏数据（空标题/错日期/非法风险级/重复 Topic 快照）
一旦入库，会污染报告、KOL 分层、舆情判断。写入前校验门在最便宜的位置拦住坏数据。

## 二、ZBC 三层数据治理分工（互补不重复）

| 层 | 职责 | 工具 |
|---|---|---|
| 结构层 | DB 表/列类型反射 | schema_registry（只读） |
| **语义层** | 必填/格式/取值/范围/日期/长度/批内唯一 | **DataQualityGate（本模块）** |
| 下游 | 报告/采集/分析消费 | 各模块 |

## 三、模块

| 文件 | 说明 |
|---|---|
| data_quality_gate.py | DataQualityGate：契约加载+validate+validate_batch（unique 批内去重） |
| config/data-contracts/*.yaml | 内置契约：note / event / topic_snapshot |
| tests/test_data_quality_gate.py | 8 测试（加载/合法/非法/severity/未知契约/枚举/批内唯一/条件规则） |

## 四、规则

not_empty / regex / min / max / range / min_length / max_length / allowed_values / date_format
+ severity(error|warning) + condition(条件应用) + unique(批内)。

## 五、用法

from data_quality_gate import DataQualityGate
gate = DataQualityGate()
res = gate.validate("note", {"title":"...","url":"https://...","publish_date":"2026-08-31 10:00:00"})
# -> {"valid":bool,"errors":[{rule,field,message,severity}],"warnings":[],"contract","version"}
gate.validate_batch("topic_snapshot", records)   # 批内 unique 生效

接线建议：采集写入 DB 前（database.py 插入处）调用 gate.validate(contract, record)，error 拒绝入库并记录失败原因。

## 六、验证

- 单测 8/8 过
- 全量回归 EXIT=0
- Evidence：staging/baseline-evidence/、git commit、OSAI learning-feed

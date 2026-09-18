# 序境 · 研发闭环 Evidence 10 — SIT 六模板机制 + 案例背书

- 日期：2026-09-04
- 基线：ZBC `e4b2cda`（前一轮）
- 类型：创意引擎研究落地（研究→生产闭环）

---

## 1. 能力落地

### A. 新增「六模板转译」机制（Goldenberg SIT）

在创意引擎 `scripts/idea_generator.py` 新增第 9 种机制 `sit`：

| 层 | 落地 |
|---|---|
| `MECHANISMS` | `sit`：Goldenberg SIT 六模板（类比/极端/后果/竞争/换维/实效），把限制/卖点转译成可传播结构 |
| `MECH_TO_L1` | 六模板转译公式 |
| `_HOOK` | 普通版 6 句（类比「把陌生说成熟悉」/极端「把事做到头」/后果「把价值说成失去」/竞争「反向定义」/换维「换个维度重新做」/实效「只对结果负责」） |
| `_HOOK_LUX` | 高奢克制版 6 句（克制即奢侈/不留余地/稀缺即价值/定义自己的赛道/重新定义/专注即分量） |
| `MECH_TO_HOOK` | `["story","assert","imperative"]` |
| `mech_order` ×4 分支 | luxury/negative/positive/neutral 全接入 sit |

### B. 案例背书（case_reference）

- 新增 `_load_case_backing()`：懒加载+缓存读取 `data/monitor.db` `swire_events(project_key='case_study')`，按 tags 建索引（**16 个标签**）；DB 缺失降级空 dict，不阻断生成
- 新增 `_case_backing(mech)`：机制→标签映射（constraint→约束即创意/预算受限/危机转机，culture→文化转译/传统焕新，symbolize→洞察驱动/符号资产，eventify→行为设计/品牌即基础设施，participate/cocreate→用户共创/真实证据，reverse→对比，resonate→洞察驱动/仪式感，sit→行为设计/洞察驱动/跨媒介）
- `_provenance` 返回新增 `case_reference` 字段：真实案例背书（brand/title/source/url/note）

## 2. 真实产出验证（seed=20260904, premium）

```
机制分布：事件化2 / 参与式2 / 共创式1 / 情感共鸣1 / 约束即创意1 / 六模板转译1
案例背书命中：8/8

[约束即创意] 「做不到的，广州太古汇不假装」——周年，诚实就是一年一次的事
    背书: Therabody | Add Some Magic·4小时in-house | src=PRDaily
[六模板转译] 「在广州太古汇，周年从『看』变成『玩』」——都市职场的新玩法
    背书: Gatorade | 造球场·设计用户新行为 | src=抖音-233戛纳项目拆解(公开分享)
[情感共鸣] 周年嘛，广州太古汇只是把它做得刚刚好——一年一次的事，不值一提
    背书: McDonald's | Raise Your Arches·未言说的手势洞察 | src=MRS
[参与式] 「别只收藏，来广州太古汇把周年『用』一次」——一年一次的事，眼见为实
    背书: McDonald's | Cannes 2026 金狮·Camera Rolls | src=4A广告网/数英
```

## 3. 测试

- 新增 `tests/test_idea_sit_backing.py` **7 项**（SIT 注册/四分支含 sit/premium+luxury 产出/案例背书读取/DB 缺失降级/provenance 字段/机制匹配）
- 相关回归：idea_generator 18 + internal_browser 10 + 新 7 = **36 项通过**
- 全量回归 **reg67 EXIT=0**（`-m "not online" --ignore=tests/test_browser_e2e.py -k "not alembic"`）

## 4. 提交

- ZBC：`idea_generator.py` + `tests/test_idea_sit_backing.py` + 本 Evidence
- OSAI：SIT 六模板研究落地记录（ADOPT → DONE）

## 5. 说明

- 案例背书引用的是上一轮入库的 9 个公开可查证案例（Evidence 09），非编造
- 机制新增不删除/不改变既有 8 机制行为（最小增量）；DB 不可用时创意引擎照常生成（背书降级为空）

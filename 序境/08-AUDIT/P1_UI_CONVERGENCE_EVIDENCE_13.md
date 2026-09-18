# 序境 Evidence 13｜创意 API 接美奢画像 + 营销节点×圈层联动 + 国际 4A 案例库扩充

- 日期：2026-09-04
- 归属：序境-Core（Z-Brand-Core）`app.py` / `scripts/idea_generator.py` / `data/monitor.db`
- 上游研究：OSAI `RESEARCH_2026-09-C-CONSTRAINT.md` §九 + 2026 戛纳 73 届（公开可查证）

## 一、创意 API 接美奢画像 / 约束感知 / 预算档

`/api/creative/ideas` 新增入参：
- `profile`：美奢人群画像（B站×凯度 7 类）→ provenance `luxe_profile`
- `constraint_type`：约束类型（预算/同质化/媒介/信任…）→ SIT 转译感知 `sit_translation`
- `budget`：预算档 low/mid/high → BUDGETS 生成

## 二、营销节点 × 圈层联动

新建 `marketing_nodes` 表（10 节点：中秋/国庆/双11/圣诞/跨年/白色情人节/春节/清明/小满/冬至，含节日/节气/节点分类、地区、建议圈层）。
创意引擎 `_node_circles(hotspot)`：读节点表按名匹配 → provenance 新增 `node_circles`。
实测：中秋节→新中式国潮/母婴家庭/高奢小众；双十一→都市高净值/夜生活/年轻潮流；跨年→夜生活/Z世代/疗愈系。

## 三、国际 4A 案例库扩充（case_study 16 → 22）

入库 2026 戛纳 73 届国际获奖案例 6 条（公开可查证）：
- Heineken "Could Have Been a Heineken"（Social&Creator GP，LePub/WhatsApp）
- AXA "Three Words"（Creative Effectiveness GP，Publicis Conseil）
- Hyundai "Coquí Alarmed"（Audio GP，BBDO）
- KitKat "The KitKat Heist"（PR GP，Burson）
- adidas "Supernova Adaptive"（Innovation GP，TBWA）
- Mercado Livre 104米草坪条形码（场域即媒体）

## 四、真实产出验证（seed=9，中秋节×新中式×预算约束）

| 机制 | 国际案例背书 | 节点联动 | 约束转译 |
|---|---|---|---|
| 事件化 | Mercado Livre 草坪条形码 | 中秋节→新中式/母婴/高奢 | - |
| 参与式/共创式 | adidas Supernova | 同上 | - |
| 约束即创意 | Therabody 4小时拍摄 | 同上 | - |
| 六模板转译 | Mercado Livre | 同上 | 极端（预算） |

## 五、测试

- `tests/test_idea_sit_backing.py` 21 项（+4 新：国际背书/节点联动/provenance 节点/生产闭环）
- 相关回归 exit=0

## 六、结论

- 三项落地 ADOPT→DONE；案例库 22 条（9 行业案例 + 7 新圈层 + 6 国际 4A）
- 无假数据：全部来自公开可查证来源
- 未改动 Zero Sequence / 采集安全 / 权限边界

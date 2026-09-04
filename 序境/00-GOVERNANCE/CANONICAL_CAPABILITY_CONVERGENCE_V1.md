# Canonical Capability Convergence V1｜长期研发总指令

- **类型**：GOVERNANCE / 长期 Contract（Zero Sequence 兼容，不修改产品 Truth）
- **日期**：2026-09-04
- **状态**：ACTIVE（长期有效，直到明确暂停或修改）
- **适用范围**：序境双子库（序境-Core / ZBC + 序境-Intelligence / OSAI）全部研发
- **关联**：UDIP V1.0（Unified Data Intelligence Pipeline）为数据管线收敛的子集；本指令为 Capability 级总纲

## 一、总目标

在不改变既定产品定义、产品架构、功能模块、用户角色、业务边界、品牌标准、安全红线及既有正确业务口径的前提下，对全产品做 **Canonical Capability 渐进式收敛**。

核心：

```
现有产品 Truth 不变
→ 审计现有实现
→ 发现重复计算/重复数据/重复指标/重复视觉逻辑/重复 AI 逻辑
→ 建立或复用 Canonical Data / Canonical Function / Canonical Metric
→ 旧新双跑
→ Diff / Oracle 验证
→ Regression
→ E2E
→ 生产验证
→ 新实现晋升为 Canonical
→ 旧实现标记 LEGACY
→ 确认无依赖后删除
```

最终目标不是 Function Everywhere，而是 **Canonical Capability Everywhere**。

## 二、总架构

```
External Source
→ Collection Runtime
→ Raw / Evidence
→ Validate
→ Normalize
→ Canonical Data
→ Canonical Function
→ Canonical Metric
→ Truth Surface / View Model
→ UI / Table / Visualization / Report / Export / AI
```

Collection Runtime 不与纯函数层混淆。浏览器、Session、Cookie、Rate Limit、Retry、Cooldown、Heartbeat、Recovery、平台风控等仍属于 Runtime。

## 三、绝对防爆规则（10 条）

1. 一个业务事实只能有一个 Canonical Source。
2. 一个业务计算只能有一个 Canonical Function。
3. 一个业务指标含义只能有一个 Canonical Metric。
4. UI 不得重新实现业务计算。
5. Report 不得重新定义指标。
6. Export 不得重新计算业务真相。
7. AI 不得重新定义生产指标。
8. 不得为了不同消费者复制同一业务函数。
9. 不得出现 `_for_ai` / `_for_dashboard` / `*_for_report` 等仅因消费者不同而产生的重复业务计算。
10. 新代码开发前必须进行 Capability Discovery / Reference Scan。

## 四、旧功能处理原则

任何旧实现必须先分类：`KEEP / MERGE / REPLACE / LEGACY / DELETE`。禁止凭感觉删除。

- 旧实现与新 Canonical Function 数学等价、性能合理且无实际维护风险 → **KEEP**，并记录原因。
- 新旧逻辑不同 → 不得自行猜测，必须判断：
  - A. 旧逻辑正确
  - B. 新逻辑正确
  - C. 两者分别对应不同业务含义
  - D. 数据质量问题
  - E. 需要融合
  - 只有完成判断后才能继续。

## 五、替换协议（DUAL RUN）

```
OLD → NEW → DUAL RUN → DIFF/ORACLE → CONTRACT TEST → REGRESSION
→ E2E → PRODUCTION VERIFICATION → PROMOTE → LEGACY
→ IMPACT SCAN → DELETE OLD
```

任何关键 Gate 失败 → **STOP PROMOTION**。不得为了"跑绿"修改测试来掩盖真实差异。

## 六、最优计算路径（优先级）

1. 已有 Canonical Data → 直接读取。
2. 已有 Canonical Function → 直接复用。
3. 已有 Canonical Metric → 直接引用。
4. 可增量计算 → 不做无意义全量计算。
5. 可安全缓存 → 缓存。
6. 无依赖任务 → 并行。
7. 能用确定性函数 → 不调用 AI。
8. 只有需要理解、推理、比较、预测、建议时才调用 AI。

减少：重复采集 / 重复计算 / 重复 AI / 重复 SQL / 重复状态 / 重复 UI 逻辑。

## 七、UI / 动态视觉

```
Canonical Data → Function → Metric → View Model / State → Visualization → UI
```

UI 负责展示、交互、筛选、排序、动画、状态表达。UI 不负责建立第二套业务 Truth。所有动态数字、图表、趋势、排名、状态、健康度、分层等必须优先来自 Canonical Metric / View Model。

## 八、AI

```
Permission / Policy → Canonical Data / Metric / Evidence → AI Reasoning
→ Suggestion / Explanation → Human Gate（需要时）→ Action
```

AI 可以读取、理解、解释、比较、推理、预测、建议。AI 不得：偷偷建立新指标、修改 Canonical Truth、绕过权限、绕过安全 Gate、绕过人工审批、直接把研究结果变成生产事实。

## 九、双子库职责

- **Production Repository（序境-Core / ZBC）**：保存生产 Truth、Canonical Data / Function / Metric、产品实现、测试、Runtime、Lineage。
- **Intelligence Repository（序境-Intelligence / OSAI）**：负责研究、实验、评估、Benchmark、方法验证、AI 能力研究。

研究成果进入生产必须经过：Research → Evaluation → Contract → Production Validation → Canonical Registration → Safe Migration。Intelligence 不得建立第二套生产指标口径。

## 十、数据采集

采集系统继续保留既定平台适配、安全、登录、Session、Cookie、风控、限流、Heartbeat、Recovery。采集结果必须 `Raw → Evidence → Validate → Normalize → Canonical Data`。采集脚本不得直接制造多个业务统计口径。

## 十一、Lineage

所有重要 Canonical Capability 必须逐步记录：Function ID / Version / Input / Output / Source / Evidence / Run / Dependencies / Consumers / Tests / Performance / Status / Replacement / Lineage。

最终能从"一个 UI 数字"追溯到：View Model → Metric → Function → Canonical Data → Evidence → Collection Run → External Source。

## 十二、安全与稳定

任何替换不得降低：权限控制、安全边界、数据隔离、品牌隔离、异常处理、错误恢复、采集稳定性、AI Gate、人工审批、回滚能力。新增能力必须具备可回滚路径。

## 十三、研发加速原则

不以"增加代码量"获得速度，而以 `Reuse + Canonical Capability + Incremental Computation + Caching + Parallelism + Automated Validation` 获得速度。

新需求首先检查：是否已有 Data / Function / Metric / View Model / Visualization / AI Tool / Test？有则复用。

## 十四、最终执行顺序（十阶段）

1. 全仓审计。
2. 建立 Capability Registry / Reference Scan。
3. 逐项识别重复 Data / Function / Metric / UI Calculation / AI Calculation。
4. 按 WRAP → VERIFY → PROMOTE → LEGACY → DELETE 渐进迁移。
5. 补齐 Contract / Regression / E2E / Lineage / Observability。
6. 验证 KOS、采集、报告、风险、Campaign、动态可视化、Export、AI 等所有已有产品表面。
7. Cross-Surface Consistency Test。
8. 真实生产路径验证。
9. 性能、稳定性、异常恢复及回滚验证。
10. 只在全部 Gate 达标后清理确认无用的 Legacy 实现。

## 十五、最终验收标准

产品功能不被破坏 / 既定业务口径不被无意改变 / 新旧结果已验证 / Canonical Data / Function / Metric 明确 / UI 无第二套业务计算 / Report 无第二套业务计算 / AI 不建立第二套 Truth / 重复实现完成分类 / 无用 Legacy 完成安全删除 / Contract PASS / Regression PASS / E2E PASS / Production Verification PASS / Lineage 可追踪 / 权限安全 Gate 正常 / 异常可恢复 / 可回滚 / 不新增重复计算路径。

## 十六、最重要的一条

**不要为了执行这套规范而重写已经正确工作的代码。**

只有当新实现经过验证，并且能够证明更统一、更可复用、更可测试、更可追踪、更稳定或更高效，才允许替换。否则 **KEEP**。

本指令长期有效，直到明确暂停或修改。

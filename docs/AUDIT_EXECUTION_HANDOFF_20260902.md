# 下一轮双子库审计执行交接｜采集、导入、统一术语与资源闭环

状态：AUDIT_REQUIRED / NEXT_IMPLEMENTATION_CYCLE
日期：2026-09-02

## 1. 必须执行的全采集审计

逐项盘点并核验：小红书 XHS、微博 Weibo、哔哩哔哩 Bilibili、抖音 Douyin、知乎 Zhihu、Web/新闻/公开网页、热点/Topic/Trend Discovery、品牌/竞品情报、外部案例/研究资料、用户行为信号。

每个来源必须核对：采集对象、入口、Collector、API、DB、Session、Scheduler、最近成功时间、成功/失败率、数据质量、去重、主体过滤、下游消费者、状态、重复建设、迁移/合并建议和 Runtime Evidence。

“代码文件存在”不得作为“模块完成”的证据。

## 2. 外部导入 Ingestion

必须实现统一导入规范：

- 普通文件：单次最多10个，总大小≤500MB。
- 图片/视频：单次最多20个，总大小≤500MB。
- 批量媒体导入：单次最多30个图片/视频，总大小≤500MB；下一轮审计必须解决20与30两个入口的语义是否统一，最终UI/API/Runtime不得冲突。
- 不支持直接提交文件夹；允许浏览文件夹并选择文件，但不得绕过数量/容量限制。
- 支持系统内直接输入文案、粘贴文案/结构化内容，以及在对应能力允许时输入URL。

统一经过：Ingestion → Validation → Normalization → Provenance → Evidence/Resource。

## 3. 统一资源层

学习资料、真实案例、研究资料、文件、热点研究和内容案例统一归入 Zachary Unified Resource Library。

ZBC 不建立平行知识真相源；需要学习/参考时由内置 Zachary 统一调用。

## 4. 双向成长

Resource Library → Zachary → ZBC生产 → 用户行为/结果/Evidence → 脱敏/评测 → Learning Signal → Zachary/Resource Library。

不得让生产结果直接改写ZBC核心规则。

## 5. 千人千篇

用户级 Style Profile 仅可影响表达：语气、节奏、长度、情绪浓度、标题、结构、Emoji、留白、词汇密度、叙事视角。

禁止改变事实、字段语义、业务规则、主体过滤、风险定义/阈值、权限、安全策略、DB约束、Runtime、Evidence或产品架构。

原则：千人千篇，只改变表达，不改变物理性质。

## 6. 全系统术语标准化

统一枚举：

- 小红书（XHS） → `xhs`
- 微博（Weibo） → `weibo`
- 哔哩哔哩（Bilibili） → `bilibili`
- 抖音（Douyin） → `douyin`
- 知乎（Zhihu） → `zhihu`
- Web（公开网页） → `web`

必须扫描 UI/API/DB/配置/Prompt/日志/文档/Collector/Adapter/Scheduler/Resource metadata，消除同一概念的多套命名。

## 7. Zachary Context Isolation

每次调用必须携带明确的 `product_context` / `tenant_context` / `task_context`，防止不同产品功能、数据语义、业务规则、权限和架构串线。

Resource 可以共享；Product Truth 不共享。

## 8. 下一轮施工验收

必须按：

Inventory → Architecture mapping → Implementation → Unit tests → Integration tests → Runtime tests → Import boundary tests → Terminology scan → Context isolation tests → Evidence → 双子库交叉审计 → Release Gate

执行。

没有 Evidence 的项目不得标记完成。

## 9. 最终链路

External Platforms / Web / Files / Text / User Signals
→ Ingestion
→ Validation
→ Normalization
→ Provenance
→ Evidence / Resource
→ Zachary
→ ZBC Production
→ User Behavior / Result
→ Evaluation
→ Learning Signal
→ Zachary Evolution

硬边界：

`Resource ≠ Product Truth`

`Learning ≠ Permission`

`Style ≠ Business Rule`

`Recommendation ≠ Production Change`

本文件要求在下一轮代码开发周期实际执行并验证完毕后方可关闭。

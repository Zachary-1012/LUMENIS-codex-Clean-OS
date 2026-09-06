# 下一轮双子库审计执行交接｜采集、导入、统一术语与资源闭环

状态：AUDIT_REQUIRED / NEXT_IMPLEMENTATION_CYCLE
日期：2026-09-02

## 目的

下一轮双子库审计完成后，必须把本文件所列要求转化为代码开发任务，并在开发、测试、Runtime 验证和证据记录完成后才可关闭。

本文件不是“建议清单”，而是下一轮施工验收基线。

## A. 全采集模块 Inventory

逐项核对所有现有 Collector / Adapter / Importer / Parser / API / UI / DB / Scheduler：

1. 小红书 XHS
2. 微博 Weibo
3. 哔哩哔哩 Bilibili
4. 抖音 Douyin
5. 知乎 Zhihu
6. Web / 新闻 / 公开网页
7. 热点 / Topic / Trend Discovery
8. 品牌/竞品情报
9. 外部案例/研究资料
10. 用户行为信号

每个来源必须记录：

- 采集对象
- 入口
- Collector 文件
- API
- DB 表/字段
- 登录/Session 状态
- Scheduler
- 最近成功时间
- 成功率/失败率（如可测）
- 数据质量
- 去重机制
- 主体过滤/分类逻辑
- 下游消费者
- 当前状态：ACTIVE / PARTIAL / BROKEN / LEGACY / NOT_IMPLEMENTED
- 是否重复建设
- 是否需要合并
- 是否需要迁移
- Runtime Evidence

禁止以“文件存在”代替“功能完成”。

## B. 外部导入 Ingestion

必须设计统一入口，不与平台 Collector 混为一谈。

### B1 普通文件

- 单次最多 10 个文件
- 单次总大小不超过 500MB

### B2 图片/视频上传

- 单次最多 20 个
- 单次总大小不超过 500MB

### B3 批量媒体导入

- 单次最多 30 个图片/视频文件
- 单次总大小不超过 500MB
- 下一轮审计必须确认该入口与“20个媒体上传入口”的产品语义是否应统一；UI/API/Runtime 最终只能存在一套明确规则，禁止冲突。

### B4 文件夹

- 不接受“文件夹”作为导入对象
- 可以浏览文件夹并选择文件
- 文件选择后仍必须经过数量和容量校验
- 禁止通过文件夹绕过限制

### B5 文本输入

支持：

- 系统内直接输入文案
- 粘贴文案
- 粘贴结构化内容
- 粘贴 URL/外部内容地址（如对应入口支持）

最终统一进入 Ingestion → Validation → Normalization → Provenance → Resource/Evidence 流程。

## C. 资源统一

学习资料、真实案例、研究资料、文件、热点研究、内容案例等统一进入 Zachary Unified Resource Library。

不得在 ZBC 内部建立第二套平行知识真相源。

Zachary 是统一智能调用入口。

## D. 双向成长

Resource Library → Zachary → ZBC生产 → 用户行为/结果/Evidence → 脱敏/评测 → Learning Signal → Zachary/Resource Library。

生产结果不得直接改写核心规则。

## E. 千人千篇

允许用户级 Style Profile 影响：

- 语气
- 节奏
- 长度
- 情绪浓度
- 标题偏好
- 结构偏好
- Emoji 偏好
- 留白程度
- 词汇密度
- 叙事视角

禁止影响：

- 事实
- 数据字段语义
- 核心业务规则
- 主体过滤
- 风险定义与阈值
- 权限
- 安全策略
- 数据库约束
- Runtime 行为
- Evidence
- 产品架构

原则：千人千篇，只改变表达，不改变物理性质。

## F. 平台与术语标准化

全系统统一标准名称和枚举：

- 小红书（XHS） → `xhs`
- 微博（Weibo） → `weibo`
- 哔哩哔哩（Bilibili） → `bilibili`
- 抖音（Douyin） → `douyin`
- 知乎（Zhihu） → `zhihu`
- Web（公开网页） → `web`

下一轮必须扫描并统一：

UI / API / DB / 配置 / Prompt / 日志 / 文档 / Collector / Adapter / Scheduler / Resource metadata。

禁止同一概念出现多个系统真相名称。

## G. Context Isolation

Zachary 为通用能力，但每次调用必须具备明确上下文：

`product_context` / `tenant_context` / `task_context`

必须防止：

- 不同产品功能串线
- 不同产品数据库语义串线
- 不同产品业务规则串线
- 不同产品权限串线
- 一个产品的学习资料被误当作另一个产品的生产规则

Resource 可以共享；Product Truth 不共享。

## H. 验收顺序

下一轮施工不得只做静态代码修改，必须：

1. Inventory
2. Architecture mapping
3. Implementation
4. Unit tests
5. Integration tests
6. Runtime test
7. Import boundary tests
8. Terminology consistency scan
9. Context isolation tests
10. Evidence recording
11. 双子库交叉审计
12. Release Gate

任何一项没有 Evidence，不得标记完成。

## I. 最终目标

建立统一链路：

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

同时保持：

Resource ≠ Product Truth
Learning ≠ Permission
Style ≠ Business Rule
Recommendation ≠ Production Change

下一轮代码开发必须执行完毕后，再关闭本交接项。

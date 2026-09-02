# ZBC｜Unified Ingestion & Terminology Standard｜2026-09-02

## Purpose

Z-Brand-Core 与内置 Zachary 必须使用统一的采集/导入、平台、资源、内容和学习术语。本文件作为下一轮双子库审计与后续实施基线。

## Unified terminology

- `Ingestion`：采集/导入总称
- `Platform Collection`：平台采集
- `Web Collection`：公开网页/新闻采集
- `File Import`：文件导入
- `Content Input`：直接内容输入
- `User Signal Collection`：用户行为信号采集
- `Resource`：统一资源对象
- `Evidence`：支撑判断的可追溯事实依据
- `Learning Signal`：经评测和边界控制后用于学习改进的信号
- `Style Profile`：只作用于表达层的用户风格偏好

## Standard platform names

展示层：

- 小红书（XHS）
- 微博（Weibo）
- 哔哩哔哩（Bilibili / B站）
- 抖音（Douyin）
- 知乎（Zhihu）
- Web（公开网页）

代码层统一枚举：

`xhs / weibo / bilibili / douyin / zhihu / web`

不得在正式 UI/API/DB/日志中混用“RED/红书”等旧称作为同义平台标识。

## External import requirements

### General files

- 单次最多 10 个文件
- 单次总大小 ≤ 500 MB

### Image/video

- 标准上传入口：单次最多 20 个图片/视频
- 单次总大小 ≤ 500 MB

### Folder browsing

不支持将“文件夹”作为导入对象，也不能用文件夹绕过文件数量限制。

允许用户浏览文件夹并选择其中的文件后导入。

### Batch media import

业务若保留独立“批量媒体导入”入口，可设为：

- 单次最多 30 个图片/视频文件
- 单次总大小 ≤ 500 MB

下一轮审计必须确认 20 与 30 的入口语义是否确实不同；若无必要，应统一为单一限制，避免 UX/API/Runtime 不一致。

## Direct text input

支持直接在系统输入文案，并提供明确的“保存/入库”动作：

`Content Input → Validation → Metadata → Resource`

支持粘贴文本、标题、Tag、URL、案例说明和研究笔记；进入资源体系时不得绕过统一元数据、来源和去重流程。

## Unified resource pipeline

```text
Ingestion
→ Validation
→ Normalization
→ Deduplication
→ Provenance
→ Evidence
→ Resource
→ Zachary Retrieval
```

## Content terminology

- `Content Case`：真实内容案例
- `Content Pattern`：从案例抽象出的可迁移内容规律
- `Template`：只有在确有模板属性时使用
- `Rule`：不可随表达层任意改变的业务规则

案例不能直接变成固定话术；Zachary 应学习 Pattern，并依据真实任务重新生成。

## Zachary / ZBC boundary

ZBC 内置 Zachary。产品需要学习资料、案例、研究或内容参考时，通过 Zachary 调用 Unified Resource Library。

```text
Resource Library
→ Zachary
→ ZBC Production
→ User Behavior / Result
→ Evaluation
→ Learning Signal
→ Zachary Evolution
```

Resource 可以跨产品参考；Product Truth、Business Rule、权限、安全和生产 Runtime 不得跨产品串线。

## Style personalization

用户行为只能用于形成 `Style Profile` / `Learning Signal`，用于表达层个性化：语气、节奏、长度、情绪浓度、结构偏好、Emoji、词汇密度、叙事视角、留白程度等。

禁止改变事实、业务规则、风险规则、权限、安全策略、数据语义、Runtime、数据库约束和 Evidence。

> 千人千篇，只改变表达方式，不改变系统物理性质。

## Audit acceptance criteria

下一轮双子库审计必须实际核对：

- 采集器平台枚举
- UI/API/DB/日志/Prompt 词条
- 文件/媒体数量限制
- 500 MB 总容量限制
- 文件夹路径是否能绕过限制
- 文本输入/粘贴/文件导入是否统一进入 Resource Pipeline
- 是否存在重复/私有知识库
- Zachary Context Isolation
- Style Profile 与生产规则隔离
- Glossary / Enum / Schema / UI Label 一致性

本文件是实施基线，不代表所有上述能力已经生产完成；完成状态必须以 Runtime Evidence、测试结果和审计记录为准。

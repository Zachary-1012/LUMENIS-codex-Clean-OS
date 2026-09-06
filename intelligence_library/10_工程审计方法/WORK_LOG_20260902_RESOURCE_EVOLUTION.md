# Work Log｜2026-09-02｜统一资源库与双向成长模型

## 本次确认

1. 学习资料、真实案例、文件、研究资料、内容模板、热点/话题资料等，不再拆成彼此独立的学习库、资料库、案例库真相源。
2. 统一为 **Zachary Unified Resource Library**，以资源类型、领域、标签、来源、证据等级、状态等进行分类治理。
3. Zachary 是统一入口：产品需要参考资料时，由 Zachary 检索、筛选、组合和回答，而不是要求用户进入某个“资料模块”查阅。
4. Z Brand Core 内置 Zachary。ZBC 生产时通过受控 Contract 获取资源与能力。
5. ZBC 的真实生产结果、用户行为、使用反馈和 Evidence，在脱敏、评测、边界检查后形成 Learning Signal，反哺 Zachary 与 Resource Library。
6. Zachary 在当前阶段主要在内部随产品成长；成熟后再作为独立通用 AI 能力对外独立使用。
7. Zachary 可以服务所有通用模块，但必须通过边界/Contract/Context Isolation 防止把不同产品的架构、业务规则和数据语义混在一起。
8. 用户行为可形成用户级 Style Profile，实现“千人千篇”，但只允许改变表达风格，不改变任何产品物理性质。

## “千人千篇”硬边界

### 可以个性化

- 语气
- 语言节奏
- 长短
- 情绪浓度
- 标题偏好
- 结构偏好
- Emoji 偏好
- 留白程度
- 词汇密度
- 叙事视角

### 不得个性化改写

- 事实
- 数据字段语义
- 核心业务规则
- 主体过滤
- 风险等级/阈值
- 权限
- 安全策略
- 数据库约束
- Runtime 行为
- Evidence
- 生产架构边界

## 内容案例能力模型

本次新增 CARE-0002：周末随手拍 / 偶然遇见的幸福。

学习目标不是复制文案，而是学习：

```text
平淡场景
→ 偶然观察
→ 轻微停留
→ 情绪自然发生
→ 留白
→ 克制收尾
```

核心内容原则：

> 少说“我是什么感觉”，多写“什么让这种感觉发生”。

案例必须作为 Resource Library 资源被 Zachary 调用，不应硬编码进具体产品模块。

## 架构闭环

```text
全网/内部资源
      ↓
Unified Resource Library
      ↓
Zachary Retrieval + Reasoning
      ↓
ZBC / 产品生产
      ↓
用户行为 + 生产结果 + Evidence
      ↓
脱敏 + Evaluation
      ↓
Learning Signal
      ↓
Zachary / Resource Library Evolution
```

## 保护原则

资源可以跨产品被“学习参考”，但产品 Context 必须隔离：

```text
Resource ≠ Product Truth
Learning ≠ Permission
Style ≠ Business Rule
Recommendation ≠ Production Change
```

任何跨产品调用都必须携带明确的 `product_context` / `tenant_context` / `task_context`，避免不同产品的功能、数据、架构和规则串线。

## Git 落地

- `resources/README.md`：统一资源库规范
- `resources/content_cases/CARE-0002-weekend-serendipity.md`：真实创作案例资源
- `Z-Brand-Core/ZACHARY_RESOURCE_ACCESS_CONTRACT.md`：ZBC ↔ Zachary 资源访问边界合同

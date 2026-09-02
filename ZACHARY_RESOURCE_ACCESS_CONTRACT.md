# Zachary Resource Access Contract

> Z Brand Core 使用 Zachary Unified Resource Library 的边界合同
>
> 生效日期：2026-09-02

## 1. 目标

Z Brand Core 内置 Zachary 能力。产品生产过程中需要学习资料、案例、研究结论、内容参考或可复用方法时，统一通过 Zachary 访问 OSAI 的 Unified Resource Library。

ZBC 不建立与 OSAI 平行的“学习库 / 资料库 / 案例库”真相源，也不复制资源内容形成第二套长期知识库。

## 2. 双向哺育

```text
Unified Resource Library
        ↓
     Zachary
        ↓
      ZBC 使用
        ↓
生产结果 / 用户行为 / 使用反馈 / Evidence
        ↓
受控评测与脱敏
        ↓
Zachary Learning Signal
        ↓
Resource Library / Zachary Evolution
```

这是一条受控学习闭环，不意味着生产系统可以自行改写 Zachary 的核心身份，也不意味着 Zachary 可以直接改写 ZBC 的生产规则。

## 3. Zachary 在 ZBC 内的角色

Zachary 是统一 AI 入口和能力层，可以：

- 检索资源
- 综合案例
- 给出内容创作参考
- 解释研究结论
- 提供策略建议
- 根据用户任务调用不同资源
- 根据历史有效结果选择更合适的表达方式

Zachary 不得：

- 修改 ZBC 核心业务真相
- 修改主体过滤
- 修改生产数据真实性
- 修改权限/安全策略
- 绕过测试与 Release Gate
- 将学习资料直接当成生产规则

## 4. 千人千篇

用户行为数据可以形成用户级 Style Profile，仅用于表达层个性化：

- 语气
- 节奏
- 长度
- 情绪浓度
- 标题偏好
- 结构偏好
- Emoji 偏好
- 留白程度
- 词汇密度

Style Profile 严禁改变：

- 数据事实
- 字段语义
- 核心业务规则
- 主体口径
- 风险定义
- 权限
- 安全策略
- 生产阈值
- 数据库约束
- Runtime 行为
- Evidence

原则：

> 千人千篇，只改变“怎么表达”，不改变“系统是什么、数据是什么、规则是什么”。

## 5. 内容案例学习

内容案例必须作为可检索资源，而不是模块硬编码模板。

Zachary 应从案例中学习：

```text
场景
→ 情绪母题
→ 观察对象
→ 叙事视角
→ 情绪触发
→ 语言节奏
→ 留白方式
→ 标题机制
→ Tag 逻辑
→ 用户反馈
```

最终输出必须根据实际需求重新生成，不得机械复制案例原文。

## 6. 资源调用优先级

```text
User Intent
→ Zachary Retrieval
→ Resource Evidence
→ Context Assembly
→ Generation
→ User Feedback
→ Evaluation
```

当资源不足时，应明确资源不足，而不是虚构案例、数据或事实。

## 7. 架构归属

- OSAI：Unified Resource Library 与 Zachary 学习/研究 Owner
- ZBC：生产使用 Owner
- Contract：两边唯一受控连接层之一
- Evidence：验证结果的事实依据

本合同不创建第三核心仓库，不恢复历史四库/三库架构。

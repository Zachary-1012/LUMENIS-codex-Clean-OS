# 双子库下一轮审计交接单｜ZBC ↔ Zachary Unified Resource

日期：2026-09-02
状态：待下一轮审计执行

## 本次确定

ZBC 内置 Zachary，Zachary 是统一 AI 入口与通用能力层。产品研发阶段通过真实生产持续哺育 Zachary；成熟后再考虑将 Zachary 独立抽离。

学习资料、真实案例、研究资料、文件、热点/话题、Benchmark、反馈等统一视为 Resource，由 Zachary 作为入口检索和调用。ZBC 不应再建立与 Resource Library 平行的长期知识真相源。

## 下一轮审计必须核对

### 1. ZBC → Zachary
- [ ] ZBC 是否通过正式 Contract 调用 Zachary
- [ ] 调用是否携带明确 product_context / tenant_context / task_context
- [ ] Zachary 是否只返回与当前任务相关的资源/能力
- [ ] 不同产品的架构、规则、数据语义是否隔离

### 2. Resource → Production
- [ ] 资源是否作为参考依据，而不是直接成为生产规则
- [ ] 内容案例是否禁止模块硬编码
- [ ] 真实案例、生成内容、研究资料是否可区分来源
- [ ] 资源版本、证据、状态是否可追踪

### 3. Production → Zachary
- [ ] 用户行为是否经过脱敏与评测
- [ ] 生产结果是否形成可验证 Evidence
- [ ] Learning Signal 是否有版本和来源
- [ ] 未评测数据是否禁止直接进入核心学习层

### 4. 千人千篇边界

允许改变：
- 语气
- 节奏
- 长度
- 情绪浓度
- 标题偏好
- 结构偏好
- Emoji
- 留白
- 词汇密度

禁止改变：
- 事实
- 数据
- 业务规则
- 主体口径
- 风险等级与阈值
- 权限
- 安全策略
- 数据库约束
- Runtime
- Evidence

### 5. 生产安全

必须证明 Zachary 无法因为学习内容而直接修改：

- ZBC 核心业务逻辑
- 数据库 schema / 数据约束
- 权限
- 安全边界
- Release Gate
- 生产阈值
- 关键 Runtime 行为

## 内容生成专项

本次 CARE-0002 是 Resource，不是 ZBC 模块模板。

下一轮需要验证 Zachary 能否从真实案例学习“情绪发生机制”，并根据具体照片、场景、季节、任务和平台重新生成，而不是复制原文。

目标：

```text
真实素材
→ 场景理解
→ Resource Retrieval
→ 情绪/叙事机制提取
→ 用户 Style Profile
→ 重新生成
→ Evaluation
→ Evidence
```

## 审计完成标准

不得以“文件存在”作为完成条件，必须进行运行时验证、边界验证、回归测试和 Evidence 留存。

只有完整证明：

```text
资源可共享
但 Product Truth 不串

能力可共享
但 Architecture 不串

风格可个性化
但 Physical Properties 不变
```

才允许标记 DONE。

## 硬原则

> 资源共享，真相隔离；能力共享，产品边界不共享。
>
> 千人千篇，只改变表达，不改变系统物理性质。

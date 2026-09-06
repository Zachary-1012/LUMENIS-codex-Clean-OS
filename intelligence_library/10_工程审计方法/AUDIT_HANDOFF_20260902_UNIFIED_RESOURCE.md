# 双子库下一轮审计交接单｜Unified Resource × Zachary × ZBC

日期：2026-09-02
状态：待下一轮审计执行

## 本次确定

Zachary 当前阶段继续作为内部 AI 学习/进化中枢，跟随产品研发成长；成熟后再单独抽离为通用 AI 产品。

学习资料、真实案例、研究资料、文件、热点/话题、Benchmark、反馈等统一视为 Resource，不再按“模块内学习库 / 资料库 / 案例库”分裂为多个真相源。

ZBC 内置 Zachary，并通过受控 Contract 调用 Resource。ZBC 生产结果、用户行为和 Evidence 经评测后形成 Learning Signal，反哺 Zachary。

## 下一轮审计必须核对

### A. 资源统一性
- [ ] 是否存在重复知识库/重复真相源
- [ ] Resource 类型、来源、证据等级、状态、版本是否可追踪
- [ ] 内容案例是否作为资源而非产品模块硬编码
- [ ] Zachary 是否能够按任务检索资源并形成有依据的回答

### B. 双向学习闭环
- [ ] Resource → Zachary → ZBC 的调用链是否真实可运行
- [ ] ZBC → Evidence → Evaluation → Learning Signal → Zachary 是否真实可运行
- [ ] 是否存在未经评测直接进入学习层的数据
- [ ] 是否存在生产结果反向污染业务真相的路径

### C. 产品隔离
- [ ] 每次 Zachary 调用是否携带 product_context / tenant_context / task_context
- [ ] 不同产品的架构、业务规则、数据库语义是否隔离
- [ ] Resource 可共享，但 Product Truth 不得串用
- [ ] Zachary 不得通过学习资料修改 ZBC 生产规则

### D. 千人千篇
只允许影响：
- [ ] 语气
- [ ] 节奏
- [ ] 长度
- [ ] 情绪浓度
- [ ] 标题/结构偏好
- [ ] Emoji / 留白 / 词汇密度

必须保持不变：
- [ ] 事实
- [ ] 数据
- [ ] 业务规则
- [ ] 风险阈值
- [ ] 权限
- [ ] 安全策略
- [ ] Runtime
- [ ] Evidence

### E. 内容 AI
- [ ] 不得固定文案模板
- [ ] 从案例中学习生成规律，而非复制句子
- [ ] 真人/真实案例与生成内容必须区分来源
- [ ] 用户行为数据用于优化表达，不得篡改事实
- [ ] 内容生成需结合真实图片、场景、季节、任务与平台语境

## 本轮已新增资源

`resources/content_cases/CARE-0002-weekend-serendipity.md`

该案例用于训练“平淡日常 → 偶然发现 → 情绪自然抬升 → 留白”的情绪向内容生成能力，不作为固定模板。

## 审计完成标准

下一轮审计不得只检查文件是否存在，必须验证：

```text
Resource
→ Retrieval
→ Context Isolation
→ Generation / Production
→ Evidence
→ Evaluation
→ Learning Signal
→ Versioned Update
```

全链路可追踪、可回归、可阻断、可恢复后，才允许将本项标记为 DONE。

## 硬原则

> 资源共享，真相隔离；能力共享，产品边界不共享。
>
> 千人千篇，只改变表达，不改变系统物理性质。

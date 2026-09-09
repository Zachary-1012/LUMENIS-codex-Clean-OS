# E. Knowledge Gap Report

## 当前纯净库相对历史知识的主要缺口

1. **UI/UX 独有历史资产多**：980 个唯一 Blob 无当前精确等价；需要提炼交互原则，但不得恢复旧视觉。
2. **AI/Agent 当前等价未闭环**：240 个无精确等价、171 个语义候选；需要围绕 Permission → Tool → Evidence → Human Approval → Trace → Evaluation 验证真实链路。
3. **Evidence/Contract 缺口**：194 个无精确等价；需要区分历史契约、当前契约和 Runtime 执行证据。
4. **Regression Memory 未完全结构化**：历史测试和事故信息已索引，但尚未全部转换为 Failure → Root Cause → Fix → Test → Invariant。
5. **Platform 时效与合规**：平台知识虽已索引，接口、Auth、采集状态和合规结论必须按当前平台真实行为复核。
6. **Korean Production Evaluation 缺失**：缺少合法评测样本、人工基线、三语渲染与语境质量的生产证据。
7. **Release 血缘仍未实现**：历史工程资料不能弥补当前缺少 manifest、双产物构建、版本标签和 canary 证据的问题。

这些是知识或验证缺口，不代表对应功能不存在；功能状态必须回到当前源码、API、数据库、Runtime、测试和真实页面判断。

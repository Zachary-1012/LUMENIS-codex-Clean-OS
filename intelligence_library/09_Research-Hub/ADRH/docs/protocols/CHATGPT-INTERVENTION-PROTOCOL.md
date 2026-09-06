# AI Intervention Development Protocol — AI 辅助研发介入流程规范

> **Protocol ID:** HUB-PROTO-AI-INTERVENE-V1
> **归属仓库:** Zachary-1012/AI-Development-Research-Hub
> **创建:** 2026-08-31 · Research R-2026-0001
> **性质:** AI 辅助研发流程治理规范（Process Governance），不是任何 AI 的权限声明
> **约束对象:** ChatGPT · 豆包 · GitHub · 自动化系统 · 人工研发流程（全部适用）

---

## 0. 基线继承与协议关系（增量，不覆盖）

本协议**继承而非替代**以下永久基线与既有协议，只允许增量增强：

- **永久基线（IMMUTABLE）：**「三方反哺、互相验证、边界不破、能力共享、责任分明。」
  来源：DDC PLATFORM_README、SICI PLATFORM_README §16、Hub `PLATFORM_BASELINE.md` §1。
- Hub `AI-COLLABORATION-PROTOCOL.md`：定义两个 AI 之间如何互相 Review、Research ID 规范——本协议引用其 Review 流程，不重复定义。
- Hub `PLATFORM_BASELINE.md`：定义 Hub 角色边界与能力流动规则——本协议遵守其全部不可变规则。
- Hub `SHADOW-LEARNING-PROTOCOL.md`：定义 Shadow 生命周期——本协议第 5 节与其对齐。
- DDC `docs/AI-INTEGRATION.md`：定义 Local AI Bridge 技术接入与读写权限——本协议不重复其 API 细节。
- DDC `docs/REPOSITORY-FACT-BASELINE.md`：定义事实优先级——本协议第 3 节与其完全对齐。
- Z-Brand `AI_POLICY.md`：定义业务分析场景的 AI 使用边界——本协议不介入业务内部政策。
- SICI `PLATFORM_README.md`：定义移动端集成基线与变更前检查——本流程与其 §6 对齐。

**如本协议与上述任何永久基线冲突，以永久基线为准，并立即标记 BLOCKED。**

---

## 1. AI 角色定位

### 1.1 ChatGPT — Architecture Review + Research + Audit + Decision Support

**负责：**
- 架构分析与架构控制
- 技术研究与行业案例调研
- 代码 Review（独立验证 SHA、文件存在性、测试结果）
- 风险识别与隐藏耦合发现
- 方案设计与决策支持
- 知识沉淀与 Learning Asset 产出

**不负责（明确禁止）：**
- 绕过工程流程直接发布
- 替代仓库 Owner 做最终归属决策
- 替代真实测试（AI 判断不是测试）
- 替代人工最终决策
- 在未读取当前仓库事实时直接给出修改指令

### 1.2 豆包 — Engineering Execution Agent

**负责：**
- 代码实现
- 测试执行（真实运行，记录可追溯结果）
- 缺陷修复
- Commit / 工程落地
- 工程落地与提交证据整理

**约束：**
- 实现前必须完成 Audit（见第 2 节），不得凭聊天记忆改代码
- 无法真实运行的测试必须标记 NOT VERIFIED，不得写成通过
- 不得伪造 Evidence、不得把模拟 E2E 写成真实 E2E

### 1.3 GitHub — 唯一事实源（Single Source of Truth）

- 当前 Commit SHA、当前代码、当前 README/Protocol/Test/Runtime 是判断的唯一事实依据
- 聊天记录、AI 记忆、计划、承诺都不是事实
- 事实优先级对齐 DDC `REPOSITORY-FACT-BASELINE.md`：
  **当前源码 / 数据库 / 运行时实测 > 平台基线 > 其他文档 > 历史聊天**

### 1.4 自动化系统（GitHub Actions / Bridge / 定时巡检）

- 只执行被授权的、可复现的确定性流程
- 只读审计默认允许；写 / Merge / Deploy 默认禁止（对齐 DDC AI-INTEGRATION 权限矩阵）
- 自动化结果同样必须产出可追溯 Evidence，不因其"自动"而豁免验证

### 1.5 人工研发流程（Human Owner）

- 拥有最终决策权、发布批准权、基线变更批准权
- 负责高风险 / Critical 操作的人工门禁（对齐 SICI §12 风险×成熟度）
- AI 提供决策支持，不代替人工承担责任

---

## 2. AI 研发介入固定流程（禁止跳阶段）

所有开发任务（Research / Code / Capability / Automation）必须按序执行：

```text
① Audit              读取当前四库事实：SHA / 代码 / README / Protocol / Test / Runtime
   ↓
② Research           分配唯一 Research ID，记录研究问题、假设、observed SHA
   ↓
③ Architecture Review  ChatGPT（或交叉方）做架构/边界/重复造轮子审查
   ↓
④ Development Plan    最小安全变更方案，明确影响范围与回滚
   ↓
⑤ Implementation      豆包按方案实现，只改被点名范围
   ↓
⑥ Test                真实运行测试；无法运行标记 NOT VERIFIED
   ↓
⑦ Evidence            收集来自测试/运行/真实数据/可追溯记录的证据
   ↓
⑧ Review              对方 AI / 人工独立 Review，记录 reviewer 与状态
   ↓
⑨ Promotion           通过全部门禁后，才允许晋级 / 进入公共能力池 / 发布
```

**硬性规则：**
- 禁止从任意阶段直接跳到 ⑨ Promotion
- ③ Architecture Review 未通过，不得进入 ⑤
- ⑥ Test 未真实通过或标记 NOT VERIFIED，不得进入 ⑨
- ⑧ Review 无任一 approved，能力不得进入 reusable（对齐 `research_record.py` 门禁）
- 阶段可回退（发现事实错误回到 ① Audit），但不可跳过

---

## 3. GitHub 事实原则

所有判断必须基于以下**当前**事实：
- 当前 Commit SHA
- 当前代码
- 当前 README
- 当前 Protocol / Baseline
- 当前 Test
- 当前 Runtime / 运行时实测

**禁止：**
- 根据聊天历史猜测当前代码
- 根据旧版本 / 旧 SHA 判断当前状态
- 未读取仓库就直接修改
- 把"计划 / 预计 / AI 认为"写成"已完成 / 已通过 / 已部署"
- 虚构 Commit SHA、测试结果、运行结果

**发现远程出现新 Commit，立即停机重读（stop-and-reread），不得基于旧状态继续操作。**

---

## 4. 四库职责边界（不扩大、不错位）

### 4.1 AI-Development-Research-Hub
**负责：** Research · Experiment · Learning · Case Library · Benchmark · Evidence Index · Capability Registry · 公共研发工具
**不是：** 生产运行环境；三个产品不依赖 Hub 运行；Hub 不成为第四方上级。

### 4.2 Development-Command-Console（DDC）
**负责：** 工程治理 · Contract · Validation · Evidence · Release · 权限门禁 · 验证运行时

### 4.3 SICI-Core
**负责：** 手机端 · 移动交互 · 设备约束 · 真实用户工作流反馈

### 4.4 Z-Brand-Core
**负责：** 业务能力 · 品牌能力 · 生产应用 · 业务/生产真相

**边界铁律：** 一个仓库验证成功，不代表另外两个自动成功；能力在目标仓库必须重新适配并验证。

---

## 5. 代码流转规则（进入公共能力池的唯一路径）

```text
Research → Experiment → Shadow → Evidence → Verified → Reusable
```

只有走完全程、证据齐全、Review 通过的能力，才允许进入 Capability Registry 的 reusable 状态，三产品再通过 Contract / Adapter 按需使用。

**禁止：**
- AI 生成代码 → 直接进入生产
- Shadow 状态下自动改变生产行为（Shadow 只读、旁路、production_unchanged）
- 三个仓库复制同一份核心实现（用 Adapter，不复制）
- 跳过 Evidence 直接宣称 Verified

---

## 6. 双 AI 协作规则

- ChatGPT 与豆包**不是上下级**，是 Research Partner + Engineering Partner。
- 双方互相 Review，独立验证关键事实，不得互相冒充签署。
- **任何 AI 输出都不能直接作为 Evidence。**

Evidence 的唯一合法来源：
1. 真实测试结果（可复跑）
2. 真实运行结果（含运行环境与 SHA）
3. 真实数据（可追溯来源）
4. 可追溯记录（GitHub commit / workflow run / artifact）

分歧必须可见、被记录，不得由一方静默统一另一方。

---

## 7. 代码隔离规则

- **禁止：** ChatGPT 临时代码 → 直接进入 Hub
- **禁止：** 未验证实验代码 → 进入三个正式产品
- 所有实验必须先落 Research Record，再进 Experiment / Shadow，产出 Evidence
- 实验代码隔离在 Hub 的 `research/` `experiments/` `data/shadow/` 区域，不污染正式 `src/` 能力
- 临时代码 / PoC 必须显式标注 `EXPERIMENTAL` 或 `NOT VERIFIED`，不得伪装成正式能力

---

## 8. 失败记录规则（失败不删除）

失败是 Learning Asset，禁止删除或隐藏。每个失败必须记录：

| 字段 | 内容 |
|---|---|
| 原因 | 失败的根本原因（不是表象） |
| 环境 | 运行环境、版本、Commit SHA、依赖 |
| 尝试方案 | 试过哪些路径、各自结果 |
| 结果 | 实际报错 / 实际输出（保留原始证据） |
| 后续建议 | 下次如何避免 / 换什么通道 |

- WARN / BLOCKED / FAIL 不得改写为 PASS
- 失败记录进入 Learning，后续任务先读历史 Failure Record，不重复踩坑

---

## 9. Review 机制

每个重要 Research / Capability 必须可追踪三类 reviewer：
- **ChatGPT Review**（架构 / 研究 / 审计）
- **Doubao Review**（工程执行 / 测试自审与交叉审）
- **Human Review**（最终决策 / 高风险门禁）

Review 记录字段：`researcher` · `reviewer` · `reviewer_type` · `review_time` · `opinion` · `review_status`。

**Review 状态（权威枚举，R-2026-0002 统一）：**

| 状态 | 含义 |
|---|---|
| `pending` | 等待 Review |
| `approved` | 通过，可进入下一阶段 |
| `changes_requested` | 要求修改 / 暂存，修改后重新提交 Review（比 hold 更明确、更贴近实际 Review 工作流） |
| `rejected` | 驳回，记录理由 |

**规则：**
- 无任一 `approved` 的 Research 不得进入 reusable
- `changes_requested` 不等于 `approved`，不得据其晋级
- Review 意见必须具体，不得只写"同意/不同意"
- Review 方必须独立核对 SHA、文件存在性、测试结果，不得仅凭对方陈述签字

> 枚举对齐记录（R-2026-0002，ChatGPT 对 R-2026-0001 APPROVED 后执行）：Review 状态统一为 `pending / approved / changes_requested / rejected`，`src/contracts/research_record.py` 的 `REVIEW_STATUSES` 即此枚举，并由测试锁定。注意区分：研究记录**生命周期**状态机 `STATUSES` 中的 `hold` 是另一概念（能力晋级冻结），保持不变，二者不得混用。

---

## 10. 永久工程原则（只增不减）

1. **只增不减**：基线、协议、能力、Learning 只做增量，不删除既有资产
2. **不破坏基线**：不削弱永久基线与既有协议
3. **不复制核心能力**：跨仓库用 Contract / Adapter，不复制核心实现
4. **不扩大仓库职责**：Hub 不变成生产 Runtime / 第四产品
5. **不伪造验证**：不把 AI 输出当 Evidence，不把模拟当真实，不把计划当完成
6. **不绕过测试**：不跳阶段，不省略真实测试
7. **不隐藏失败**：失败可见、可追溯、转化为 Learning
8. **不保存凭证**：禁止提交 token / password / cookie / secret / API key

---

## 11. 协议生效与引用

- 本协议自提交起生效，后续所有新的 Research / Code / Capability / Automation **默认先经过本流程**。
- 本协议是流程治理层；具体技术权限以 DDC AI-INTEGRATION 为准，具体业务边界以 Z-Brand/SICI 基线为准，具体协作记录格式以 Hub AI-COLLABORATION-PROTOCOL 与 `research_record.py` 为准。
- 本协议自身的修订同样走第 2 节流程，且只能被增强，不能被削弱。

> 三方反哺、互相验证、边界不破、能力共享、责任分明。

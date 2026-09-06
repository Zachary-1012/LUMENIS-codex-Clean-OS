# AI↔AI 实时交接与 GitHub 推送协议 · R-2026-0002

> **AI=CHATGPT · Protocol Addendum · 2026-08-31**
> 目的：把 ChatGPT ↔ 豆包的研发交接从“聊天传递”升级为 GitHub 可追溯事实链。双方完成一个工作单元后，必须先整理日志、提交并推送，再把下一步明确留给对方。

## 1. 永久规则

1. **GitHub 是双方交接的唯一事实源。** 聊天消息不是任务完成证据。
2. **干完一个工作单元立即整理并推送**：不得等到一天结束、额度耗尽或多项任务堆积后再统一推送。
3. 每次推送必须包含：当前 SHA、Research ID、AI 身份、实际动作、真实测试/Evidence、风险分类、生命周期、下一方指令。
4. **AI 身份严格区分**：ChatGPT 使用 `AI=CHATGPT`；豆包使用 `AI=DOUBAO`；不得代替对方署名。
5. 推送前必须确认变更范围；不得把无关修改混入同一任务。
6. 推送后必须重新读取远程状态，确认 commit 已存在且内容与本地意图一致。
7. 失败、BLOCKED、NOT VERIFIED 同样必须记录并推送；不得因为失败而不留日志。
8. 不允许为了产生 Commit 而制造无意义修改；没有实际增量时，只记录必要的审计/研究结论。
9. 不得删除或覆盖历史 Evidence / Failure Record；新信息采用增量记录。
10. 永远遵守三方永久基线：**三方反哺、互相验证、边界不破、能力共享、责任分明。**

## 2. 标准闭环

```text
读取当前四库事实
      ↓
Audit / Research / Review
      ↓
执行最小工作单元
      ↓
真实 Test / Evidence
      ↓
整理本轮日志
      ↓
COMMIT（明确 AI 身份）
      ↓
PUSH GitHub
      ↓
REMOTE VERIFY
      ↓
留下 NEXT FOR <对方>
      ↓
对方读取最新 SHA并独立复核
```

**核心原则：先形成可追溯事实，再交接；不能先在聊天里宣布“完成”，再补 Git。**

## 3. 豆包完成任务后的固定动作

每个巡检/开发/修复/研究工作单元结束时，豆包必须按顺序执行：

1. 整理本轮日志与 Evidence。
2. 写明实际测试命令及实际结果；不能运行则写 `NOT VERIFIED`。
3. 写明四库观察 SHA（至少涉及本轮任务的仓库）。
4. 标记 `P0/P1/P2/INFO` + `NEW/REGRESSION/UNCHANGED/RESOLVED/DEFERRED`。
5. Commit，正文包含 `AI=DOUBAO`。
6. **立即 Push，不等待下一轮。**
7. 重新读取远程 HEAD / commit，确认推送成功。
8. 最后一段固定使用：

```text
NEXT FOR CHATGPT:
- <需要 ChatGPT 独立验证的事实>
- <需要 ChatGPT 关注的风险/疑点>
- <如需开发，给出最小下一步动作>
```

## 4. ChatGPT 完成任务后的固定动作

ChatGPT 同样必须遵守完全对称的交接规则：

1. 开始前重新读取四库当前 SHA、基线、协议和最近双方 Handoff。
2. 独立验证豆包上一轮的 Evidence，不把豆包陈述直接当作事实。
3. 完成自己的 Research / Audit / Architecture Review / 开发工作单元。
4. 有实际变更时立即整理日志并 Commit / Push；无实际变更则留下审计记录，不制造代码。
5. Commit 正文必须包含 `AI=CHATGPT`。
6. Push 后重新读取远程 HEAD / commit，完成 Remote Verify。
7. 最后一段固定使用：

```text
NEXT FOR DOUBAO:
- <需要豆包独立验证的事实>
- <下一轮最小工程动作>
- <测试/运行 Evidence 要求>
```

## 5. 双方不得做的事

- 不得把自己的判断写成对方已经确认。
- 不得使用对方 AI 身份提交。
- 不得依赖聊天记录作为唯一交接渠道。
- 不得基于旧 SHA 继续修改；发现远程新 Commit 必须 Stop-and-Reread。
- 不得自动替对方完成其 Review / Approval。
- 不得跳过真实 Test / Evidence。
- 不得因额度不足而把未完成任务伪装成完成。

## 6. 额度耗尽 / 中断恢复

如果任一 AI 因额度、网络、运行环境或其他原因中断：

```text
中断前最后一个已推送 Commit = 最后事实边界
                         ↓
恢复后读取远程 HEAD
                         ↓
读取最近 Handoff / 日志
                         ↓
确认未完成工作单元
                         ↓
从最后事实边界继续
```

**不得依赖中断前的聊天上下文恢复任务，不得重复已经有 Evidence 的工作。**

## 7. Commit 标准模板

```text
Research ID: R-2026-0002
AI=DOUBAO | AI=CHATGPT
Work unit: <本轮工作单元>
Observed SHAs: <相关仓库 SHA>
Changes: <实际变更>
Tests: <实际测试命令与结果>
Evidence: <路径 / workflow / artifact>
Classification: <P0/P1/P2/INFO>
Lifecycle: <NEW/REGRESSION/UNCHANGED/RESOLVED/DEFERRED>
Remote verify: PASS | NOT VERIFIED
NEXT FOR <OTHER AI>: <明确、最小、可验证的下一步>
```

## 8. 与现有协议的关系

本文件是 `CHATGPT-INTERVENTION-PROTOCOL.md`、`AI-COLLABORATION-PROTOCOL.md`、`PLATFORM_BASELINE.md`、`SHADOW-LEARNING-PROTOCOL.md` 的**操作级增量补充**，不覆盖、不削弱、不改变其规则。

它只把一个长期要求具体化为可执行门禁：

> **每次干完活 → 整理日志 → 真实 Evidence → Commit → Push → Remote Verify → 给对方留下一步指令。**

任何冲突以永久基线和更高优先级协议为准，并立即标记 `BLOCKED`。

## 9. 生效范围

适用于：

- ChatGPT ↔ 豆包交接
- 四库审计
- Research / Learning
- Code Development
- Capability / Adapter
- GitHub Actions 巡检
- Shadow Learning
- Review / Promotion 前后的证据交接

**本协议只增加可追溯性与交接效率，不增加 Hub 对三个正式产品的运行时依赖，也不改变三个产品仓库的职责边界。**

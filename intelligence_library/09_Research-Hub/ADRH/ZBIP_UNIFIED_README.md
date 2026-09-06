# ZBIP Unified Baseline

> AI-D 在 ZBIP 四库中的统一架构、Mobile Experience、Browser Research、采集研究与 Learning/Evidence 对齐基线。本文件为增量融合文档，不替换原 README，不改变生产 Runtime。

## 1. 四库定位

| 仓库 | 产品 | 中文定位 | 主责 |
|---|---|---|---|
| Z-Brand-Core | CTH-POMS / ZBMP | 广州太古汇舆情监测 / 品牌传播与市场情报平台 | 生产业务 |
| Development-Command-Console | DCC | 开发指挥控制台 | 工程治理、审计、Evidence、Release |
| SICI-Core | SICI | 手机端 AI 开发执行控制台 | Code / Run / Preview / Test / Git / Deploy |
| AI-Development-Research-Hub | AI-D | AI 开发研究与学习中枢 | Research / Experiment / Shadow / Case / Benchmark / Evidence / Capability |

AI-D 是研究与学习中枢，不是第四个生产产品，不拥有 CTH/ZBMP 生产业务、不拥有 DCC 工程控制权、不拥有 SICI Mobile Runtime。

## 2. ZBIP Mobile Design System v1

四库移动端采用统一母风格：**GPT / Codex × Apple × Linear 的设计哲学 + ZBIP 自有状态色语言**。

统一：
- 黑 / 白 / 灰
- Soft Light / Deep Dark
- Linear Icon
- Typography / Radius / Border
- 彩色小圆点状态签名
- 克制 Surface / Frosted Glass
- 低噪声、高信息密度

交互统一：Tap、Long Press、Swipe、Push、Bottom Sheet、Drawer、Pull Refresh、Infinite Scroll、Skeleton、Progressive Loading、Context Menu、Command Menu、Loading / Empty / Error / Offline / Retry。

动效统一：100–180ms 快反馈；180–280ms 普通转换；280–420ms 页面/Sheet；Spring 用于 Sheet / Toggle / Panel / Drag。

## 3. 产品信息架构

```text
CTH-POMS → 风险 / 舆情驾驶舱
ZBMP     → 品牌 / 市场情报工作台
DCC      → 研发治理控制台
SICI     → 开发执行控制台
AI-D     → 研究学习工作台
```

视觉一脉相传，信息架构因职责不同而不同。

## 4. Browser / Research Surface

```text
Research
 ↓
Hypothesis
 ↓
Browser / API / Source Research
 ↓
Evidence
 ↓
Benchmark
 ↓
Shadow
 ↓
Review
 ↓
Capability Candidate
```

Browser Research 用于合法浏览、E2E、状态检查和经授权的数据获取；不得研究或提供绕过验证码、封禁、访问限制或平台安全机制的实现。

“模拟真人浏览”只作为 UI/UX 体验研究：自然滚动、惯性、内容流、图片/视频渐进加载、正文/评论展开、状态反馈等。

## 5. RedNote / XHS Dual-Source Adapter Research

AI-D 负责研究与 Benchmark，不直接拥有生产采集器。

当前策略：

- **香港/国际 RedNote：当前主要合法采集来源。**
- **国内 XHS：暂缓几天，待账号/平台环境稳定后恢复。**
- 长期形成两个有授权来源的冗余入口。
- 不通过账号轮换、高频切换或技术手段规避平台限制。

研究范围：搜索、话题、笔记、正文、作者、发布时间、标签、点赞、收藏、评论、回复、图片、视频；比较 Browser、Approved API、第三方服务和开源 Adapter 的稳定性、数据质量、成本、合规边界与维护成本。

研究结论必须进入 Evidence / Benchmark，不能因为实验成功就直接进入生产。

## 6. Shadow Learning

统一生命周期：

`Research → Hypothesis → Candidate → Shadow → Evidence → Review → Verify → Promotion Candidate → Reusable Capability`

AI 输出不能直接成为生产事实。所有候选能力必须能说明：来源、假设、实际结果、失败原因、适用范围、NOT_VERIFIED 项。

## 7. Case / Benchmark / Capability

AI-D 重点沉淀：
- UI/UX 案例
- Agent 工程案例
- Browser Runtime 案例
- 采集 Adapter 案例
- 品牌营销案例
- 舆情传播案例
- 失败/成功工程案例
- 性能与稳定性 Benchmark
- Capability Delta

成熟能力才可以申请进入共享 Capability Registry；生产 Owner 仍由对应仓库决定。

## 8. Evidence

每个研究任务固定记录：

- Research ID
- Hypothesis
- Source / Provenance
- Baseline
- Experiment
- Observed Result
- Evidence
- Benchmark
- NOT_VERIFIED
- Recommendation
- Promotion Decision

不得把模拟 E2E 写成真实 E2E，不得把 AI 推测写成 Evidence。

## 9. 与其他三库的边界

```text
AI-D
 ↓ Research / Benchmark / Shadow
DCC
 ↓ Governance / Evidence / Release Gate
SICI
 ↓ Mobile Dev / Browser Surface
Z-Brand-Core
 ↓ Production Business
```

AI-D 提供研究结论和候选能力，不直接修改生产逻辑。

## 10. 当前优先研究

1. ZBIP Mobile Design System v1 的跨库一致性。
2. 视频参考中的 UI 视觉、层级、Linear Icon、Light/Dark、交互和 Motion。
3. Mobile Browser Surface 的可行架构。
4. RedNote/XHS Dual-Source Adapter 的稳定性与数据质量 Benchmark。
5. 真实采集 Evidence 与 Shadow Learning。
6. 将成功/失败沉淀为长期 AI 学习案例库。

## 11. 每次研究/提交固定输出

【Research ID】
【本次任务】
【Baseline】
【研究来源】
【假设】
【实际观察】
【Benchmark】
【Evidence】
【NOT_VERIFIED】
【与四库影响】
【Promotion Decision】
【Commit SHA】
【下一步】

## 12. 永久原则

- 只增不破坏已有基线。
- 不复制其他仓库核心代码。
- 不把研究实验当生产能力。
- 不把模拟 E2E 当真实 E2E。
- 不把 AI 推测当事实。
- 不越权修改生产业务。
- 研究、Shadow、Evidence、Capability 必须可追溯。

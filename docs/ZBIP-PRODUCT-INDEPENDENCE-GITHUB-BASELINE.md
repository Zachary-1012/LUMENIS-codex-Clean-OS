# ZBIP 产品独立化 + GitHub 长期运行基线（补充基线）

> 版本 v1.0｜2026-09-01｜依据用户《ZBIP 产品独立化 + GitHub 长期运行基线》指令固化。
> **性质：补充基线，不重写既有规范。** 本文只承载"产品独立化演进 + GitHub 长期定位"这一主题；命名看 `PRODUCT_NAMING_BASELINE.md`，统一架构/UI/红线看 `ZBIP_UNIFIED_CONVERGENCE.md` 与（ui/staging-foundation 分支）`ZBIP-UNIFIED-CONVERGENCE-BASELINE.md`，AI-D 研究节奏看 `AI-D-RESEARCH-ROADMAP.md`，资产事实看 `governance/consolidation-002/`。
> 权威顺序：当前源码 / 数据库 / Runtime 实测 ＞ 本基线 ＞ 历史文档 ＞ 聊天结论；冲突不自行覆盖，登记到 §7。

---

## 1. GitHub 的定位（修正：长期研发协作基础设施）

GitHub **既不是临时研究工具，也不是中央控制器 / 中央 Runtime**。它是当前阶段所有产品统一的研发协作基础设施，长期承载：

```
Repository · Branch · Commit · PR · Issue · Test · CI/CD · Deploy · Rollback · Evidence · 研发协作
```

- **长期保留**：只要满足「稳定、安全、高效、成本合理」就继续使用，没有必要更换；连接长期保持。
- **每产品一个 Repository、一条独立生命周期**：独立 Branch / 代码 / 版本 / 测试 / 部署 / Release / Evidence；**禁止把多个产品的核心 Runtime 混在同一个仓库**。
- 每个产品在自己的 GitHub 内形成独立闭环：`Development → Test → CI → Release → Deploy → Runtime`。
- GitHub 不承担产品运行时依赖：任一产品在 GitHub 不可达时，其**已部署的核心功能仍能本地运行**。

### 当前 4 仓库 / 5 身份映射（与命名基线一致）

| 身份 | 仓库 | 独立闭环现状（实测，2026-09-01） |
|---|---|---|
| CTH-POMS + ZBMP | Zachary-1012/**Z-Brand-Core** | 同仓同 Core/DB/Runtime；CTH 已生产（8201），ZBMP 在建（8301 旁路） |
| DCC | Zachary-1012/**Development-Command-Console** | 以子模块挂 `tools/development-command-console`；本轮不动 |
| SICI | Zachary-1012/**SICI-Core** | 独立仓；职责迁移研究中（见 §7 C2）；本轮不动 |
| AI-D | **独立新仓（建议名 AI-D-Core，待最终确认）** | 尚未创建远程仓；见 §7 C3 |

> 共享但不入核心 Runtime 的资产可跨仓复用：Design System、Contract、Adapter 接口、Documentation、Research、Benchmark、工程规范。

---

## 2. 产品独立化目标模型（最终每个产品可独立生存）

### 2.1 独立生存定义

> 任一产品离开其它产品后，**核心功能仍可正常运行**：可独立采集/处理自己的数据、独立判断、独立出结果、独立部署与恢复。协作是"可选增强"，不是"运行前提"。

明确禁止的核心运行时强依赖（方向 = 不得"依赖才能跑"）：

- CTH-POMS ↛ 不依赖 DCC 才能运行
- ZBMP ↛ 不依赖 AI-D 才能运行
- SICI ↛ 不依赖 DCC 才能运行
- AI-D ↛ 不依赖 SICI 才能运行
- 通用：生产产品 ↛ 不依赖研究/治理产品在线；核心业务 ↛ 不依赖云端 AI 在线（生产 AI = Ollama-only，云端默认关）

### 2.2 每个产品最终应具备的 13 项自有能力

自有 AI · 自有 Agent · 自有 Runtime · 自有配置 · 自有数据层 · 自有测试体系 · 自有 GitHub · 自有部署 · 自有监控 · 自有日志 · 自有错误恢复 · 自有 Release · 自有知识库 / 能力 Registry。

### 2.3 独立化成熟度（I 级，运行时解耦维度）

> 与 `AI-D-RESEARCH-ROADMAP.md` 的 **L0–L5（AI 自主度维度）正交**，不要混用：I 级衡量"产品离得开别人吗"，L 级衡量"AI 离得开人手吗"。

| 级别 | 名称 | 判据 | 当前位置 |
|---|---|---|---|
| I0 | 共生 | 多产品代码/数据/Runtime 混在一起，边界靠约定 | — |
| I1 | 逻辑分层 | 同仓内职责清晰、唯一 Owner、接口化、可分别测试 | **CTH/ZBMP 当前≈I1**（资产收敛②–⑥进行中） |
| I2 | 可独立部署 | 独立端口/配置/DB/日志/Browser Profile，可单独起停且互不影响 | ZBMP 8301 Staging 隔离在建 |
| I3 | 独立仓 / 独立 Release | 独立 Repo、CI/CD、回滚、Evidence、版本号 | DCC/SICI 已独立；AI-D 待建；CTH/ZBMP 长期同仓（见 §7 C1） |
| I4 | 自治运行 | 13 项自有能力齐备，离开他产品核心可运行、可自恢复、自有知识闭环 | 长期目标 |

---

## 3. 五产品 Product AI 分工矩阵（共享研究、各自拥有产品 AI）

- **现在**：AI Research / Model / Prompt / Benchmark 可由 AI-D 统一研究与沉淀，成果以"经验证的能力包 + Evidence + 接入说明"对外提供。
- **未来**：每个产品拥有自己的 Product AI，作为该产品的**增强层**嵌入自己的 Runtime，不跨产品成为运行前提。

| 产品 | 自有 Product AI 职责（只做辅助判断，不做事实 Owner） |
|---|---|
| CTH-POMS AI | 舆情理解、事件分析、风险辅助、报告辅助 |
| ZBMP AI | 品牌分析、市场分析、消费者洞察、竞品分析 |
| DCC AI | 研发审计、代码理解、风险分析、测试建议、Release 分析 |
| SICI AI | 代码生成 / 修改、运行、测试、Debug、Git 操作、Deploy（执行向） |
| AI-D AI | 研究、学习、Benchmark、Experiment、Knowledge、Capability（研究向） |

### AI 不能取代产品核心（铁律，适用于每个产品）

每个产品必须**自己保留并自己执行**：Rules、Domain Logic、Data、Runtime、Validation、Evidence、Security。

- AI 输出必须经过**该产品自己的验证**才能采用：AI 说 PASS ≠ PASS；AI 说正确 ≠ 事实；AI 改核心逻辑后**不得直接进生产**。
- 唯一上生产通道：`研究/建议 → 产品自验证（规则+数据+测试）→ Shadow 只看不写 → Evidence → DCC Release Gate → 以增强层身份接入`。
- 生产事实 Owner 永远是产品的规则 / 数据 / 统计，不是任何模型。

---

## 4. 产品间通信：只允许松耦合，禁止核心强依赖

产品之间**可以协作，但不能形成核心运行时强依赖**。只允许通过以下六种契约物通信，禁止跨库直读对方内部实现 / 直连对方数据库：

| 允许的通信方式 | 用途 |
|---|---|
| API | 明确版本、鉴权、契约的接口调用（推荐 `/api/v1` 版本化） |
| Contract | 输入/输出 schema 与状态机约定 |
| Adapter | 对方能力以薄层适配器接入，可替换、不渗透进 Core |
| Webhook | 事件通知，异步、可重试、失败不拖垮本方核心 |
| Evidence | 测试/运行证据交换，供审计与交叉验证 |
| Artifact | 报告/数据集/能力包等静态产物交换 |

---

## 5. 共享能力与退出判据

### 5.1 只共享"真正适合共享"的东西

Design Tokens · UI/交互原则 · 安全原则 · Evidence 格式 · Contract 标准 · 研究方法论 · Benchmark 方法论。

### 5.2 共享退出判据（出现任一即重新评估，必要时下沉为各产品自有）

共享导致 ① 强耦合、② 版本冲突、③ 部署困难、④ 性能下降 —— 立即重新评估，宁可复制一份稳定的小契约，也不制造一处改动、多产品被迫联动的瓶颈。

---

## 6. 当前开发策略：现在统一研发，未来独立运行（不为未来提前大拆分）

**现在不做**：为了"未来独立"而提前大规模拆仓 / 重写 / 换技术栈 / 复制 Runtime。

**现在要先做到（按序）**：
1. 先把产品做稳定（无 P0、核心链路 PASS）；
2. 先把 UI/UX 做完整、功能做完整；
3. 先建立各自的 Runtime 与独立 Staging（CTH 8201 生产 / ZBMP 8301 隔离）；
4. 先建立各自的 GitHub 与测试闭环、部署闭环、回滚闭环、Evidence；
5. 随产品成熟，按 I1→I4 **逐步**解除共享依赖，每一步都可回滚、有 Evidence。

> 最终形态：**一个品牌体系（ZBIP）+ 多个独立产品 + 各自 AI + 各自 Runtime + 各自 GitHub + 可选协作接口**。同源、同语言、可协作、但可独立生存。ZBIP 只统一产品哲学 / 品牌体系 / Design Language / 部分工程规范与协作原则，**不是中央 AI、不是中央 Runtime、不是必须依赖的核心服务**。

---

## 7. 与既有基线的增量对照 & 待拍板项（STOP，不自行改）

### 7.1 本基线相对既有文档的增量（避免重复建设）

| 主题 | 既有覆盖 | 本基线增量 |
|---|---|---|
| 五产品身份/命名 | PRODUCT_NAMING_BASELINE、ZBIP_UNIFIED_CONVERGENCE | 不重复，沿用 |
| 统一分层/UI/采集红线 | ZBIP_UNIFIED_CONVERGENCE / mother-spec | 不重复，沿用 |
| AI 是增强层 | mother-spec §6 | 扩展为**五产品 Product AI 分工矩阵** + 产品自验证铁律（§3） |
| AI-D 研究节奏 | AI-D-RESEARCH-ROADMAP（L0–L5） | 补**运行时独立化 I0–I4**（正交维度，§2.3） |
| 共享唯一 Owner | UNIFIED_CONVERGENCE §四 | 补**共享退出判据**（§5.2）与**六类松耦合通信**（§4） |
| GitHub | 仅作为 push 远端出现 | **首次明确长期基础设施定位 + 每产品独立闭环**（§1） |
| 独立化路线 | 无系统表述 | **13 项自有能力 + I0–I4 + 现在/未来策略**（§2、§6） |

### 7.2 待用户拍板（登记，不擅自动作）

- **C1 中间层 ZBP 是否保留**：mother-spec 建议保留为"业务生产平台"逻辑分组（容纳 CTH-POMS+ZBMP），成本为零；最终是否保留该层名称待确认，确认前不做全局改名。
- **C2 SICI 职责迁移**：SICI 趋向"手机端 AI 开发执行控制台"，原研究学习职能移交 AI-D；走研究路线、不立即改 SICI 代码。
- **C3 AI-D 独立仓**：确定独立建仓，建议仓名 `AI-D-Core`；远程创建方式 / 默认分支 / 协作策略待确认后执行（当前不擅自创建远程仓）。
- **BRANCH 分支合并**：`main`(06fd0c8) 与 `ui/staging-foundation`(6db9222，工作区 D:/Taikoo-staging-ui) 自 d16d000 分叉（main 独有 11、staging 独有 10）。staging 侧自带"合 main 检查项"，合并涉及生产 8201，需在 Staging 全绿后择机合并，**本轮不擅自 merge/rebase 两条业务线**。
- **PORT 8301**：本轮实测 Staging 8301 未监听（8201 生产 v5.9.9 正常、9222 CDP 正常）；需要继续 ZBMP 旁路时再按 Staging 流程启动。

---

## 8. 本轮范围声明与 Evidence

- 做：固化本补充基线（纯文档），明确独立化目标、GitHub 长期定位、Product AI 分工、解耦通信与分阶段路线。
- 不做：不改任何业务/采集/DB/UI 代码；不建远程仓；不合并 main/staging；不动 DCC/SICI；不全局改名；生产 8201 不重启、不写入。
- 实测 Evidence（2026-09-01）：本地 main = origin/main = 06fd0c8（0/0 同步）；worktree：D:/Taikoo-monitor-new[main]、D:/Taikoo-staging-ui[ui/staging-foundation]；8201 healthz = ok/v5.9.9；9222 LISTENING；8301 未监听；资产收敛②ASSET-REGISTRY 已登记 400 模块 / 全仓 363 路由 / 51 表 / 23 CSS / 22 JS / 15 依赖。

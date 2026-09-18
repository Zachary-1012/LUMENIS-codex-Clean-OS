# ZBIP Architecture Map

> Z-Brand Intelligence Platform 统一架构图。定义六层架构、四库职责、数据流和跨仓库协作方式。
>
> 版本：v1.0 · 维护者：AI-D Hub · 最后更新：2026-08-31

---

## 1. 六层统一架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 6 — UI Layer                                          │
│  页面 / 组件 / 导航 / 主题 / 交互 / 动效                     │
│  消费 Design Tokens，不直接操作数据层                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 5 — Interaction Layer                                 │
│  事件处理 / 状态管理 / 表单验证 / 导航逻辑 / 反馈            │
│  连接 UI 和 Application，不包含业务规则                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 4 — Application / Feature Layer                       │
│  功能模块 / 用例 / 工作流 / 任务合同 / 审计流程              │
│  业务用例编排，调用 Domain 层能力                             │
├─────────────────────────────────────────────────────────────┤
│  Layer 3 — Domain Layer                                      │
│  领域模型 / 业务规则 / 权限矩阵 / Evidence Schema            │
│  核心业务逻辑，不依赖具体技术实现                             │
├─────────────────────────────────────────────────────────────┤
│  Layer 2 — Data / Service Layer                              │
│  数据存储 / API 服务 / Bridge / 学习存储 / 注册表            │
│  数据访问和服务编排，不包含 UI 逻辑                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 1 — Adapter / External Layer                          │
│  GitHub API / 浏览器 / 采集器 / 第三方服务 / OS Credential   │
│  外部系统适配，所有外部交互经过此层                           │
└─────────────────────────────────────────────────────────────┘
```

### 架构规则

| 规则 | 说明 |
|---|---|
| UI 不直接操作数据库 | 必须经过 Interaction → Application → Domain → Data |
| 页面不承担复杂业务逻辑 | 业务逻辑在 Domain 层 |
| 采集器不决定品牌业务规则 | 采集只产出 Raw Evidence，业务规则在 Domain |
| AI 不决定生产事实 | AI 是增强层，生产事实由规则+数据+事件负责 |
| 研究代码不直接进入生产 Runtime | 必须经过 Research → Shadow → Evidence → Review → Promotion |
| DCC 不承担业务生产 | DCC 是工程治理工具 |
| SICI 不承担研究逻辑 | SICI 是开发执行环境 |
| AI-D 不修改生产核心 | AI-D 是研究学习中枢 |

---

## 2. 四库职责矩阵

| 能力 | DCC | SICI | AI-D | Z-Brand-Core |
|---|---|---|---|---|
| **产品定位** | 开发指挥控制台 | 手机端AI开发执行 | 研究学习中枢 | 舆情监测/品牌情报生产 |
| **核心职责** | 任务/审计/Evidence/Release/风险控制 | Code/Run/Preview/Test/Git/Deploy | Research/Experiment/Shadow/Case/Learning | 监测/采集/舆情/风险/事件/报告 |
| **UI Layer** | 控制台化，状态明确，操作精准 | 执行效率优先，编辑效率优先，路径短 | 研究工作台，实验可追踪，知识可沉淀 | 信息密度高，风险优先，状态清晰 |
| **代码语言** | Node.js + Python | HTML/CSS/JS (PWA) | Python + 文档 | Python (生产) |
| **部署方式** | 本地 Bridge + 静态前端 | PWA + 本地 | 静态文档 + 研究工具 | 生产服务器 + Docker |
| **可见性** | 私有 | 私有 | 公开（严格脱敏） | 私有 |
| **测试要求** | 自动化测试 + E2E | 手动 + 浏览器测试 | 研究验证 + 数据校验 | 生产回归 + 影子验证 |
| **发布频率** | 开发迭代快 | 开发迭代快 | 研究持续更新 | 稳定优先，发布谨慎 |

---

## 3. 共享能力 Owner 矩阵

| 共享能力 | 唯一 Owner | 其他仓库使用方式 |
|---|---|---|
| Design Tokens | AI-D | 通过 CSS 变量 / JSON 消费 |
| Icon System | AI-D | SVG 组件 / 图标字体 |
| Motion Tokens | AI-D | CSS transition / animation |
| Evidence Schema | DCC | 所有仓库产出 Evidence 必须符合此 Schema |
| Research Registry | AI-D | DCC/SICI/Z-Brand 注册研究案例 |
| Learning Store | DCC (server) | AI-D 消费学习数据，SICI 通过 Bridge 访问 |
| Shadow Learning Protocol | AI-D | 所有仓库的 Shadow 实验遵循此协议 |
| Capability Registry | AI-D | 所有可复用能力在此注册 |
| Cross-Repository Validation | DCC | 三仓库验证由 DCC 编排 |
| GitHub Audit (只读) | DCC | 前端组件可复用 |
| Local AI Bridge | DCC | SICI/AI-D 可通过 127.0.0.1:8787 接入 |
| Collection Adapter | Z-Brand-Core | 采集业务归属生产系统，其他仓库不复制 |
| Subject Filter (主体过滤) | Z-Brand-Core | 生产红线，其他仓库不得修改 |

**规则**：共享能力必须确定唯一 Owner，其他仓库通过 API / Contract / Adapter / Evidence 使用，**禁止复制核心实现**。

---

## 4. 数据流

### 4.1 开发治理数据流（DCC 主导）

```
自然语言需求
    ↓
DCC 任务合同 (Layer 4)
    ↓
AI 开发指令 (Layer 4)
    ↓
开发者 / AI Agent 执行
    ↓
GitHub Commit (Layer 1 Adapter)
    ↓
DCC GitHub 只读审计 (Layer 2)
    ↓
Evidence Bundle (Layer 3 Domain)
    ↓
测试 / E2E (Layer 4)
    ↓
验收等级 L0-L5 (Layer 3)
    ↓
Release Candidate (需人工批准)
```

### 4.2 研究学习数据流（AI-D 主导）

```
外部研究案例 / 内部工程经验
    ↓
Research Registry (AI-D Layer 2)
    ↓
Hypothesis / Experiment (AI-D Layer 4)
    ↓
Shadow Learning (AI-D Layer 3)
    ↓
Evidence (符合 DCC Evidence Schema)
    ↓
Cross-Repository Validation (DCC 编排)
    ↓
Capability Delta (DCC Layer 3)
    ↓
Promotion Candidate (5-Gate 全部通过)
    ↓
人工 Review → Approved
    ↓
反哺目标仓库 (Z-Brand / SICI / DCC)
    ↓
再次三方验证
    ↓
形成新的 Learning Case (回到 AI-D)
```

### 4.3 生产数据流（Z-Brand-Core 主导）

```
采集源 (RedNote / XHS)
    ↓
Collection Adapter (Layer 1)
    ↓
Raw Evidence (Layer 2)
    ↓
Normalize → Quality Gate → Subject Gate → Dedup (Layer 3)
    ↓
Database (Layer 2)
    ↓
aggregate_events / build_daily_report (Layer 3 生产红线)
    ↓
Dashboard / 报告 (Layer 6)
```

---

## 5. 跨仓库协作协议

### 5.1 变更传播

```
AI-D 研究产出
    ↓ (Shadow + Evidence + Review)
DCC 工程验证
    ↓ (Capability Delta + 三仓库验证)
SICI / Z-Brand 适配
    ↓ (生产回归)
正式发布
```

### 5.2 禁止事项

| 禁止 | 原因 |
|---|---|
| DCC 直接修改 Z-Brand 生产代码 | 生产红线，必须人工批准 |
| SICI 承担研究逻辑 | 职责分离 |
| AI-D 修改生产核心 | 研究不直接进生产 |
| 跨仓库复制核心实现 | 必须通过 Adapter / API / Contract |
| 研究案例直接当生产事实 | 必须经过 Shadow + Evidence + Review |
| AI 判断替代 Evidence | Evidence 是唯一事实依据 |

---

## 6. 各仓库当前架构成熟度

| 仓库 | UI Layer | Interaction | Application | Domain | Data | Adapter | 总分 |
|---|---|---|---|---|---|---|---|
| DCC | ✅ 双主题+磨砂 | ⚠️ 基础交互 | ✅ 7功能区 | ✅ Evidence+权限 | ✅ Bridge+Learning | ✅ GitHub API | 5/6 |
| SICI | ⚠️ PWA基础 | ⚠️ 待确认 | ⚠️ 升级模块 | ❌ 待确认 | ❌ 待确认 | ⚠️ 浏览器 | 2/6 |
| AI-D | ❌ 无前端 | ❌ N/A | ✅ 研究工作流 | ✅ Schema+协议 | ✅ 研究数据 | ⚠️ 工具 | 3/6 |
| Z-Brand | ⚠️ Dashboard | ✅ 生产交互 | ✅ 舆情工作流 | ✅ 生产红线 | ✅ 数据库+采集 | ✅ 采集Adapter | 5/6 |

> ✅ = 已实现 / ⚠️ = 部分实现 / ❌ = 未实现或待确认

---

*本文件由 AI-D Hub 维护，架构变更需经过 Cross-Repository Validation。*

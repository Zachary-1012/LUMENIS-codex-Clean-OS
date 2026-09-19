# AI-Development-Research-Hub

> **Zachary AI 三产品共享研发中枢 · Research / Experiment / Shadow Learning / Case Library / Benchmark / Evidence Index / Capability Registry**

**仓库：** `Zachary-1012/AI-Development-Research-Hub`  
**定位：** 三个正式产品共享的 AI 研究、实验、学习和公共开发能力中枢  
**状态：** 非生产 Runtime — 三个正式产品**不依赖 Hub 才能运行**

---

## 1. 这不是第四个产品

Hub 不是第四个产品，而是三个正式产品共享的研发能力中枢：

| 仓库 | 角色 | 职责 |
|---|---|---|
| `Zachary-1012/Z-Brand-Core` | 业务/生产真相 | 品牌业务、舆情、市场情报、生产能力 |
| `Zachary-1012/SICI-Core` | 手机端产品 | 移动交互、设备约束、真实用户工作流反馈 |
| `Zachary-1012/Development-Command-Console` | 工程控制 | 审计、权限、验证、Evidence、Release、工程学习 |
| `Zachary-1012/AI-Development-Research-Hub` | **研发中枢** | **研究、实验、Shadow Learning、案例库、基准、Evidence 索引、能力注册、公共工具** |

**Hub 不拥有生产业务逻辑，不拥有工程控制权，不拥有移动 UI。** 三个正式产品通过 Contract / Adapter 按需使用 Hub 的 reusable 能力。

---

## 2. 继承的永久基线

Hub 完整继承三方永久基线，不创建新协议覆盖它：

> **三方反哺、互相验证、边界不破、能力共享、责任分明。**
>
> Z-Brand-Core 提供业务/生产真相；DDC 提供工程控制与验证真相；SICI-Core 提供移动交互与真实使用反馈。三方通过 Contract + Evidence + Test + Learning 形成闭环，任何一方都不能成为另外两方的无边界上级。

来源：`Development-Command-Console/PLATFORM_README.md` 第18节、`SICI-Core/PLATFORM_README.md` 第16节（IMMUTABLE）。

---

## 3. 目录结构

```text
AI-Development-Research-Hub/
├── docs/                          # 研究文档、架构说明
│   └── protocols/                 # 流程治理协议（AI 研发介入流程等）
├── protocols/                     # 协议文档（持续研发政策等）
├── research/                      # 活跃研究任务（按 Research ID 组织）
├── cases/                         # 研究案例库
├── benchmarks/                    # 基准测试与评估
├── architecture/                  # 架构决策记录（ADR）
├── data/
│   ├── research/                  # 研究记录（JSONL）
│   ├── experiments/               # 实验数据
│   ├── shadow/                    # Shadow 运行记录
│   ├── evidence/                  # Evidence 索引
│   └── learning/                  # 学习成果沉淀
├── src/
│   ├── contracts/                 # 数据契约（Research Record, Capability 等）
│   ├── adapters/                  # 跨仓库适配器（DDC research_learning 等）
│   └── shared/                    # 共享工具（Capability Registry, Shadow Lifecycle）
├── tools/                         # CLI 工具
├── tests/                         # 单元测试
└── .github/workflows/             # CI：研究验证、能力晋级检查
```

---

## 4. 核心协议文档

| 文档 | 内容 |
|---|---|
| `PLATFORM_BASELINE.md` | Hub 平台基线、边界、与三仓库关系 |
| `AI-COLLABORATION-PROTOCOL.md` | ChatGPT ↔ 豆包互相 Review 协议、Research ID 规范 |
| `RESEARCH-LEARNING-SCHEMA.md` | 研究记录 Schema（兼容 DDC research_learning.v1） |
| `SHADOW-LEARNING-PROTOCOL.md` | Shadow Learning 固定生命周期与禁止项 |
| `THREE-REPOSITORY-VALIDATION.md` | 三方验证矩阵：Z-Brand / DDC / SICI 各自验证维度 |
| `CAPABILITY-REGISTRY.md` | 能力注册表规范、reusable 晋级标准 |
| `CASE-LIBRARY.md` | 案例库规范、研究主题清单、质量标准 |
| `docs/protocols/CHATGPT-INTERVENTION-PROTOCOL.md` | **AI 辅助研发流程规范（R-2026-0001，ChatGPT APPROVED）**：约束 ChatGPT/豆包/GitHub/自动化/人工的九阶段固定流程与双 AI 互相 Review 机制 |
| `protocols/CONTINUOUS-RESEARCH-AND-DEVELOPMENT-POLICY.md` | 永久持续研发政策与定时巡检/交接基线（commit b499805） |

> 协议权威顺序：永久基线（IMMUTABLE）> 平台/协作协议 > 流程治理协议；任何新 Research / Code / Capability / Automation 必须先经过 `docs/protocols/CHATGPT-INTERVENTION-PROTOCOL.md` 第 2 节九阶段流程（Audit → Research → Architecture Review → Development Plan → Implementation → Test → Evidence → Review → Promotion），禁止跳阶段。

---

## 5. 已复用的现有能力（不重复实现）

Hub **不重复实现** DDC 已有的研究学习基础设施，而是通过 Adapter 复用：

| DDC 已有能力 | Hub 使用方式 |
|---|---|
| `tools/research_learning.py` | `src/adapters/ddc_research_adapter.py` 兼容其 JSONL schema |
| `docs/RESEARCH-LEARNING-DATABASE.md` | `RESEARCH-LEARNING-SCHEMA.md` 引用并扩展 |
| `tools/learning_cycle.py` | Shadow bundle 构建参考其只读模式 |
| `tools/learning_promote.py` | 晋级逻辑参考其 evidence-gated 设计 |
| `tools/research_registry.py` | Benchmark 注册表分析参考其校验逻辑 |
| `tools/capability_delta.py` | CASE-2026-0012 研究其量化 before/after 增量门禁；Hub 引用门禁思想，不复制实现（DDC 为 Owner） |
| `.github/workflows/platform-five-inspections.yml` | Hub workflow 参考其只读巡检模式 |

**DDC commit 参考：** `878ebbf5546976cfb49238fd2bd5003022ae2c5b`（capability_delta 后续见 CASE-2026-0012）

---

## 6. 研究生命周期

```text
Research → Hypothesis → Candidate → Shadow → Evidence → Review → Verify → Promotion Candidate → Reusable Capability
```

**禁止：AI 判断 → 直接生产。** Shadow 状态下不得自动改变生产行为。

---

## 7. 提交标准

每次提交必须输出：
- Commit SHA
- 修改文件
- 研究来源（Research ID）
- 实现内容
- 实际测试结果
- Evidence
- 未验证项目（NOT_VERIFIED 显式标记）
- 对 Z-Brand / SICI / DDC 的影响
- 下一轮 Research ID

**不得伪造测试通过。不得把模拟 E2E 写成真实 E2E。不得把 AI 输出写成 Evidence。不得保存凭证。**

---

## 8. 永远遵守

- 只增不减
- 不破坏既有基线
- 不扩大仓库职责
- 不制造无必要复杂度
- 不复制核心代码
- 不越权
- 不伪造验证

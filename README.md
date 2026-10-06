# 序境 / LUMENIS

序境是面向商业运营与品牌市场的一个产品，当前处于**工程闭环执行阶段**，尚不能把源码存在、测试通过或 HTTP 200 等同于完整用户验收。已批准的产品体验覆盖官网、Web Workspace、Desktop App 和 Mobile Companion 四个入口，共用一套 Product Core、Canonical Data、Evidence、Permission、AI Gateway、Agent Runtime、Reporting、Evaluation 与成果版本。

仓库：`Zachary-1012/LUMENIS-codex-Clean-OS`；唯一开发/整合分支：`main`。本机标准目录为 `D:/LUMENIS_REBUILD/序/序境`。**当前状态必须由 Git、源码、Runtime、DB、测试和用户结果重新取证，不从 README、旧报告或聊天记录猜测。**

## 从这里开始

Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)。

无论是 Codex 还是人类工程师，第一次进入仓库都按这个顺序阅读：

```text
AGENTS.md
→ 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md
→ 00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md
→ 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
→ 当前 Owner、合同、源码、Runtime/DB 和真实结果
```

- [`AGENTS.md`](AGENTS.md)：**唯一仓库执行路由**。决定当前谁可以执行、怎么准入、什么不能绕过。
- [CURRENT](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)：当前已经验证的实现、运行状态、缺口和最近证据。
- [Product Architecture](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)：唯一产品蓝图。
- [Source Owner Index](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)：源码 Owner、调用方、C1–C6 与 R01–R15/J1–J8/U01–U25 映射。
- [Experience Constitution](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)：唯一 UI/UX 与四端体验权威。
- [Real Delivery Overlay](00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md) 与 [Global/Context/Data Maturity](00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md)：真实任务、范围、数据成熟度、恢复和结果口径。

## 给人类工程师的产品地图

序境不是“广州太古汇舆情系统”的延续名称，也不是多个产品拼接。当前只有一个产品：**序境 / LUMENIS**。

```text
四个产品入口
Public Website
Flutter Web Workspace
Desktop App (Windows / macOS / Linux)
Mobile Companion (Android / iOS)
        │
        ▼
一个 Product Core
        │
        ├─ CTH · 商业运营 / Commerce Operations（Subject-first）
        ├─ BMP · 品牌市场 / Brand & Market（Brand/Market-first）
        ├─ Shared Capability
        │  ├─ Evidence / Reporting / Evaluation / Learning
        │  ├─ Importer / Research / Content / Artifact
        │  └─ Video / Podcast / Saved Work
        └─ SYSTEM
           ├─ Runtime / Database
           ├─ Collector / Browser / Scheduler
           ├─ Permission / Action Firewall / Effect Fence
           └─ AI Gateway / Agent Runtime / Owned AI
```

默认产品上下文是 `GLOBAL / ALL`。广州太古汇、深圳罗湖万象城、Nike、Le Labo 等是受控 Subject/BrandFocus 或验收参考对象，**不是产品默认范围**。

核心真相链：

```text
External / User Source
→ Source / Evidence
→ Canonical Data
→ Function
→ Metric / Truth
→ View Model
→ Experience / Report / Artifact / Export
→ Outcome / Evaluation / Learning
```

原始来源不能被模型分析覆盖；`UNKNOWN` 不能写成 `0`；“配置存在”“测试通过”“模型文件存在”“HTTP 200”都不能单独证明产品闭环。

## 当前执行拓扑（2026-10-06 15:40 +08）

Product Owner 已恢复批准的完整执行拓扑：

| 角色/窗口 | 当前职责 |
|---|---|
| **M · 总控** | 冻结当前真相、解决跨窗口架构/Owner/接口冲突、审查完整结果、控制整合与验收；不替代各窗口做重复实现。 |
| **F · Frontend / Experience** | 四入口前端与 Experience 实现；按唯一 Experience Constitution 落实 Flutter/Website、真实绑定、响应式、本地化、可访问性与用户操作。 |
| **C1 / W1 · Data & Collection** | Registry、来源、六主平台采集、Browser/Session、Source→Evidence→Canonical、刷新/恢复。 |
| **C2 / W2 · Owned AI & Agent** | 单一 AI Gateway、自有模型训练/推理、Agent/Skills/Memory/Evaluation/Learning；免费 GPU 优先，付费资源必须重新授权。 |
| **C3 / W3 · CTH & BMP Workflows** | 商业运营、市场/竞品/Creator/Consumer、Campaign、决策、Outcome 与业务闭环。 |
| **C4 / W4 · Pitch / Video / Podcast** | 原创提案、可编辑视频、可用播客、媒体工作台、保存/重开/恢复/导出。 |
| **C5 / W5 · Importer / Research / Shared** | 资料导入、Research、Citation、Reporting、Artifact、通知、共享偏好和版本化成果。 |
| **C6 / W6 · Integration / Runtime / Release** | 共享 API 组合、DB 变更协调、Core/Runtime/Supervisor、四端整合、CI、恢复/回滚与最终发布证据。 |

**M + F + C1–C6 现在都属于当前执行体系。** 各窗口可按真实依赖并行推进，但不能因为“窗口已恢复”就盲启：每个任务开工前仍必须核对 fresh `origin/main`、本地 dirty、Owner/调用方、Runtime、DB、Permission、Evidence 以及平台 Session/GPU 等真实前置条件。

### 当前执行器

- **Codex / Codex CLI**：当前研发执行器。每个窗口使用 Product Owner 当下手动选择的模型、推理强度和服务档位；仓库不自动分配 Sol/Luna/Astra 等模型。
- **OpenCode**：**当前搁置，不属于本轮执行路径，也不是 Codex 额度不足时的自动 fallback。** 已有安装/配置不等于获准执行；除非 Product Owner 以后明确恢复，否则任何窗口都不要把任务派给 OpenCode。
- TRAE、Apple、ChatGPT 等只在各自既有规则内作为 Experience/研究参考，不拥有序境产品架构或执行权。

## 当前状态摘要

截至 `2026-10-06 15:40 +08` 的重新取证：

- 本轮状态更新前的冻结基线为 `local HEAD == origin/main == 90192058e0cb6cce9b8d0a1d7577d5e6e4a56f50`、分歧 `0 / 0`；发布后必须重新 `git fetch` 获取新的当前HEAD，不能把这个SHA当永久基线。
- Core `:8201 /healthz` 返回 `200`，`service=lumenis-core`，Database=`ok`。
- 产品身份已收敛为 `序境 / LUMENIS`，Runtime 默认上下文为 `GLOBAL / ALL`；历史广州太古汇采集记录仍作为业务数据保留。
- Only-One 产品/Owner 方向已建立，但完整用户结果、六平台真实持续运行、C2 真实训练/Promotion/Service binding、F 批准体验的完整实现、四端真实 E2E 和 Release 仍需各责任窗口继续闭合。
- 本地仍有受保护的未提交 Importer 候选、Collector 运行状态、C1 证据、C2 训练配置与 `work/` 材料；任何窗口开工前先识别这些 dirty 的 Owner，**不得 reset/clean/覆盖**。
- 当前阶段是工程闭环执行，不得写成 `RELEASED` 或 `OPERATING`，除非对应 Product Gate、Runtime、真实用户结果和发布证据全部成立。

更细的逐能力状态始终以 [CURRENT](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md) 为准。

## 人类工程师安全开工流程

```powershell
Set-Location D:\LUMENIS_REBUILD\序\序境
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

然后：

1. 阅读 `AGENTS.md` 与 `CURRENT`，不要从 README 判断某能力已完成。
2. 用 `scripts/audit_tools/locate_capability_context.py` 定位当前能力 Owner、合同、调用方和验收路径；不要默认整仓扫描。
3. 明确你属于 M、F 或 C1–C6 中的哪一个窗口，只修改该 Owner 允许的路径。
4. 保护已有 dirty、生产 DB、Cookie/Session、用户材料和历史 Evidence。不要为了“干净”执行 `reset --hard`、`clean -fd` 或批量覆盖。
5. DB/迁移/测试优先使用隔离临时库；受保护 `monitor.db` 存在 WAL/SHM 时不得复制后冒充干净测试库。
6. 改动后运行**受影响测试 + 合法 blocking gates**，不靠删除测试或降低标准获得绿色。
7. 完成完整结果后由对应窗口交付；共享整合走 W6，M 做跨窗口审查/验收。
8. 发布后再次 `git fetch` 并证明本地 HEAD 与 `origin/main` 一致；源码、CURRENT 和必要 Evidence 在同一交付周期对齐。

## 运行入口

```powershell
Set-Location D:\LUMENIS_REBUILD\序\序境
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

Core 健康：`http://127.0.0.1:8201/healthz`。Flutter Web 入口由同一 Core 的 `/workspace` host 提供，需实际构建及配置；Desktop/Mobile 复用 Flutter 代码；`website/` 仅承载官网。参见 [App说明](app/README.md) 与 [官网说明](website/DEVELOPMENT-BRIEF.md)。

当前产品入口保持开放，不新增账号/升级墙；服务端 Permission、Action Firewall、Effect Fence 和平台会话边界始终有效。

## 执行与安全边界

- C1 可以继续真实只读采集，但必须遵守已有 Scope、Permission、Session、频率与平台规则；一个平台 Blocked 不能伪装成 ACTIVE，也不应暂停其他已满足前置的平台。
- C2 可以继续免费 GPU 训练闭环，但必须先验证真实零成本 GPU、精确 model/recipe/data hash、MODEL_TRAIN Permission、Checkpoint/Evaluation 合同；**不得自动租 GPU、充值或启用付费 fallback**。
- F 可以继续已批准 Experience 实现，但设计状态不等于 Runtime/用户验收。
- C3–C5 继续各自真实用户成果，不能用 fixture、文档、测试或 Mock 替代实际业务结果。
- C6 负责整合、Runtime/Release，不得把单模块绿色扩写成全产品绿色。
- Production DB 写入、破坏性迁移、部署/Release、付费资源和外部业务效果仍遵守 `AGENTS.md` 的精确授权边界。

## 验收语义

```text
IMPLEMENTED
→ TESTED
→ LIVE_VERIFIED
→ USER_VERIFIED
→ RELEASED
→ OPERATING
```

这些状态互不替代。`Product Gate / App Gate / Critical E2E / User Outcome` 需要各自证据；旧绿色、旧 SHA、历史报告或模型输出不能替代当前验收。

[直接修复证据](00-GOVERNANCE/evidence/round-15/DIRECT-REPAIR-20261004.md) · [批准后收敛证据](00-GOVERNANCE/evidence/round-15/APPROVED-CONVERGENCE-20261004.md)

历史 ZBC/Z-Brand-Core/CTH-POMS/ZBMP 命名、旧研究和旧运行回执只按 Canonical Naming 兼容规则保留，不得重新成为当前产品身份或执行入口。

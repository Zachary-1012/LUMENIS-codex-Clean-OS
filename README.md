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

这里的“恢复/可执行”只表示角色 **ELIGIBLE**，不是实时派工。最新 Product Owner 指令和
本地 Live Dispatch 决定各窗口是否开工。规则同步、语义校准或研究准备完成都不会自动恢复
C1–C6/F 的产品研发；不能把 README 的拓扑当作运行状态。

### 语义校准与研究采用入口

2026-10-08 增补：匿名采集路由与本地系统朗读由现有 Collector/Shared/Experience
Owner承接，状态与限制见 [CURRENT](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)。
本轮排除需登录的OpenCLI接入，原有平台授权、Skill商店和GitHub增强能力保留。
[Intelligent UI研究与职责映射](00-GOVERNANCE/evidence/round-15/INTELLIGENT-UI-ADOPTION-20261008.md)
已纳入唯一Experience规则，等待后续相应窗口执行；不因规则写入而自动开工或宣称功能完成。

产品词义以 [Product Architecture 当前语义与兼容边界](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
为准。[语义清单](00-GOVERNANCE/evidence/round-15/SEMANTIC-CALIBRATION-20261007.md)
记录当前术语、旧技术标识、实际修复与验证边界。`CTH/BMP` 是序境内的领域；
`ZBMP/zbmp/ZBC_*` 保留技术兼容，不建立第二产品，也不得直接批量替换持久化 ID。
[OpenAI Math 采用清单](00-GOVERNANCE/evidence/round-15/OPENAI-MATH-ADOPTION-20261007.md)
记录原文适用条件和实际采用点：严格域/焦点解析、状态来源分离、Provider 兼容标识、
学习记录晋升后的消费，以及相应正常结果与反例验证。C1–C6/F复用这些已发布公共边界与
证据，继续自己的真实用户成果；不重复实现或重做原文审计。研究、代码验证、实际业务验收
和模型训练准入分别记录，不能互相替代。

## 产品完整闭环职责（不可由 README 摘要缩减）

下面只是给人类工程师和 Coding Agent 的**导航摘要**。完整要求仍由 [Source Owner Index](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)、Product Architecture、Experience Constitution、R01–R15、J1–J8、U01–U25、现有研究/材料采用义务和各 Screen/Owner 合同共同约束。**任何 README、状态表、测试数量或窗口名称都不能把这些要求缩短成更小的产品。**

| 窗口 | 必须完成的完整结果 |
|---|---|
| **M · 总控** | 冻结当前线上/本地/Runtime/DB/dirty真相；解决跨窗口 Product Architecture、Owner、接口与共享写冲突；审查各窗口完整用户成果；协调 W6 统一整合、发布和回归；不替代 F/C1–C6 的实现职责，也不把局部修复冒充全产品完成。 |
| **F · Frontend / Experience** | 把所有已批准能力完整落到官网、Web Workspace、Desktop、Mobile 的真实界面和交互；完成真实 API 绑定、信息架构、屏幕状态、loading/empty/error/denied/offline/cancel/retry/recovery、保存/重开、响应式、中文/英文/韩文、本地化和可访问性。设计稿或 DESIGN_READY 不等于运行验收。 |
| **C1 / W1 · Data & Collection** | 建立并持续维护 GLOBAL/ALL、Subject/BrandFocus/关系和真实数据宇宙；对 Instagram、Facebook、微信公众号、RedNote/XHS、抖音、X 的批准路径执行真实采集、历史/增量维护、原生字段/时间/互动/评论/允许媒体、分页/续跑/去重/恢复，并进入唯一 Source→Evidence→Canonical 真相链；样本、Seed、Cookie文件或配置存在都不能冒充覆盖率。 |
| **C2 / W2 · Owned AI & Agent** | 通过唯一 SYSTEM AI Gateway 完成 LUMENIS 自有模型的真实训练、checkpoint/resume、独立 held-out Evaluation、正常业务推理、多模态理解、Agent/Skills/Memory/Context、反馈/Learning、低置信与失败恢复、受控 Promotion/Rollback；当前免费资源优先，模型文件/preflight/三步训练都不能冒充质量或部署完成。 |
| **C3 / W3 · CTH & BMP Workflows** | 完整完成商业运营与品牌市场真实工作：监测/事件/日历、消费者/媒体/趋势/风险、市场/竞品/Creator/传播、Case→Insight→Decision→Action→Outcome→Evaluation、内容/Campaign生命周期及实际效果；必须保留精确 Subject/BrandFocus、市场、时间、单位、分母、来源和不确定性。报告或提案不等于已执行结果。 |
| **C4 / W4 · Pitch / Video / Podcast** | 分别交付原创专业提案、真正可编辑且可播放的成片、完整可听可编辑的播客；覆盖真实 Brief/素材/预算约束、时间线、编辑/替换/预览/渲染、音频/字幕/章节/转录、保存/导出/重开/取消/恢复、版本和人工质量复核。三类成果各自独立验收，Demo 不能替代完整工作流。 |
| **C5 / W5 · Importer / Research / Shared** | 完成资料导入、Library/Search、精确 Citation、逐篇/逐页/逐段/逐帧/时间码研究、Reporting、Artifact、SavedWork、通知和共享偏好；所有原件、rights、source hash、父子版本、撤销/恢复可追溯。191行 manifest 不是全部语料，未读正文、未采用研究和 UNKNOWN rights 不能被写成“已吸收”。 |
| **C6 / W6 · Integration / Runtime / Release** | 把已验收 Owner 能力整合成同一 SHA 的 Core/API/DB/四端/FFmpeg/Supervisor/CI/Packaging/Recovery；协调正式 DB 变更、共享调用、启动/重启/取消/回滚、Product/App/Critical E2E 和最终 Evidence bundle；代码存在、build成功或 health=200 都不能单独写成 RELEASED/OPERATING。 |

产品最终闭环不是“所有窗口都有代码”，而是对应真实用户任务能够从**真实输入 → 有依据的结果 → 保存/修改/重开/恢复 → Outcome/Evaluation → 跨端继续使用**完整成立。

### 当前执行器

- **Codex / Codex CLI**：当前研发执行器。序境研发角色默认值为 M/F=`GPT-6 Astra / ultra`、C1–C6=`GPT-6.1 Sol / ultra`、任务 Subagent=`GPT-6 Luna / max`；机器合同见 `.codex/model-routing.toml`，Subagent 默认同时写入 Codex 原生 `[agents]` 配置。Product Owner 在任一当前窗口的手动模型、推理强度、速度/服务档位选择始终即时覆盖角色默认；显式 spawn 选择覆盖 Subagent 默认；Hook 不拥有模型选择权。M 有已分配或未闭合工作时执行，无任务时停止待命。
- **OpenCode**：**当前搁置，不属于本轮执行路径，也不是 Codex 额度不足时的自动 fallback。** 已有安装/配置不等于获准执行；除非 Product Owner 以后明确恢复，否则任何窗口都不要把任务派给 OpenCode。
- TRAE、Apple、ChatGPT 等只在各自既有规则内作为 Experience/研究参考，不拥有序境产品架构或执行权。

## 当前状态摘要（开工时必须重新取证）

README **不固化 current HEAD、Runtime、DB 行数、dirty文件清单或窗口进度**，因为这些会随每次交付变化。每次开工先执行 `git fetch origin main`、读取 `HEAD` / `origin/main` / dirty，再核 Runtime、DB、Permission、Evidence 和真实用户结果；最新逐能力事实、当前缺口和最近证据只记录在 [CURRENT](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)。

- 当前产品身份是 `序境 / LUMENIS`；默认工作宇宙是 `GLOBAL / ALL`。具体运行进程是否已加载这一版本必须现场验证。
- 当前执行拓扑是 **M 总控 + F 前端/Experience + C1–C6 六个独立交付窗口**；窗口通过准入后持续完成完整结果直到验收或真实阻塞。
- 本地工作树中的任何 dirty/untracked 都先按 Owner 识别并保护；README 不枚举或推断其完成状态，**不得 reset/clean/覆盖未知工作**。
- 当前总体阶段是工程闭环执行；只有对应 Product/App/Critical E2E、Runtime、用户结果和Release证据真实成立后，才能分别声明 `USER_VERIFIED`、`RELEASED` 或 `OPERATING`。

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

## 仓库结构

下面只列当前人类工程师最需要辨认的入口，不代表完整文件清单：

```text
00-GOVERNANCE/   当前治理、Product Architecture、Owner、CURRENT、Evidence、第三方登记
lumenis/         当前主要产品源码与 SYSTEM / Shared / domain 实现
app/             Flutter Web / Desktop / Mobile Experience
website/         Public Website
contracts/       现有机器/接口合同
config/          受控配置；本地秘密不得提交
migrations/      DB 迁移与版本化变更
alembic/         Alembic migration tooling
scripts/         启动、审计、Gate、维护与受控工具
 tests/           单元/集成/合同/回归测试
research/ docs/  研究、说明与历史材料；不是当前产品真相本身
work/ staging/ output/ tmp/  工作区/候选/输出；不能因文件存在就当成 main 或 Production Truth
```

根目录仍有历史兼容文件和旧命名包装层。它们只有在当前 Owner/调用链仍引用时才是兼容边界；**文件数量、旧名称或历史目录不能重新定义产品架构。**

## 开发环境、配置与秘密

- Python 依赖以 `requirements.txt` / `requirements-dev.txt` 和当前 `.venv` 实际状态为准；不要为了“统一环境”擅自重建环境或升级全部依赖。
- Flutter SDK 版本以 `app/toolchain.json` 为唯一机器锁定，依赖以 `app/pubspec.yaml` / `app/pubspec.lock` 为准；本机与 App Gate 必须核对同一 SDK 版本/Revision/Dart，各平台实际构建能力仍需对应平台验证。
- Node/Browser脚本依赖以 `package.json` / `package-lock.json` 为准。
- `.env`、Cookie、API Key、平台 Session、生产 DB、用户文件和本机私有路径属于本地/受保护配置，**不得提交、打印到日志、写进README或Evidence正文**。`.env.example` 只用于说明变量形状，运行时代码与测试不得把它加载为真实环境。
- 新依赖、模型、字体、二进制工具或外部服务加入产品前，必须同时更新 Owner、第三方登记、License/Notice、运行/恢复和Release影响。
- 当前 OpenCode 已搁置；其本机安装状态不构成序境产品依赖或运行时 Provider。

## 测试与质量 Gate

测试是证据，不是产品成果。正常改动至少执行**受影响测试 + 当前合法 blocking gates**；不能通过删除测试、跳过失败、改断言或换成 fixture 来制造绿色。

当前治理级基础检查包括：

```powershell
.\.venv\Scripts\python.exe scripts\audit_tools\verify_ai_native_constitution.py
.\.venv\Scripts\python.exe scripts\audit_tools\verify_codex_takeover_governance.py
.\.venv\Scripts\python.exe scripts\audit_tools\verify_current_configuration.py
.\.venv\Scripts\python.exe scripts\audit_tools\verify_lumenis_single_product.py
```

Product Gate、App Gate、Critical E2E、真实Runtime和User Outcome仍需按对应Owner/CI/Release合同分别成立。旧CI、旧SHA、旧数据库、旧截图或历史成功日志不能代替当前证据。

## 安全、隐私与数据边界

- Permission、Action Firewall、Effect Fence、Scope和Source/Evidence边界不能为了开发速度绕过。
- 真实平台采集只处理已批准范围和允许的数据；Cookie/Session授权与产品账号体系分离。
- 用户材料、第三方内容、模型训练语料和导出结果必须保留来源、用途、rights和版本；未知权利状态保持UNKNOWN/未批准，不自动升级为可训练/可发布。
- Production DB写入、破坏性迁移、外部发布、自动评论/投放/消息、付费资源和模型Promotion使用各自现有授权边界。
- 日志、测试夹具和Evidence不得泄露密码、Token、Cookie、个人浏览器状态或原始生产数据库内容。

## License、知识产权与第三方声明

LUMENIS原始材料采用仓库根目录 [LICENSE](LICENSE) 中的 **LUMENIS PROPRIETARY LICENSE NOTICE**：除特定文件或组件另有声明外，序境/LUMENIS的原创源码、文档、产品逻辑、架构、设计、Schema、Workflow、Prompt、Dataset、配置及其他原创材料均为专有材料，`Copyright (c) 2026 Zachary-1012. All rights reserved.`。访问私有仓库、参与开发或看到源码**不自动授予复制、分发、再许可、销售、公开部署或商业利用权**；相关许可需仓库所有者明确书面授权。

第三方/开源软件、模型、字体、图标、数据集、工具和资产**不被LUMENIS重新许可或主张所有权**，继续受其各自License、Attribution、Notice、Usage Policy和分发义务约束。当前规范登记入口为：

- [Third-Party / Open-Source Component Register](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)
- [LICENSE](LICENSE)

登记册中的 `VERIFY_BEFORE_RELEASE` / `NOT VERIFIED` 是真实Release阻塞，不允许根据“常见许可证”自行猜测。每次Release前必须重新对齐实际 shipped dependency graph、锁文件、二进制、字体/图标、模型/权重、FFmpeg构建和相应Notice/Source义务。

## 贡献、整合与变更规则

- `main` 是唯一当前实现；不要创建第二产品、第二Owner、第二DB/Evidence store、第二AI Gateway或长期并行候选架构。
- 并行窗口可以工作，但共享Owner/共享文件需要显式M/W6协调，不能互相覆盖。
- 每个窗口对自己Owner内的普通Bug、回归和技术阻塞负责到底：先做一次明确复现并定位Owner/调用链，再查当前官方/标准文档、维护中的上游GitHub和高质量最新实现；必要时比较多种前沿方案，选择对完整能力、正确性、恢复、安全、许可、维护、延迟和实际成本最优的可行方案，直接修复、验证并继续同一窗口闭环。不要把可解决的问题反复抛给M/别的窗口/用户，也不要为同一问题新开重复研究窗口。只有产品决策、权限/凭据、付费资源、安全/数据重大风险或不可控外部依赖才升级。
- 提交只stage当前交付的精确文件；本地未知dirty/untracked工作必须先归Owner，禁止bulk-stage、`reset --hard`、`clean -fd`或“顺手整理”。
- 新研究必须落实到已存在的能力、质量标准或真实结果；研究、线框、报告、测试、文档和Mock都不能取代实现/Runtime/User Outcome。
- 修改产品定位、Owner、Permission、Canonical、数据语义、模型Promotion或Release标准必须遵守现有治理和Product Owner授权，不能由单个工程师自行改写。

## 运行入口

```powershell
Set-Location D:\LUMENIS_REBUILD\序\序境
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

Core 健康：`http://127.0.0.1:8201/healthz`。Flutter Web 入口由同一 Core 的 `/workspace` host 提供，需实际构建及配置；Desktop/Mobile 复用 Flutter 代码；`website/` 仅承载官网。参见 [App说明](app/README.md) 与 [官网说明](website/DEVELOPMENT-BRIEF.md)。

当前产品入口保持开放，不新增账号/升级墙；服务端 Permission、Action Firewall、Effect Fence 和平台会话边界始终有效。

## 执行与安全边界

- C1 获当前明确派工后可继续真实只读采集，但必须遵守已有 Scope、Permission、Session、频率与平台规则；一个平台 Blocked 不能伪装成 ACTIVE，也不应暂停其他已满足前置的平台。
- C2 获当前明确派工后可继续免费 GPU 训练闭环，但必须先验证真实零成本 GPU、精确 model/recipe/data hash、MODEL_TRAIN Permission、Checkpoint/Evaluation 合同；**不得自动租 GPU、充值或启用付费 fallback**。
- F 获当前明确派工后可继续已批准 Experience 实现，但设计状态不等于 Runtime/用户验收。
- C3–C5 获当前明确派工后继续各自真实用户成果，不能用 fixture、文档、测试或 Mock 替代实际业务结果。
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

### 2026-10-08 全产品智能交互规则

智能 UI 采用范围覆盖全部现有能力、44屏及四端，包含研究/业务/创作、设置/通知/恢复。唯一执行依据是[产品蓝图](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)与[Experience §38](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)；[44屏规范索引](contracts/experience/screen-specifications/README.md)逐屏给出实际用户任务和后续采用入口，[既有文字草图](00-GOVERNANCE/evidence/round-15/experience-review-2026-10-06/LUMENIS-44-SCREEN-TEXT-WIREFRAMES-1.5.md)保留历史并同步日期增补。规则/蓝图/草图同步不表示44屏已经实现，后续窗口按既有Owner和明确派工执行。

2026-10-08 前端审计增补已纳入上述唯一规则：全44屏和官网家族需可编辑设计与源码/动作/验收映射，详见[ScreenSpec索引](contracts/experience/screen-specifications/README.md)。其余窗口等待 Product Owner 确认；规则同步不代表 Figma 工程、智能UI实现或用户验收完成。

### 2026-10-08 成熟基础能力、竞品机制与用户操作期待

两份最新增补已合并进[唯一产品蓝图](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)、[Owner执行映射](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)、[双层真实验收](00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md)和[Experience §38](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)：先让用户完成成熟软件基础操作，再证明序境的来源、业务、智能、版本与学习连续性。SH-01/BMP-08及原文字草图细化真实剪辑/播放/波形/录音/重开；GPT/Apple/Tesla只贡献适用操作原则。开源选择遵守[组件准入](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)，不重造现有内核。

当前M完成本次规则及已授权修复同步；F/C1–C6等待Product Owner明确确认再执行。规则收录不是这些能力已实现，也不自动安装新组件或形成训练许可。历史材料保留，最新材料清单为197项（原191+本轮6增补），不代表全部历史资料已读完。

### 2026-10-08 采集日期与维度展示更正

已取消全局固定采集起点：按主体/话题/任务语义采集，显式用户时间范围仍遵守，按真实出版/事件时间整理，未知时间不伪造。无需每项数据都采到，但业务维度必须准确定义并保留；缺值显示“—”和原因，真实0仍是0。采集能力必须用真实正常链及恢复验收，不能靠横杠掩盖Bug。详细合同、旧日期源码及后续C1/C6/F落实入口见[Global§10](00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md)。本轮仅规则同步，未改变运行计划或启动采集。

### 2026-10-08 智能UI逐步交付与产品逻辑审阅

[Experience §38](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)已细化任务选组件、先给有依据的有用部分、持续补充/更正、保留用户编辑、真实保存及取消/重连；待后续Owner实施。[逻辑审阅](00-GOVERNANCE/evidence/round-15/PRODUCT-LOGIC-REVIEW-20261008.md)覆盖既有J1–J8/U01–U25及跨模块断点，优化归入原蓝图与Owner，不另起系统或恢复窗口。研究/源码/运行状态分开，不声称产品智能UI已交付。

# 序境 / LUMENIS

## OpenAI Math v2：可用的有限数学情景与完整升级边界

本次接入用户提供的 v2 源码，采用固定原文公式及精确有限语义，提供 16 个受控计算入口。现有 CTH 来源简报和 BMP 市场研究入口可声明问题、对象/权重或高级参数，经 Task/API 计算并保存数学成果，修订保留父版本，用原任务编号重新打开。没有 AI 仍可执行；声明情景与真实来源、市场发生率及 Canonical 事实严格区分。

[逐篇实现与验收记录](00-GOVERNANCE/evidence/round-15/OPENAI-MATH-ADOPTION-20261007.md)同时保留未完成的一般主算法、形式化证明与模型实验状态。有限枚举不是 FPRAS，二次势不是一般采样器，小型 Gibbs 参数训练不是 gpt-oss 模型能力。源码、实际加载版本、Artifact、UI 与模型收益各自核验，不凭文件/CI 宣布完整产品闭环。


序境是面向商业运营与品牌市场的一个产品，当前处于**工程闭环执行阶段**，尚不能把源码存在、测试通过或 HTTP 200 等同于完整用户验收。已批准的产品体验覆盖官网、Web Workspace、Desktop App 和 Mobile Companion 四个入口，共用一套 Product Core、Canonical Data、Evidence、Permission、AI Gateway、Agent Runtime、Reporting、Evaluation 与成果版本。

仓库：`Zachary-1012/LUMENIS-codex-Clean-OS`；唯一开发/整合分支：`main`。本机标准目录为 `D:/LUMENIS_REBUILD/序/序境`。**当前状态必须由 Git、源码、Runtime、DB、测试和用户结果重新取证，不从 README、旧报告或聊天记录猜测。**

## 当前交付顺序

**基础业务和数据分析不依赖 AI。** 没有模型、外部 AI API、GPU 或推理服务时，真实数据的计数、既定指标、时间聚合、可比范围比较、规则/人工判断及报告仍须产生有用成果，支持保存/修订/重开/恢复。AI 只增强解释、建议和生成；增强不可用不得使基础任务失败。OpenAI Math 已核读方法通过现有分析、报告、评价路径落实目标/约束、分母、范围、样本代表性和成本口径；不以数学模拟补齐真实数据。先验收无 AI 成果，再评价 AI 收益；现存源码缺口与实际采用状态见唯一蓝图、Owner Index、真实交付与 Math 采用记录。

**前端直接构建，不先做设计稿。** 复用已有设计和44屏规范并随源码更新。后续原生客户端只交付 **Windows、macOS 和 iOS**；Android/Linux原生客户端不再是交付目标，保留其历史源码与证据。Linux服务器/CI和Web的跨OS浏览器、窄屏体验不受此限制。

**先闭环官网（Public Website）和 Web Workspace，再推进 Desktop App 与 Mobile Companion。** 后置两端的需求、源码、设计和验收任务完整保留，不当作通过。当前两端的真实业务、来源/权限、成果保存/修改/重开/恢复及适用评价仍须闭环；Web必要的Core/SYSTEM服务继续推进。实际窗口由PO决定，保留原Owner/共享写入保护及零新增付费。此顺序不等于四端整体完成或新增部署授权；详见现有[多端决策](00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md)与[真实交付规则](00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md)。

**所有平台与公开网页的来源类别基础权重相同。** 真实采集、原件入库及恢复能力有证明后，优先用已有获准数据打通分析、业务和创作工具流，形成可保存、修订、重开和恢复的实际成果；不等待全部平台完善或重复采集。来源质量、身份、时间、权益和用途照常核验；平台缺口单列，只影响确实依赖它的路径与结论，完整平台目标不删除。详见[蓝图中的同权与已有数据规则](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md#2026-10-09-来源类别同权与已有数据优先闭环)。

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
Desktop App (Windows / macOS)
Mobile Companion (iOS)
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

## 五轮产品成果与保留的工程责任

唯一交付轮次为 **SYSTEM → CTH → BMP → Shared → Agent Groups / 自研 AI**。
完整成果和退出条件见[唯一产品蓝图](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md#五轮架构产品闭环--2026-10-09-product-owner-直接批准)。
每轮须真实操作、有用成果、保存修订、重开恢复、来源权限及适用真正E2E；必要跨域依赖在本轮关闭。
C1–C6、F、M、W1–W6保留下表工程源码责任，不是六轮产品交付、单业务窗口限制或新阶段。
Product Owner 决定实际窗口开工/暂停/恢复及模型/推理档位；GitHub只记录有核验时间和证据来源的事实。
未知状态/模型记录 `NOT_VERIFIED`；旧审批/PAUSED/RUNNING/恢复条件/默认模型均不自动派工。
本次只同步六份治理文件，不启动窗口，不修改业务源码。原未完成Goal、候选和研究证据完整保留。

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

实际开工前核对 fresh `origin/main`、dirty、Owner/调用方、Writer预约、Runtime、
DB、Permission、Evidence 和真实外部前置条件。源码责任与历史拓扑不能替代当前PO派工。
共享写入继续按M/W6认领、冻结和有界交接，不同时改同一区域。



`ELIGIBLE` 是角色可承接工作；`RUNNING` 需当前实际派工和准入证据。
本地Live Dispatch保留为有日期的事实/接续记录，不能让旧等待或恢复条件自动决定新执行。
配置中的历史模型默认不作为当前指派，不改任何窗口手选模型、effort、速度或账号。



已接受的有效源码、规则、规划和当前状态在同一交付批次同步发布，并核对本地 HEAD、origin/main 与 GitHub live main。正在修改或尚未验收的工作树单独记录为未发布，不覆盖它来制造一致；私有凭证、生产数据库与原始历史不进入提交。旧候选只保留来源与处置证据，当前实现和执行入口仍唯一指向 main 与 AGENTS/CURRENT。

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

当前 C1 先按真实主体批量采集相关发帖，每批返回立即经原 Source/Evidence/Canonical 数据链处理，词条/主题分析后置，同步采集每帖最多处理一张真实封面；不等完整词库或六个平台结束。图片和视频内容理解保留，由既有后台路径处理真实图片、音轨与时间画面，并以原帖/图位置/时间码和版本供后续任务使用。只取封面、OCR 或状态登记都不等于完成理解；执行器未绑定保持 NOT_RUN。C1 自行落实同一 SYSTEM 权限链的用途绑定，导入、关键词与媒体分析/派生保存分别核验，不冒充业务结论或改写原来源权益。准确范围、原文覆盖、幂等/权益/恢复与未读状态保留，详见 [Global §10](00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md)。

本轮 2026-10-09 全产品数据到业务升级沿现有 Collector/Shared/CTH/BMP/Research/Reporting/Evaluation/SYSTEM 及受影响 Web 接线执行，不只是 C1 说明。合法原始观察保存、来源有效性、权限、身份核验、业务分析分开；待核验原件在原 Source 路径可恢复，但不能成为主体事实。六平台独立保留实际能力/限制/事务与性能口径，至少一个获准平台或公开网页来源实证从主体选择、采集到成果保存/关闭重开/修订/来源追溯/中断恢复。完整要求与A–F交付见 Global §10 和 Real Delivery Overlay；不能以规则、原文条数或发布源码宣称闭环。M/C1及其他Owner原候选、材料、集成和采集职责保留；实际窗口状态及模型只据当前PO决定和有日期的核验，不由本段派工。

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
| **C5 / W5 · Importer / Research / Shared** | 完成资料导入、Library/Search、精确 Citation、逐篇/逐页/逐段/逐帧/时间码研究、Reporting、Artifact、SavedWork、通知和共享偏好；所有原件、rights、source hash、父子版本、撤销/恢复可追溯。当前199行 manifest（原191+8增补）不是全部语料，未读正文、未采用研究和 UNKNOWN rights 不能被写成“已吸收”。 |
| **C6 / W6 · Integration / Runtime / Release** | 把已验收 Owner 能力整合成同一 SHA 的 Core/API/DB/四端/FFmpeg/Supervisor/CI/Packaging/Recovery；协调正式 DB 变更、共享调用、启动/重启/取消/回滚、Product/App/Critical E2E 和最终 Evidence bundle；代码存在、build成功或 health=200 都不能单独写成 RELEASED/OPERATING。 |

产品最终闭环不是“所有窗口都有代码”，而是对应真实用户任务能够从**真实输入 → 有依据的结果 → 保存/修改/重开/恢复 → Outcome/Evaluation → 跨端继续使用**完整成立。

### 当前执行器

- **Codex / Codex CLI**：当前研发执行器；Product Owner选择实际窗口模型、推理档位及速度/服务档位。GitHub不固定角色模型；有实际核验才记录模型、时间与证据，否则NOT_VERIFIED。旧配置/启动Profile只是保留的历史数据，Hook不得改变手选设置。M完成获准工作后待命，本次规则更新不启动任何窗口。
- **OpenCode**：**当前搁置，不属于本轮执行路径，也不是 Codex 额度不足时的自动 fallback。** 已有安装/配置不等于获准执行；除非 Product Owner 以后明确恢复，否则任何窗口都不要把任务派给 OpenCode。
- TRAE、Apple、ChatGPT 等只在各自既有规则内作为 Experience/研究参考，不拥有序境产品架构或执行权。

## 当前状态摘要（开工时必须重新取证）

README **不固化 current HEAD、Runtime、DB 行数、dirty文件清单或窗口进度**，因为这些会随每次交付变化。每次开工先执行 `git fetch origin main`、读取 `HEAD` / `origin/main` / dirty，再核 Runtime、DB、Permission、Evidence 和真实用户结果；最新逐能力事实、当前缺口和最近证据只记录在 [CURRENT](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)。

- 当前产品身份是 `序境 / LUMENIS`；默认工作宇宙是 `GLOBAL / ALL`。具体运行进程是否已加载这一版本必须现场验证。
- 产品采用五轮架构成果；M/F/C1–C6保留原工程源码职责。实际窗口由PO决定并现场核验，不从README推断已开工、暂停、模型或并发限制。
- 本地工作树中的任何 dirty/untracked 都先按 Owner 识别并保护；README 不枚举或推断其完成状态，**不得 reset/clean/覆盖未知工作**。
- 当前总体阶段是工程闭环执行；只有对应 Product/App/Critical E2E、Runtime、用户结果和Release证据真实成立后，才能分别声明 `USER_VERIFIED`、`RELEASED` 或 `OPERATING`。

## 人类工程师安全开工流程

本地零新增费用研发入口：VS Code 使用官方 Python/Pylance/Ruff、Dart/Flutter、PowerShell 与 Astro 语言服务；原生 Tasks 调用 [现有 PowerShell 工具](scripts/local_development.ps1)。快照、定向静态检查、差异、格式预览、既有生成器预览和构建不调用模型，不运行模块测试，不自动提交或启动产品服务。授权写入与恢复采用精确 HEAD/hash/Owner/预约和私有回执；用法见 [.codex/README.md](.codex/README.md)。它不改变 C1 派工、产品蓝图、权限或验收标准，也不证明产品能力闭环。

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
6. 按最新 PO 策略完成适用构建、静态/安全/数据检查和真实用户操作验收；不创建/执行单元、集成或换名模块测试，保留历史测试与失败证据。
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

2026-10-08 PO 正式移除单元/集成测试的开发、合并、验收及发布强制地位，禁止新建、执行及换名模块测试；历史文件、断言、失败记录保留。当前以真实任务→源码修改→构建运行→实际操作→真实成果→保存/修订/重开→恢复→验收→正式集成为主线。保留编译、静态质量、安全、权限与数据一致性、真实产品 E2E 和发布验证；历史 FAILED 不改写为 PASS。机器合同 `verification_policy` 和 [当前验收清单](tests/CI_TEST_TIERS.md) 为现行执行定义。

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

LUMENIS 的原创软件及随附原创技术文档采用标准 **Apache License 2.0**，完整条款见根目录 [LICENSE](LICENSE)，版权署名见 [NOTICE](NOTICE)。允许依许可证使用、修改、分发及商业使用；不增加“仅限非商业”、禁止竞争或额外使用审批条款。具体自有软件、第三方材料、数据和商标边界见 [LICENSING.md](LICENSING.md)。本版本覆盖的自有作品不再适用旧的整体专有许可声明；Git 历史保留。

第三方/开源软件、模型、字体、图标、数据集、工具和资产**不被LUMENIS重新许可或主张所有权**，继续受其各自License、Attribution、Notice、Usage Policy和分发义务约束。当前规范登记入口为：

- [Third-Party / Open-Source Component Register](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)
- [LICENSE](LICENSE)
- [NOTICE](NOTICE) / [Licensing scope](LICENSING.md) / [Third-party notices](THIRD_PARTY_NOTICES.md)

登记册中的 `VERIFY_BEFORE_RELEASE` / `NOT VERIFIED` 是真实Release阻塞，不允许根据“常见许可证”自行猜测。每次Release前必须重新对齐实际 shipped dependency graph、锁文件、二进制、字体/图标、模型/权重、FFmpeg构建和相应Notice/Source义务。

## 贡献、整合与变更规则

- `main` 是唯一当前实现；不要创建第二产品、第二Owner、第二DB/Evidence store、第二AI Gateway或长期并行候选架构。
- 已获当前PO派工的Owner按原源码责任工作；共享Owner/文件区域仍按M/W6认领冻结与交接，不同时写入。
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

以下只定义源码责任及必要条件，全部须另有当前PO实际派工；本段不启动窗口/训练/服务。

- C1 在完成 fresh admission 且真实前置条件满足后可执行真实只读采集，并遵守已有 Scope、Permission、Session、频率与平台规则；一个平台 Blocked 不能伪装成 ACTIVE，也不应暂停其他已满足前置的平台。
- C2 在完成 fresh admission 后可执行已批准的免费 GPU 训练闭环，但必须先验证真实零成本 GPU、精确 model/recipe/data hash、MODEL_TRAIN Permission、Checkpoint/Evaluation 合同；**不得自动租 GPU、充值或启用付费 fallback**。
- F 在完成 fresh admission 后执行已批准 Experience 成果；设计状态不等于 Runtime/用户验收。
- C3–C5 在完成 fresh admission 后继续各自真实用户成果，不能用 fixture、文档、测试或 Mock 替代实际业务结果。
- C6 负责整合、Runtime/Release，不得把单模块绿色扩写成全产品绿色。
- Production DB 写入、破坏性迁移、部署/Release、付费资源和外部业务效果仍遵守 `AGENTS.md` 的精确授权边界。

## 验收语义

```text
DEFINED
→ IMPLEMENTED
→ INTEGRATED
→ VERIFIED
→ JOB_CLOSED
→ RELEASED
→ OPERATING
```

这些状态互不替代。`Product Gate / App Gate / Critical E2E / User Outcome` 需要各自证据；旧绿色、旧 SHA、历史报告或模型输出不能替代当前验收。

[直接修复证据](00-GOVERNANCE/evidence/round-15/DIRECT-REPAIR-20261004.md) · [批准后收敛证据](00-GOVERNANCE/evidence/round-15/APPROVED-CONVERGENCE-20261004.md)

历史 ZBC/Z-Brand-Core/CTH-POMS/ZBMP 命名、旧研究和旧运行回执只按 Canonical Naming 兼容规则保留，不得重新成为当前产品身份或执行入口。

### 2026-10-08 全产品智能交互规则

智能 UI 采用范围覆盖全部现有能力、44屏及四端，包含研究/业务/创作、设置/通知/恢复。唯一执行依据是[产品蓝图](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)与[Experience §38](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)；[44屏规范索引](contracts/experience/screen-specifications/README.md)逐屏给出实际用户任务和后续采用入口，[既有文字草图](00-GOVERNANCE/evidence/round-15/experience-review-2026-10-06/LUMENIS-44-SCREEN-TEXT-WIREFRAMES-1.5.md)保留历史并同步日期增补。规则/蓝图/草图同步不表示44屏已经实现；授权启动后的实际派发/准入以本地ledger与真实工具回执为准。

2026-10-08 前端审计增补已纳入上述唯一规则：F保留全44屏和官网家族的可编辑设计、四端差异与任务交互，优先复用Figma；免费受限立即用现有Flutter/Dart/变量/SVG继续，不新增费用，不等全部Figma完成才修已有交互；依既有逐屏合同直接构建，必要设计决定随代码记录，不再等待独立设计稿/Figma或M设计审批。原生Figma与可编辑源码分别记录，载体/版本与源码/动作/验收映射详见[ScreenSpec索引](contracts/experience/screen-specifications/README.md)。C1–C6/F/M/W1–W6 保留原源码责任和完整成果；实际开工、暂停、恢复、模型与推理档位由 Product Owner 决定，本文件只记录有时间和证据来源的已核实事实，不设单业务窗口限制；历史等待文字不再构成暂停指令，M待命也不暂停执行窗口。实际派发/准入以当前直接PO指令、本地ledger和真实工具回执为准，各窗 fresh admission 后才进入 RUNNING。规则同步不代表 Figma 工程、智能 UI 实现或用户验收完成。

### 2026-10-08 成熟基础能力、竞品机制与用户操作期待

两份最新增补已合并进[唯一产品蓝图](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)、[Owner执行映射](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)、[双层真实验收](00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md)和[Experience §38](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)：先让用户完成成熟软件基础操作，再证明序境的来源、业务、智能、版本与学习连续性。SH-01/BMP-08及原文字草图细化真实剪辑/播放/波形/录音/重开；GPT/Apple/Tesla只贡献适用操作原则。开源选择遵守[组件准入](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)，不重造现有内核。

M/F/C1–C6保留原工程职责；实际开工、暂停、恢复、模型与推理档位由PO决定，不从历史状态或串行拓扑推断。源码/Goal 与完整 J/R/U 保留；实际派发/准入以本地 ledger 和真实工具回执为准，fresh admission 后才进入 RUNNING。M 仅核对有变化的成果、共享冲突、CI/风险，无实际可处理事项即待命。规则收录不表示能力实现、验收、组件安装或训练许可。最新材料清单为199项（原191+8增补，含电脑/浏览器视频及12项安全核查），不是全部历史资料已读证明。

### 2026-10-08 采集日期与维度展示更正

已取消全局固定采集起点：按主体/话题/任务语义采集，显式用户时间范围仍遵守，按真实出版/事件时间整理，未知时间不伪造。无需每项数据都采到，但业务维度必须准确定义并保留；缺值显示“—”和原因，真实0仍是0。采集能力必须用真实正常链及恢复验收，不能靠横杠掩盖Bug。详细合同、旧日期源码及后续C1/C6/F落实入口见[Global§10](00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md)。本轮仅规则同步，未改变运行计划或启动采集。

### 2026-10-08 智能UI逐步交付与产品逻辑审阅

[Experience §38](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)已细化任务选组件、先给有依据的有用部分、持续补充/更正、保留用户编辑、真实保存及取消/重连；待后续Owner实施。[逻辑审阅](00-GOVERNANCE/evidence/round-15/PRODUCT-LOGIC-REVIEW-20261008.md)覆盖既有J1–J8/U01–U25及跨模块断点，优化归入原蓝图与Owner，不另起系统或恢复窗口。研究/源码/运行状态分开，不声称产品智能UI已交付。

### 2026-10-08 电脑操作、内置浏览器与派工纠偏

历史全窗恢复/全停、单业务窗口及F调度记录只作有日期的来源。当前PO决定实际派工；窗口转述必须保留原话、日期和范围，不自动扩散暂停/恢复。核验不明为NOT_VERIFIED，本次不启动任何窗口。

序境产品本身须完成授权电脑任务；手机可在任务内查看/接管受控浏览器，Desktop/Web在产品内使用，外部浏览器为明确可选。当前已有受控Browser动作服务，SYS-06前端仍只读、远端绑定及OS executor未闭合，不能声称已完成。[SYS-06](contracts/experience/screen-specifications/SYS-06.md)与[取证及执行映射](00-GOVERNANCE/evidence/round-15/BROWSER-COMPUTER-CONTINUITY-20261008.md)记录准确差距。材料清单现198项（原197+本次视频），不是历史资料全部完成阅读或训练准入。

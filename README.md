# 序境 / LUMENIS

序境是面向商业运营与品牌市场的一个产品，当前处于工程闭环阶段。已批准的产品体验覆盖官网、Web Workspace、Desktop App和Mobile Companion四个入口，共用一套Product Core、数据、Evidence、权限、AI Gateway与成果版本；各入口的当前实现、运行和验收状态以CURRENT及对应源码/运行证据为准。

Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)。

```text
AGENTS.md
→ 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md
→ 00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md
→ 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md
→ 当前Owner、合同、源码与真实结果
```

仓库：`Zachary-1012/LUMENIS-codex-Clean-OS`；唯一开发/整合分支：`main`。本机目录为 `D:/LUMENIS_REBUILD/序/序境`。当前本地与线上状态必须由Git读取，不从README猜测。

## 唯一蓝图与执行入口

- [已批准产品蓝图](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)：闭环后用户得到什么、四入口职责、完整能力和执行顺序。
- [当前接续](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)：已验证结果、实际缺口和下一步。
- [Source Owner Index](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)：C1-C6责任与全部R01-R15/J1-J8/U01-U25、源码和调用合同。
- [Experience](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)：唯一UI/UX、四端、原创手绘视觉和屏幕验收。
- [真实交付](00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md)与[数据范围](00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md)：真实任务、来源、范围、变化修订、恢复和诚实覆盖。

**CTH · 商业运营**采用Subject-first；**BMP · 品牌市场**采用Brand/Market-first。Shared Capability负责资料、研究、创作、Artifact、评价与学习；SYSTEM负责采集、浏览器、调度、数据库、权限、AI和运行。AI增强结果，不拥有Production Truth。

## 当前执行阶段与执行器

当前已进入**受控执行阶段**，但不是把C1–C6全部同时启动。每个任务开工前先重新读取origin/main与本地HEAD/dirty，定位当前Owner、调用方和合同，再核Runtime、DB、Permission、Evidence以及平台Session/GPU等外部前置条件；没有真实缺口、前置条件不满足或已被其他当前工作覆盖时，不制造任务、不绕过阻塞。

- **Codex / Codex CLI**：主控制器与高风险工程执行器。Codex使用产品负责人当前手动选择的模型/推理档位，不由仓库或旧规则自动换模。
- **OpenCode**：M/Codex可调用的受控基础Worker，不是第二产品、第二窗口或第二Owner。当前批准的零成本Worker为opencode/mimo-v2.6-flash-free，允许在已验证的免费白名单内自动选用最强可用模型；当前白名单只开放这一项，**没有付费fallback**。
- OpenCode优先承担明确范围的基础工作，例如Collector适配器/状态/Checkpoint/Source-Evidence检查、测试选择与dry-run准备，以及C2训练输入/hash/recipe/checkpoint/evaluation preflight。默认不做全仓发现式审计。
- OpenCode不得修改产品蓝图、Owner、Permission、Production DB、模型Promotion或发布判断，也不得直接commit/push main。真实平台采集和免费GPU训练只有在现有Scope/Permission/Session/资源前置条件真实满足后才进入执行；配置存在、模型可见或授权存在都不等于任务已完成。


## 正常工作闭环

真实目标与资料 → 授权来源/Evidence/Canonical → 有依据的研究与判断 → 提案/可编辑视频/播客 → 保存与业务使用 → 来源或预算改变 → 定位受影响处并明确采用新版 → 局部修订 → 重开/恢复/回滚 → Outcome/Evaluation。

原始来源不被分析覆盖；未知不是零。提取帧数不等于看完视频，配置成功不等于训练，HTTP200/测试/构建不等于真实用户验收。

## 运行入口

```powershell
Set-Location D:\LUMENIS_REBUILD\序\序境
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

Core健康：`http://127.0.0.1:8201/healthz`。Flutter Web入口由同一Core的 `/workspace` host提供，需实际构建及配置；Desktop/Mobile复用Flutter代码；`website/`仅承载官网。参见 [App说明](app/README.md)与[官网说明](website/DEVELOPMENT-BRIEF.md)。四个入口各有职责，共用同一Product Core。

当前产品入口保持开放，不新增账号/升级墙；服务端Permission、Action Firewall、Effect Fence和平台会话边界始终有效。保护本机个人CN小红书身份，开发采集只用已批准HK/国际身份。

## 当前执行约束

当前由M按AGENTS.md控制执行和main整合；C1–C6与F仍是完整责任/验收映射，不作为需要同时启动的平行队列。Codex负责主控、高风险修复与最终判断，OpenCode只作为被M/Codex调用的基础Worker。C1只读采集与C2免费GPU路径已有执行方向，但每次真实启动仍必须先通过对应Scope/Permission/Session/零成本资源等现有前置条件；条件不满足就记录真实阻塞，不靠换Provider、放宽权限或假状态推进。正式Production DB写入、部署、付费资源和外部业务效果继续按AGENTS.md的精确边界执行。全部需求和材料继续归现有Owner，研究须落实到产品能力；未读或未采用不得称为已吸收。

每项能力只保留一个当前主实现、已有完整任务卡和一个当前成果入口，不新增并行候选源码目录。按真实依赖连续完成，不做无变化的重复审计、测试或逐函数交接。必要验证保留。主线发布与CURRENT/证据在同一交付完成，读取remote核对；其他dirty工作保护到单独验证后。

## 验收与历史

`IMPLEMENTED → TESTED → LIVE_VERIFIED → USER_VERIFIED → RELEASED → OPERATING`需各自证据。Product Owner重复任务在工程可操作后进行。最新同版本线上CI与本地结果见CURRENT，不能用历史绿色替代。

[直接修复证据](00-GOVERNANCE/evidence/round-15/DIRECT-REPAIR-20261004.md) · [批准后收敛证据](00-GOVERNANCE/evidence/round-15/APPROVED-CONVERGENCE-20261004.md)。旧规则、研究、原件、失败和版本回执用于溯源；已退役的V3/双库Gate及全盘扫描脚本不再是当前开工入口。

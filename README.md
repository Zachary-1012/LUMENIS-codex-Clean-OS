# 序境 / LUMENIS

序境是面向商业运营与品牌市场的一个产品，当前处于工程闭环阶段。它通过官网、Web Workspace、Desktop App和Mobile Companion四个入口，共用一套Product Core、数据、Evidence、权限、AI Gateway与成果版本。

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

本轮M只完成开工前规则、材料、Owner、依赖和验收收敛，不实施产品源码或运行操作。C1–C6保持暂停；F按产品负责人单独授权独立工作，M不读取、管理或联系F。现有/免费GPU优先不构成本轮训练或付费授权；全部需求和材料保留，研究必须映射到既有产品能力，未读/未采用不得称吸收完成。

每项能力只保留一个当前主实现、已有完整任务卡和一个当前成果入口，不新增并行候选源码目录。按真实依赖连续完成，不做无变化的重复审计、测试或逐函数交接。必要验证保留。主线发布与CURRENT/证据在同一交付完成，读取remote核对；其他dirty工作保护到单独验证后。

## 验收与历史

`IMPLEMENTED → TESTED → LIVE_VERIFIED → USER_VERIFIED → RELEASED → OPERATING`需各自证据。Product Owner重复任务在工程可操作后进行。最新同版本线上CI与本地结果见CURRENT，不能用历史绿色替代。

[直接修复证据](00-GOVERNANCE/evidence/round-15/DIRECT-REPAIR-20261004.md) · [批准后收敛证据](00-GOVERNANCE/evidence/round-15/APPROVED-CONVERGENCE-20261004.md)。旧规则、研究、原件、失败和版本回执用于溯源；已退役的V3/双库Gate及全盘扫描脚本不再是当前开工入口。

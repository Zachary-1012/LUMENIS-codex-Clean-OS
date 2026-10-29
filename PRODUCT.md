# 寰意 / OEVIRA

寰意是自研的信息研究与创作工作平台：持续取得与用户有关的信息，帮助用户形成
可靠判断，并完成可以修改、交付和继续使用的成果。

商业运营团队、品牌与代理机构、个人研究与创作者共同使用一套工作、资料、成果
和权限基础。专业差异通过任务、分析口径和编辑工具提供，不通过多个互不相通的产品。

共同工作方式：目标与约束 → 资料获取 → 核对与处理 → 分析或创作 → 修改交付
→ 按需跟踪。独立研究、写作、视频和播客可以直接开始，不需登记商业主体。

一级导航：工作、监测、资料、成果。设置、通知、搜索、工作空间切换是全局工具。
监测是长期关注；工作是一次有目标的活动；资料是可复用输入；成果是可使用输出。
同一对象在多个视图出现时仍只有一份数据与版本链。

## Decisions approved 2026-10-29

- New product architecture and code, using old source only as optional reference.
- Keep commercial, brand, research, creative, document and professional media depth.
- One general acquisition system with HTTP and browser acquisition; platform-specific
  parsing belongs inside it, never in separate schedulers, stores or identity systems.
- Platform identities are authorized by each user, not restricted to developer accounts
  or regions. Product identity and platform identity remain distinct.
- Maintain self-developed core capabilities and owned AI development. Only planned
  components may be adopted; research of another product is not permission to integrate it.
- Basic operations work without AI. AI-specific results require actual inference and
  separate evaluation. Withdrawn GPU training is not restored.
- Public observations do not imply sales, market share, conversion or causation.
- Work/results can be saved before a business decision. Draft preservation is not
  approval for publishing, spending or another external action.
- Retain pixel-cyber, botanical ecology and retro-futurist identity, Gypsophila logo,
  and the five plant characters. No inherited rejected screen skeletons.
- Web and Windows are primary operational surfaces; Website presents real capabilities
  and entries; macOS/iOS retain later device-specific acceptance.
- General OS control, a standalone image editor, duplicate dashboards and user-facing
  internal governance/algorithm consoles are excluded.

The complete functionality, workflows and disposition decisions are in
`docs/PRODUCT-SPEC.md`; presentation is in `DESIGN.md`, implementation boundaries
in `docs/ARCHITECTURE.md`, and completion criteria in `docs/ACCEPTANCE.md`.

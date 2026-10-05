# 批准后的规则、引用与源码收敛 — 2026-10-04

本记录是交付证据；唯一执行入口为AGENTS，唯一产品蓝图为现Product Architecture。

基线：`be347f03eb9f2bc470a39644df281be3a3d704c9`。用户批准蓝图SHA256：`b5477138083401a427e0995fd877805f9a451db6c90ad0dbc2d3125cadc47552`。编号更正：49项审计处置使用D01–D49；产品验收仅使用R01–R15。原审计材料曾把49条处置临时标为R01–R49；此处仅以“原审计编号（非验收项）”保存历史行标签，绝不与产品R01–R15按序号对应。原观察时间、基线、处置内容和Git历史证据均保留。

## 本批完成与限制

- 删除7个过时活动入口；保留独有安全条款及固定历史出处。
- APP ONLY误读、旧website缺失状态、旧15段串行派工和历史恢复指令已校准；四入口与全部R/J/U保留。
- 能力locator将共享API正确归Product Core composition/API；89项定向检查通过。线上旧失败保留，本批包含遗漏的5个配套测试修正。
- 20项已发布源码不再作为待合任务；75份可核历史副本与1份根目录误置研究脚本已可回读归档。14份不匹配副本仍保留，不能称全体本地工作已合完。
- 191项资料精确定位，空locator为0；实际位置状态：`{'EXISTS': 71, 'REMOTE_NOT_RECHECKED': 95, 'MISSING_OR_MALFORMED': 25}`。十四类研究直接对应现Owner和产品行为，未读/缺件/未采用不伪装完成。
- 本批未启动其他窗口、付费GPU、模型或生产DB写入；未宣称四端、Owned AI、实时正常业务及产品全部闭环。

## 49项逐项处置（D01–D49，与验收项R01–R15分开）

| ID | 原审计编号（非验收项） | 路径 | 审计分类 | 已执行处置与剩余边界 |
|---|---|---|---|---|
| D01 | R01 | `00-GOVERNANCE/GOVERNANCE-AUTHORITY-MAP-20260904.md` | 已替代但仍引用 | 明确退役活动入口；固定提交和校验过的外部备份保留，独有有效条款归现Owner。 |
| D02 | R02 | `00-GOVERNANCE/CANONICAL-EXECUTION-V3-20260904.md` | 已替代但仍引用 | 明确退役活动入口；固定提交和校验过的外部备份保留，独有有效条款归现Owner。 |
| D03 | R03 | `00-GOVERNANCE/AI-EXECUTION-MASTER-COMMAND-V2-20260904.md` | 明确废弃 | 旧地图删除后缺失V2不再是开工入口；不创建占位文件。 |
| D04 | R04 | `00-GOVERNANCE/WEB-NO-SCROLL-INTEGRATED-UI-EXECUTION-CONTRACT-20260904.md` | 明确废弃 | 失效旧引用退出；非必要不上下滚动及官网例外保留在Experience。 |
| D05 | R05 | `00-GOVERNANCE/UNIFIED_UI_UX_INFORMATION_ARCHITECTURE_V1.md` | 已替代但仍引用 | 旧UI总纲已退出入口；保留当前Experience与屏幕合同。 |
| D06 | R06 | `00-GOVERNANCE/RELEASE_AND_AUTORUN_GATE.md` | 已替代但仍引用 | 明确退役活动入口；固定提交和校验过的外部备份保留，独有有效条款归现Owner。 |
| D07 | R07 | `00-GOVERNANCE/TWIN_EXECUTION_GATE.md` | 已替代但仍引用 | 明确退役活动入口；固定提交和校验过的外部备份保留，独有有效条款归现Owner。 |
| D08 | R08 | `00-GOVERNANCE/CANONICAL_REGISTRY.md` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D09 | R09 | `00-GOVERNANCE/CANONICAL-NAMING-AND-TWIN-SYNC.md` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D10 | R10 | `AGENTS.md` | 仍有效 | 已修订当前说明/引用；采用既有Owner，不删除能力与历史。 |
| D11 | R11 | `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D12 | R12 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md` | 已替代但仍引用 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D13 | R13 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md` | 已替代但仍引用 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D14 | R14 | `00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md` | 历史需保留 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D15 | R15 | `00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md` | 已替代但仍引用 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D16 | R16 | `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` | 仍有效 | 去掉旧恢复指令；Cue/319b/图标分层/无固定AIGC配额及实际阅读边界保留。 |
| D17 | R17 | `00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D18 | R18 | `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D19 | R19 | `scripts/audit_tools/locate_capability_context.py` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D20 | R20 | `.agents/skills/lumenis-local-engineering-tools/SKILL.md` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D21 | R21 | `.agents/skills/lumenis-current-truth/SKILL.md` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D22 | R22 | `app.py` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D23 | R23 | `experience_runtime.py` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D24 | R24 | `lumenis/system/runtime/workspace_host.py` | 仍有效 | 当前workspace host保留；本轮未把路由存在认作用户任务验收。 |
| D25 | R25 | `website/package.json` | 仍有效 | 实际网站包保留；旧ABSENT断言修正，未发布公共站点。 |
| D26 | R26 | `app/web/index.html` | 仍有效 | Flutter Web目标保留；四入口不被APP ONLY旧措辞取消。 |
| D27 | R27 | `app/README.md` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D28 | R28 | `website/DEVELOPMENT-BRIEF.md` | 历史需保留 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D29 | R29 | `contracts/experience/README.md` | 仍有效 | 共同数据/权限/状态合同保留；不定义第二设计权威。 |
| D30 | R30 | `scripts/audit_tools/verify_experience_authority_exclusive.py` | 仍有效 | 真正禁止旧渲染器与第二设计权威的门禁保留；未弱化。 |
| D31 | R31 | `scripts/audit_tools/verify_lumenis_single_product.py` | 仍有效 | 四表面/单Owner门禁保留，修复蓝图漏写的有效兼容语义。 |
| D32 | R32 | `scripts/audit_tools/scan_all.py` | 明确废弃 | 明确退役活动入口；固定提交和校验过的外部备份保留，独有有效条款归现Owner。 |
| D33 | R33 | `scripts/audit_tools/scan_local_repos.py` | 明确废弃 | 明确退役活动入口；固定提交和校验过的外部备份保留，独有有效条款归现Owner。 |
| D34 | R34 | `scripts/audit_tools/local_feature_diff.py` | 明确废弃 | 明确退役活动入口；固定提交和校验过的外部备份保留，独有有效条款归现Owner。 |
| D35 | R35 | `scripts/audit_tools/asset_impact_scan.py` | 明确废弃 | 当前无脚本且无活动workflow调用；历史删除/失败证据保留，不恢复空脚本。 |
| D36 | R36 | `lumenis/shared/agents/skills/lifecycle.py` | 仍有效 | 当前生命周期源码与调用保留；旧404结论不可用于删除。 |
| D37 | R37 | `docs/DB-MIGRATION-PLAYBOOK.md` | 历史需保留 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D38 | R38 | `docs/learning/SQLITE-ALEMBIC-MIGRATION-20260903.md` | 已替代但仍引用 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D39 | R39 | `lumenis/shared/database/migrations.py` | 仍有效 | Shared Database唯一迁移实现保留；未改生产数据库。 |
| D40 | R40 | `topic_campaign.py` | 仍有效 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D41 | R41 | `output/final-audit-2026-09-21/LUMENIS_PRODUCT_ARCHITECTURE_FUNCTION_SOURCE_AUDIT_2026-09-21.md` | 历史需保留 | 继续保留有效合同/历史证据；不作为第二执行权威。 |
| D42 | R42 | `00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/MATERIAL-OWNER-MANIFEST.json` | 证据不足 | 191项精确原件locator已恢复，空locator为0；缺件/未读/权限仍逐条保留，未宣称资料全部采用。 |
| D43 | R43 | `work/research-continuation-20261003/FULL-COVERAGE-OWNER-INTERFACE-ACCEPTANCE-MATRIX-20261004.json` | 已并入唯一索引；本地证据保留 | 14个RC类别与当前Owner Index RC-01–RC-14对应；唯一新增的RC-09采样率/声道/time_base/start_pts/分段映射已并入RC-09。矩阵仍是本地证据，不是第二队列；正文未读、来源权利和实际采纳仍按各行状态保持OPEN。 |
| D44 | R44 | `work/w6-integration-20261002/coherent-owner-integration-20261004/APPLIED.json` | 已替代但仍引用 | 17路径已发布；可核历史源码副本退出活动目录，APPLIED原回执未改写；不重放旧postimage。 |
| D45 | R45 | `work/w6-integration-20261002/coherent-owner-integration-20261004/missing-layer-integration/APPLIED.json` | 已替代但仍引用 | 3路径已发布；同样按哈希归档，未宣称运行任务已验收。 |
| D46 | R46 | `work/frontend-2026-10-03/FRONTEND-REFERENCE-EXECUTABLE-20261004.md` | 证据不足 | 前端报告保留为证据；确认的范围已归Experience；尚未完成逐帧/试听的部分继续OPEN。 |
| D47 | R47 | `config/ai-owned-training-runtime.json` | 证据不足 | 私有训练配置原样保留不提交；不改变运行绑定，不启动GPU。 |
| D48 | R48 | `undefinedvalidate_research.py` | 证据不足 | 与原包验证器不完全同字节，有独有内容；从根目录迁出到可回读归档，未丢弃。 |
| D49 | R49 | `00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json` | 仍有效 | 唯一跨产品JSON契约保留，旧双库总指令不再覆盖它。 |

## 可复核入口

- 同名JSON保存批准指纹、逐文件当前SHA、替代来源、固定提交链接和准确未完成项。
- 原始审阅报告位于本机 `D:/LUMENIS_REBUILD/序/审阅交付/规则引用审计与产品蓝图-20261004/`。
- 退役内容、逐文件回执及实际日志位于本机 `D:/LUMENIS_REBUILD/序/序境-convergence-backups/approved-cleanup-20261004/`；原始APPLIED回执未改写。
- 当前提交的远端CI结果以GitHub同SHA运行记录为准。本地通过不预填远端PASS。

## 直接后续

优先将已保留采集/媒体/播放器等独有源码收敛到同一主线正常路径；按蓝图以真实许可资料、Source/Evidence、保存修订重开恢复与同版本运行验收。尚未实测的Owned AI与四端结果继续OPEN，不能用本记录代替能力交付。

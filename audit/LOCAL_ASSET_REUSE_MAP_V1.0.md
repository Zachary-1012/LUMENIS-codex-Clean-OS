# ZBC 本地资产复用地图 V1.0（判"缺失/需新建"前先查这里）

> 原则：任何功能/模块/数据/研究被标"缺失/需新建/找不到/BLOCKED"前，必须先在下列本地目录检索已有实现，能复用就**适配融合**（不照抄、融入当前双域架构、不推翻主线）；确实没有才自研。用户明确：本地基本都有，不要重复造轮子。

## 一、可复用目录（D:\）
| 目录 | 是什么 | 复用做什么 | 归属/边界 |
|---|---|---|---|
| Taikoo-monitor-new | **ZBC 主库（当前工作）** | 唯一事实基线 | ZBC |
| Taikoo-monitor-new-backups\dcc-legacy-20260831-052749 | 8/31 旧版备份 | 找"以前做过、现在找不到"的旧功能/旧实现回补 | ZBC，回补需适配当前架构 |
| Taikoo-staging-ui (git) | 完整 staging 镜像：static/templates/collector_v2/platform_adapters/v4_upgrade/report_export/ref_gpt_v2/tests | 旧 UI/CSS/JS（design-v9-gpt-codex.css、zb-gpt-theme.css、keyboard_shortcuts.js 等）、旧采集器/适配器/导出参考 | ZBC，增量取长不恢复旧UI |
| Taikoo-security (git) | 安全专项镜像：collector_guard 等 | 安全防护/守卫/边界的已有实现回补 | ZBC/Shared |
| Zachary OS AI | OSAI 共享智能层（633 文件，已导入 intelligence_library） | 研究/协议/能力注册表参考 | SHARED，只走版本化契约，**不成 runtime 依赖** |
| AI-Development-Research-Hub (git) | ADRH：cases/CASE-LIBRARY、research、design-system、protocols、CAPABILITY-REGISTRY | 研究案例库、设计系统、协议、影子学习、跨仓基线 | SHARED 参考 |
| intelligence_library / OSAI / ADRH 研究库 | 已研究沉淀的 KOS 成果 | **KOS 去固定公式时，以"平台官方 KOS 规则 + 已研究成果"结合为准** | ZBC/Shared |
| SICI-Core (git) | B2 SICI 独立产品（css/js/shadow_run/upgrade_modules/ZBIP design tokens） | 只借设计 token/手法 | **独立产品，不并入业务代码** |
| Development-Command-Console (git) | B1 DCC 独立产品（protocols/server/tools） | 只借协议/工程手法 | **独立，不并入** |
| global-growth-intelligence (git) | GGI 独立产品（ggi/07-CONTRACTS/migrations） | 三仓协同对照 | **GGI 归属，不混进 ZBC** |
| Zachary\osai-ui | OSAI 前端 | 仅参考 | SHARED |
| BrowserUse、edge-cdp-profile | 浏览器自动化/CDP 画像 | 内置浏览器采集通道参考 | Shared 工具 |
| C盘过往数据、恢复文件 | 历史遗留 | 找丢失资料时兜底检索 | 只读 |

## 二、禁止纳入/禁止动
- `D:\KOS AI Review 工作台`：与本项目**完全无关**，数据、界面、流程一律不参考、不纳入、不复制。
- `D:\太古汇运营资料`：用户明确禁止动、禁止纳入 ZBC。
- `D:\微信数据`：仅素材来源，不纳入代码库。
- 网盘/软件数据目录（BaiduNetdisk、wps云空间、KingsoftData、KimiData、Doubao、$RECYCLE.BIN 等）不作为功能来源。

## 三、复用纪律
1. 顺序：先查主库 → backups → staging-ui/security → ADRH/OSAI → KOS 基础数据 → 独立产品(只借手法)；都没有再自研。
2. 复用必须适配 ZBMP/CTH 双域与当前 No-Scroll/设计 token/函数驱动真实数据要求，增量融合，不整体搬迁、不恢复旧 UI、不推翻已验证模块。
3. 资产带归属：ZBC 可直接用；GGI/SICI/DCC 保持独立只借思路；OSAI 走契约不成运行时依赖。
4. 数据精准红线不变：缺失显式 null/unknown/missing，禁估算/默认值；**KOS 指标与归因去固定公式，以"各平台官方 KOS 规则 + intelligence_library/OSAI/ADRH 已研究成果"结合、可延展、不写死公式；D:\KOS AI Review 工作台与本项目完全无关，数据/界面/流程均不参考。**
5. 每处复用在交付说明里写清"来自哪个本地目录、如何适配"，保证可追溯。

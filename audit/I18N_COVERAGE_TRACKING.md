# I18N 存量替换登记与覆盖率追踪 V1.0

> 生效日期：2026-09-06
> 阶段：阶段一（地基铺设）
> 规则：新增改动页禁止硬编码裸串，存量分批替换并登记。韩文 missing 显式列出，不编造。

## 一、框架状态

| 组件 | 状态 | 路径 |
|---|---|---|
| i18n 核心框架 | ✅ 已建 | static/js/i18n.js |
| 术语渲染替换 | ✅ 已建 | static/js/terminology.js |
| 线性图标库 | ✅ 已扩展 | static/js/lumenis-icons.js |
| zh-CN 词条 | ✅ 核心词条 | static/locales/zh-CN.json |
| en 词条 | ✅ 核心词条 | static/locales/en.json |
| ko 词条 | ⚠️ 地基版（大部分 missing） | static/locales/ko.json |
| 语言切换入口 | ✅ 设置-外观 | templates/system/settings.html |
| 持久化 | ✅ localStorage('lumenis-lang') | — |
| 默认语言 | ✅ zh-CN | — |

## 二、页面 i18n 迁移进度

### 已迁移（阶段一）

| 页面 | 模板路径 | 迁移内容 | 状态 |
|---|---|---|---|
| 基础布局/导航 | templates/base.html | 导航标签、域名标签、Logo、搜索框、状态文本（data-i18n） | ✅ 核心词条 |
| 首页/Command Home | templates/home/command_home.html | 全部可见文案（内联 homeDict + data-i18n） | ✅ 已迁移 |
| 设置页 | templates/system/settings.html | 语言切换器接入（页面自身文案待阶段二迁移） | ⚠️ 部分 |

### 待迁移（阶段二）

| 页面 | 模板路径 | 硬编码串估算 | 优先级 |
|---|---|---|---|
| ZBMP 概览 | templates/zbmp/overview.html | 高 | P0 |
| ZBMP 品牌 | templates/zbmp/brand.html | 中 | P1 |
| ZBMP 内容 | templates/zbmp/content.html | 中 | P1 |
| ZBMP KOS | templates/zbmp/kos.html | 中 | P1 |
| ZBMP 竞品 | templates/zbmp/competition.html | 中 | P1 |
| ZBMP 风险 | templates/zbmp/risk.html | 中 | P1 |
| ZBMP 报告 | templates/zbmp/reports.html | 中 | P1 |
| ZBMP 智能 | templates/zbmp/intelligence.html | 中 | P1 |
| CTH 概览 | templates/cth/overview.html | 高 | P0 |
| CTH 实时 | templates/cth/realtime.html | 中 | P1 |
| CTH 事件 | templates/cth/events.html | 中 | P1 |
| CTH 风险 | templates/cth/risk.html | 中 | P1 |
| CTH 小红书 | templates/cth/xiaohongshu.html | 高 | P0 |
| CTH 报告 | templates/cth/reports.html | 中 | P1 |
| CTH 品牌 | templates/cth/brands.html | 中 | P1 |
| CTH 行业 | templates/cth/industries.html | 中 | P1 |
| CTH 证据 | templates/cth/evidence.html | 中 | P1 |
| CTH KOS | templates/cth/kos.html | 中 | P1 |
| 系统运行时 | templates/system/runtime.html | 中 | P1 |
| 系统采集器 | templates/system/collector.html | 中 | P1 |
| 系统 AI | templates/system/ai.html | 中 | P1 |
| 系统数据库 | templates/system/database.html | 中 | P1 |
| 系统安全 | templates/system/security.html | 中 | P1 |
| 系统评估 | templates/system/evaluation.html | 中 | P2 |
| 登录页 ZBMP | templates/auth/zbmp_login.html | 高 | P0 |
| 登录页 CTH | templates/auth/cth_login.html | 高 | P0 |
| 智能库 | templates/intelligence/library.html | 中 | P2 |
| 生产域各页 | templates/production/*.html | 高 | P1 |
| 研究域各页 | templates/research/*.html | 中 | P2 |
| 运维域各页 | templates/operations/*.html | 中 | P2 |

## 三、术语替换进度

| 代号 | 渲染层替换(terminology.js) | 模板硬编码修复 | 状态 |
|---|---|---|---|
| ZBC | ✅ 已映射 | ✅ 首页已修复 | ✅ |
| OSAI | ✅ 已映射 | ✅ 首页已修复 | ✅ |
| ZBMP | ✅ 已映射 | ⚠️ 域名Tab待阶段二 | 部分 |
| CTH | ✅ 已映射 | ⚠️ 域名Tab待阶段二 | 部分 |
| SYS | ✅ 已映射 | ⚠️ 域名Tab待阶段二 | 部分 |
| TOTP | ✅ 已映射 | ⚠️ 设置页待阶段二 | 部分 |
| Provider: detecting… | ✅ 已映射 | ✅ 首页已修复 | ✅ |
| AI Ready | ✅ 已映射 | ✅ 首页已修复 | ✅ |
| Evidence-backed | ✅ 已映射 | ✅ 首页已修复 | ✅ |
| source: * | ✅ 已映射 | ⚠️ 首页部分修复，其余待阶段二 | 部分 |

## 四、图标线性化进度

| 位置 | 原图标 | 新线性图标 | 状态 |
|---|---|---|---|
| 左导航 ZBMP-Overview | ◈ | home | ✅ |
| 左导航 ZBMP-Brand | ▣ | brand | ✅ |
| 左导航 ZBMP-Content | ✎ | content | ✅ |
| 左导航 ZBMP-KOS | ◉ | megaphone | ✅ |
| 左导航 ZBMP-Competition | ⇄ | compare | ✅ |
| 左导航 ZBMP-Risk | ⚠ | risk | ✅ |
| 左导航 ZBMP-Reports | ▤ | report | ✅ |
| 左导航 CTH-Overview | ◈ | home | ✅ |
| 左导航 CTH-Real-time | ⚡ | bolt | ✅ |
| 左导航 CTH-Events | ◆ | event | ✅ |
| 左导航 CTH-Risk | ⚠ | risk | ✅ |
| 左导航 CTH-小红书 | 📕(实心红块) | xiaohongshu(线性) | ✅ 关键修复 |
| 左导航 CTH-Reports | ▤ | report | ✅ |
| 左导航 SYS-Runtime | ⚙ | gear | ✅ |
| 左导航 SYS-Collector | ⬢ | inbox | ✅ |
| 左导航 SYS-AI | ◇ | intelligence | ✅ |
| 左导航 SYS-Database | ▦ | database | ✅ |
| 左导航 SYS-Security | 🔒 | lock | ✅ |
| 顶栏搜索 | ⌕ | search | ✅ |
| 顶栏通知 | ♪ | bell | ✅ |
| 底栏主题切换 | ◐ | sun | ✅ |
| 移动端Tab栏 | ◈⚡◆⚠⚙ | home/bolt/event/risk/gear | ✅ |
| 设置页图标 | 🎨👤🔐🛡️… | emoji(待阶段二替换) | ⏳ 阶段二 |
| 首页快捷入口 | 内联SVG | 已线性 | ✅ |

## 五、韩文 missing 清单（阶段一）

> 韩文必须复用 intelligence_library/OSAI/ADRH 三语库母语校对，没把握标 missing 回退中文，严禁机翻硬凑。
> 当前确认词条：서경（序境/LUMENIS 品牌名，来源 CANONICAL-NAMING-AND-TWIN-SYNC.md）

### 已确认韩文词条
- product.name = "서경 LUMENIS"
- appearance.lang_zh_cn = "简体中文"
- appearance.lang_en = "English"
- appearance.lang_ko = "한국어"

### 待补韩文词条（missing，回退中文）
- domain.zbmp / domain.cth / domain.system
- common.*（全部 20+ 词条）
- nav.*（全部 20+ 词条）
- status.*（全部 13 词条）
- home.*（全部 25+ 词条）
- appearance.*（除语言名外全部）
- security.*（全部）
- footer.*（全部）

**待办**：阶段二需审计 intelligence_library 中 OSAI/ADRH 三语库资产，提取已有韩文翻译，经母语校对后补全 ko.json。

## 六、验收清单

- [x] i18n 框架 t(key) 函数可用
- [x] zh-CN / en / ko 三套词条文件存在
- [x] 语言切换在设置-外观，持久化 localStorage
- [x] 默认 zh-CN
- [x] 术语表 audit/PRODUCT_TERMINOLOGY_TABLE_V1.0.md
- [x] 渲染层术语替换 static/js/terminology.js
- [x] 首页 ZBC/OSAI 代号文案已修复
- [x] 左导航全部图标线性化（小红书实心红块已改线性）
- [x] 面向用户层 grep 无 ZBC/OSAI 裸串
- [ ] 全页面 i18n 迁移（阶段二）
- [ ] 韩文全量翻译（阶段二，需母语校对）
- [ ] 设置页 emoji 图标线性化（阶段二）
- [ ] 全页面技术态串(source:/Provider:)替换（阶段二）

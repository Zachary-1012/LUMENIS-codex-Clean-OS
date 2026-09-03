# 序境首页命名/图标收敛 + Emoji 全量审计（Audit #03）

- 日期：2026-09-04 · 状态：本批 EXECUTED + VERIFIED；Emoji 全量替换为分批 BACKLOG
- 触发：首页可见文本/DOM 导出比对序境命名与线性图标规范
- 上游：CSS_CONVERGENCE_AUDIT_01/02

## 一、本批已完成（真实渲染验证）

| 项 | 位置 | 处理 | Evidence |
|---|---|---|---|
| 旧副品牌 CorTech Lab 残留 | index.html 首页 hero eyebrow + 描述 | 收敛为「序境 · CTH-POMS」「序境 · 广州太古汇舆情监测系统（CTH-POMS）」 | 渲染后 document.body 全文 CorTech = 0 |
| 导出日报按钮彩色 emoji | index.html hero 主按钮 | 📊 → 14px 线性下载 SVG（currentColor，无新增 CSS） | exportBtnHasSvg=true、emoji=false |
| 导出格式菜单彩色 emoji | index.html exportMenu | 去除 📗📘📄，纯文字 Excel/Word/CSV | innerText 验证无 emoji |
| 热门话题分类 `other` 未本地化 | app.js renderTopics | 新增 topicLabel() 显示层归一 other/others/uncategorized→其他；**检索 key 与后端数据不变** | 首页 chips 原 `other` 显示为「其他」，topicUrl/showNoteCases 仍用原始 key |
| 历史启动屏模板零引用 | static/launch-screens（14 文件，dark/morandi/cth-poms 多主题） | 全仓检索仅 1 处历史文档提及、零代码/路由引用，已被 splash v4 取代 → git mv 归档 99-ARCHIVE/static/launch-screens（R 保留，作设计参考不删） | 14 个 R rename |

- app.js `node --check` 通过；Playwright 1440 渲染真实 pageerror = 0（过滤既有 credentials 提示）。
- 首页 6 个 metric 图标经核查已是线性 SVG（前序完成），本轮不重复处理。

## 二、Emoji 全量审计（464 个 / 29 文件，分批替换依据）

扫描范围 static 下 .html/.js（排除 99-ARCHIVE）。按性质分四类，**不一次性大改**，逐类走"线性 SVG 替换 → 渲染回归 → 提交"小批次。

### 分类与优先级
| 类别 | 代表 | 处理原则 | 优先级 |
|---|---|---|---|
| A. 正式 UI 图标（按钮/卡片/标题/icon 容器） | 📊📋📝🔍📱💬📈🏢📚🔧🛡⚙📥📤🌐 | 替换为统一线性 SVG（currentColor、统一 stroke/size），建立 Icon Registry | P1（最高） |
| B. 彩色状态 emoji | 🔴🟡🟢✅❌⚠️🔄 | 状态点统一为 CSS `.status-dot`（序境状态签名）；操作结果用线性 ✓/✕ SVG 或 Stone 文本，不用彩色 emoji | P1 |
| C. 业态/内容分类编码 | app.js 👗👔🍽💄👜🧸🏃（8 大业态）、🏷🏷 | 有信息识别价值，不删除语义；统一改为线性分类图标集（与 topic type-tag 同一套），保持极浅底/中性 | P2 |
| D. AI 回复 / 命令帮助文本内 emoji | zachary_system_knowledge(47)、zachary_robot_enhanced 等 | 属生成文本风格而非 UI icon，**不在 UI 线替换**；如要改需另立"AI 表达风格"任务并评估对回复可读性影响 | P3（暂缓，需决策） |

### 文件工作量分布（A/B/C 类主战场，D 类单列）
| 文件 | 数量 | 主要类别 |
|---|---|---|
| architecture_dashboard.js | 60 | A/B 为主（架构控制台，优先） |
| system_features_ui.js | 58 | A/B 为主 |
| index.html | 54 | A/B/C 混合（首屏，逐区推进） |
| zachary_system_knowledge.js | 47 | D 为主（暂缓） |
| app.js | 46 | C 业态 + A/B |
| v3_modules.js | 40 | A 为主 |
| case_deep_analysis.js | 26 | A/C |
| frontend_enhancement.js | 26 | A/B |
| modal_simplify.js | 19 | A |
| 其余 19 文件 | 各 ≤12 | 零散，随所在页面批次处理 |

### 替换铁律
1. 只改视觉呈现，不改任何 onclick / 数据 key / 检索逻辑 / AI 输出事实。
2. 线性 SVG 统一：fill:none;stroke:currentColor;stroke-width:2;round 端点；尺寸 14/16/18 三档；颜色走 Stone/语义 token，禁裸色。
3. 每个文件改完 `node --check`，每批页面 Playwright 回归 + pageerror=0 后再提交。
4. D 类（AI 文本）未获明确指令前保持原样。

## 三、剩余 BACKLOG
- Emoji A/B 类分批线性化（建议顺序：index.html 剩余区 → architecture_dashboard → system_features_ui → v3_modules → 其余）。
- C 类业态线性图标集设计（与 topic type-tag、smart-icon 共用一套分类色板）。
- D 类 AI 文本 emoji 是否收敛，待产品决策。
- LEGACY CSS（#01 标注 8 个）逐页渲染回归后停用，沿 #02 继续。

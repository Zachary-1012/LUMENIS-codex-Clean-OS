# UI 审计 04 · index.html metric/integration 图标线性化 + ⚡ 全量清除

- 日期：2026-09-04
- 范围：`static/index.html`、`static/css/style.css`、`static/js/case_deep_analysis.js`
- 上游：UI_AUDIT_03_NAMING_ICON_EMOJI（emoji 四类分批清单）；本批 = A 类正式 UI 图标第 4 批
- 设计真相层：`static/css/zbip-tokens.css`（Stone Design Token）
- 代码提交：图标改动由 02:59 自动巡检收录于 `c266acd`（3 文件 20+/22-）；本审计文档单独提交

## 一、用户指令

用户明确「⚡改掉」，推翻 AUDIT_03 中"⚡ 作为 AI 资源标识保留 emoji 形态"的判断：**所有 ⚡ 闪电 emoji 一律改为线性 SVG，不保留 emoji 形态**；AI 资源包功能本身保留，只换图标形态。

## 二、本批改动（最小、只动视觉，不改 onclick / 数据 key / 检索逻辑 / AI 事实）

### 1. metric-icon 彩色 emoji → 线性 SVG（9 处，裸 svg 由 `.metric-icon svg` 全局样式自动继承）

| 位置 | 原 emoji | 线性图标 | 处理 |
|---|---|---|---|
| KOS 总数 | 👥 | users（人群） | 补 gray 中性 class |
| S级核心 | ⭐ (#e74c3c 内联红) | star | **清除内联硬编码彩色**，统一 gray |
| A级重点 | 📈 (#f39c12 内联橙) | trending-up | **清除内联硬编码彩色**，统一 gray |
| 潜力KOS | 💎 (#3498db 内联蓝) | diamond | **清除内联硬编码彩色**，统一 gray |
| 本月营销节点 | 🎯 (amber) | target | 保留 class（CSS 已 Stone 化） |
| 舆情日报 | 📅 (blue) | calendar | 同上 |
| 舆情周报 | 📆 (green) | calendar-check | 同上 |
| 舆情月报 | 📊 (amber) | bar-chart | 同上 |
| 舆情年报 | 📈 (purple) | trending-up | 同上 |

### 2. integration-icon 彩色 emoji → 线性 SVG（4 处）+ 容器彩色底 Stone 化

- 公司域名 🌐 → globe；推送邮箱 📧 → mail；运行代码(热更新) ⚡ → zap；场内品牌 🏪 → store。
- `style.css`：原 `.integration-icon.blue/green/purple/amber` 为 iOS 高饱和（#e3f2fd/#1976d2、#e8f5e9/#388e3c、#f3e5f5/#7b1fa2、#fff8e1/#f57c00），统一为浅米底 `#F5F5F4`(Stone-100) + 图标 `#57534E`(Stone-600)；新增 `.integration-icon svg{20px;fill:none;stroke:currentColor;stroke-width:1.8;round}`。

### 3. ⚡ 全量清除（4 处，全仓 static ⚡ 归零）

- index.html：AI 资源包弹窗标题（ai-pack-title，13px 内联线性闪电）、增强搜索按钮（裸 svg 走 `.action svg`）、运行代码 integration（见上）。
- case_deep_analysis.js：动态生成的"外部增强结果（search-std）"小标题，emoji → 14px 内联线性闪电，flex 对齐。

### 4. 顺带：周报"发邮件"按钮 📧 → 线性 mail（L1112 sendWeeklyEmail，onclick 不变）。

## 三、Evidence（真实测试，非推断）

- 静态：`node --check case_deep_analysis.js` 通过；index.html 大括号 303/303、style.css 975/975 配平；全 static `⚡` = 0；本批 12 个目标 emoji 在 index.html 归零。
- Playwright（1440×900@1.25，Basic Auth，networkidle）三视图回归：
  - KOS 传播主体：11 个指标块，emoji=0，svg=20；四卡统一中性灰底线性图标。
  - 报告中心：10 块，emoji=0，svg=16。
  - 系统设置·增项接口：2 块，emoji=0，svg=4；`.integration-icon` computed `background-color=rgb(245,245,244)`、`color=rgb(87,83,78)`、hasSvg=true、textContent 空。
  - 真实 pageerror = 0（已过滤浏览器 credentials 策略噪声）。
- 截图：Temp/reg_kos.png、reg_reports.png、reg_settings.png。

## 四、刻意保留 / 不在本批

- 单色线性文本符号 ☰✦✕✓✗⬇↻：currentColor 下即线条，保留。
- 🔴🟡🟢（9 个，L823/831）：`<option value="🔴">` 是**绑定入库的风险等级数据值**，改 value 会动数据语义，须与后端口径一起处理，C 类不动。
- 报告中心 page-hero 大标题 📊、报告预览 📄（页面/面板标题，非 metric-icon）：登记下一批。
- 右侧 AI 洞察浮层 💡⚠📚 等：由 frontend_enhancement / case_deep_analysis 动态渲染，A 类后续批次。

## 五、index.html emoji 进度

54（批次三末）→ **24（本批末，13 种）**。剩余：登录面板 📱🔐×4、option 数据值 🔴🟡🟢×9（不动）、功能按钮 🔍🧩📋×6、平台品牌 📕💬📢🎵×4（连同平台体系设计）、上传 📤×1。

## 六、Backlog（下一批 A 类）

1. 登录面板 emoji（📱🔐，含 L1776 JS 动态标题）线性化。
2. 功能按钮/面板标题：🔍×3、🧩×2、📋、📤，以及报告中心 page-hero 📊/📄。
3. 平台品牌图标 📕💬📢🎵：需连同 .ae-platform-icon 平台识别体系一起设计，不单独硬改。
4. 其余 JS 文件按 AUDIT_03 工作量表逐文件小批次：architecture_dashboard.js(60)、system_features_ui.js(58)、v3_modules.js(40)、frontend_enhancement.js(26)、modal_simplify.js(19)。

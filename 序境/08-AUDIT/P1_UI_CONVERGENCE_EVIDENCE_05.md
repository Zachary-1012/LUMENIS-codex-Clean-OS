# 序境 UI 收敛 Evidence #05（中英韩三语）

- 日期：2026-09-04
- 范围：static/js/xujing-i18n.js（新）+ static/index.html（渐进增强打标）
- 依据：《序境》母基线「中英韩」要求

## 一、落地

- 新建 `static/js/xujing-i18n.js`：轻量三语框架（zh/en/ko 字典 + 切换 + localStorage 记忆 + 浏览器语言探测）。
  - 全局 API：`window.xujingSetLang(lang)` / `xujingGetLang()` / `xujingT(key)` / `XUJING_I18N` 字典
  - 渐进增强：`[data-xujing-i18n]` 属性扫描替换，不重构现有 DOM/JS
  - 事件 `xujing:lang`（供动态渲染区联动）
- `static/index.html`：
  - 核心文案 10 处打标（品牌区 splash-title/tagline/subtitle + 状态卡 6 处 + topbar 标题）
  - 顶部语言切换控件（中/EN/한）
  - `</body>` 前加载 i18n 脚本
- 字典覆盖：品牌名（序境/XUJING/서경）、副标题、采集状态/风险预警/AI 引擎/运行中/监测中/就绪、快捷操作与导航核心（为后续扩展）。

## 二、验证（playwright 真实渲染）

- 默认语言 topbarTitle = `序境`（zh）
- 切换 ko 后 topbarTitle = `서경`（韩语）✓
- 语言控件存在，JS 无 pageerror
- 三语字典完整性：zh/en/ko 各 27+ key

## 三、边界与后续

- 本版为**三语能力基线**：静态品牌区 + 状态区 + 字典框架已三语化。
- 动态渲染区（zbip-shell 快捷按钮、导航 30+ 项）字典已提供 key，UI 打标按序境节奏分批扩展（P1/P2）。
- 与报告母模型 `language` 字段对接（报告三语输出）后续落地。

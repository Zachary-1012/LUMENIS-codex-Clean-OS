

---

## 2026-09-02 · UI 第二批精修层 zbip-refine（侘寂黑白灰 / 语义小圆点 / 移动重排，Staging 8301）

- **方式**：Strangler 新增最高优先级精修层 `static/css/zbip-refine.css`（最后加载），不改 22 个旧 CSS、不改加载顺序、不改业务 DOM；回滚 = 删该文件与其 `<link>`。仅在 Staging 8301 验证，**未合 main、未动生产 8201**。
- **已完成（已实测，Playwright 独立 chromium 双视口 1440×900 / 390×844）**：
  1. 风险类型彩色填充块 → 语义小圆点+文字：●高风险=红 / ●上升过快=橙 / ●高影响力=蓝（`.alert-type.risk/.rising/.influence::before`），桌面+移动一致。
  2. 手机风险页 `.alert-row` 单行横排改两行栅格（类型·状态·操作一行，标题+meta 一行），标题/meta 完整换行不再省略号截断，"标记已读"不再被右下浮动 badge 遮挡（内容区底部留 88px）。
  3. 手机 Home 覆盖层透出下层旧 page"幽灵字"修复：`#zbHome` z-index 300 + 实底；Ask textarea `overflow:hidden` 去原生上下滚动箭头、placeholder 两行完整可见；手机端隐藏与汉堡重叠的 refreshBtn。
  4. 旧蓝链/蓝文字收敛 stone：`.back-btn`、page-actions 描边按钮、`.alert-status` 全部黑白灰；侧栏旧 `.sidebar-toggle` 三横线折叠按钮在新 Shell 下隐藏（不删源码）；旧空分组标签 `.side-group-label`(ZACHARY OS AI) 隐藏。
  5. 侧栏分组补齐：键盘快捷键(kbShortcutsEntry)、驻场浏览器/内置浏览器/证据看板全部归入「系统」组，最终 6 组 = 总览/监测/分析/品牌资产/产出/系统，无游离项。
  6. 弹窗边缘极淡微光（modal-panel 弱阴影+内高光，仅桌面），分组间距/字距克制化。
- **顺带修复（非本层 CSS，已确认正确一并保留）**：index.html footer 后补 `</main>` 闭合（原 `<main class=content>` L148 缺闭合，right-panel 应在 main 外）。
- **测试**：全量 pytest 238 点全 `.` 无 F/E、exit=0；test_css_balance 通过；CSS 括号 44/44、注释配对；JS 括号平衡。DB schema/数据、五条红线主体口径、采集链零变更。
- **Evidence**：docs/UI/evidence/refine_audit/（desk_home/desk_risk/m_home/m_risk/m_drawer/final_desk_home）。
- **未完成 / 未实测（如实登记）**：
  - 430/768/1024/1280 断点本轮未逐档取图（仅 1440 与 390 实测）；风险预警侧栏红色 31 badge 略贴右缘，待微调。
  - 手机滚动到最后一条时浮动"采集健康"badge 仍可能轻微压标题（已留 88px，需真机滚动复核）。
  - 另一套空导航骨架（概览/品牌/监测/洞察/产出/系统，0 side-item，不在 .side-nav 内、视觉不可见）来源待查，暂不影响。
  - 本层与 Step3/Step4 同在 Staging，**尚未合 main**，等最终验收后一次性合并切生产。


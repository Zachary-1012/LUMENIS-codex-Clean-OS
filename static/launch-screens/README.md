# 启动封面（Launch Screens）· 当前不启用

本目录存放两套产品的**启动封面海报 + 密码登录示意**，为独立静态页，**当前未接入主系统、未被 `index.html` 引用**，不影响 8201 生产与 8301 Staging。可直接双击 HTML 预览。

## 目录与命名（遵循 docs/PRODUCT_NAMING_BASELINE.md）

| 产品 | 中文全称 | 英文全称 | 简称 | 文件 |
|---|---|---|---|---|
| CTH-POMS | 广州太古汇舆情监测系统 | CorTech Lab · Guangzhou Taikoo Hui Public Opinion Monitoring System | CTH-POMS | `cth-poms/desktop.html`（网页版）、`cth-poms/mobile.html`（手机版） |
| ZBMP | Z-Brand 品牌监测平台 | Z-Brand Monitoring Platform | ZBMP | `zbmp/desktop.html`、`zbmp/mobile.html` |

## 设计与交互（沿袭侘寂黑白灰产品风格）
- 黑/白/灰为主，无彩色泛滥；顶部 1px 启动进度线（约 1.1s），主名区淡入上移。
- 主视觉为正式全名（中文全称为主、英文全称次之、简称用极小描边胶囊），线性几何 mark，大量留白。
- **系统名 `Z-BRAND CORE` 缩小、居中、固定在页面最底部**（按需求）。
- 启动进度结束后（约 1.2s）浮现 **iOS 式居中密码登录弹窗**：材质白卡 / 手机版带背景模糊、圆角、弱阴影、淡入 + 轻微上移（`cubic-bezier(.22,1,.36,1)`，约 0.24–0.3s）；CTH 为访问密码、ZBMP 为访问密钥。
- 手机版针对 390/430 竖屏做字号/触控/安全区（`env(safe-area-inset-*)`）自适应，非简单缩放。

## 将来如何启用（暂不执行）
1. 由后端在未登录会话时先路由到对应封面，或在 `index.html` 最前置一层启动视图。
2. 把弹窗里的 `alert(...)` 示意替换为真实校验：CTH 走本地访问密码；ZBMP 走现有 `/v4/auth/workspace/unlock`（与 `zbip-shell.js` 密钥门同一接口）。
3. 校验通过后再加载主工作台；登录态有效期沿用现有 12 小时会话。
4. 启用前需补：密码/密钥的配置来源、失败态、忘记密码、键盘焦点与 Esc 关闭（对齐苹果"同一时刻只有一个模态"）。

## 待你拍板
- **ZBMP tagline 候选「品牌传播与市场情报平台」**：是否上封面、放在英文全称下还是工作区内，位置未定，故当前封面**未放入**，避免擅自定位置。
- 是否需要深色版封面（当前为浅色侘寂；主工作台日后若提供深/浅双主题，封面同步出深色）。

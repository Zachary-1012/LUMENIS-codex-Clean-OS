# 启动封面（Launch Screens）· 当前不启用

本目录存放 ZBIP 各系统的**启动封面海报 + 密码登录示意**，全部为独立静态页，**当前未接入主系统、未被 `index.html` 引用**，不影响 8201 生产、8200 与 8301 Staging。可直接双击 HTML 预览（`file://` 即可，无需起服务）。

命名遵循 `docs/PRODUCT_NAMING_BASELINE.md`：首次出现写中文全称 + 英文全称 + 简称。

---

## 一、两套方案并存（待拍板，互不覆盖）

### A. 浅色侘寂版（2026-09-01 下午，desktop / mobile 分离）
| 产品 | 网页版 | 手机版 |
|---|---|---|
| 广州太古汇舆情监测系统（CorTech Lab · Guangzhou Taikoo Hui Public Opinion Monitoring System，CTH-POMS） | `cth-poms/desktop.html` | `cth-poms/mobile.html` |
| Z-Brand 品牌监测平台（Z-Brand Monitoring Platform，ZBMP） | `zbmp/desktop.html` | `zbmp/mobile.html` |

- 暖白 `#FAFAF9` + stone 石色系，顶部 1px 启动进度线，全名为主、简称为极小描边胶囊，大量留白。
- 系统名缩小居中固定最底部；约 1.2s 后浮现 iOS 式居中密码弹窗（CTH 为访问密码、ZBMP 为访问密钥）。
- 手机版针对 390/430 竖屏做字号/触控/安全区 `env(safe-area-inset-*)` 自适应。

### B. 深色侘寂版（2026-09-01 晚，单文件响应式，覆盖全部 6 系统）
目录：`dark/`，共享 `dark/launch-common.css` + `dark/launch-common.js`，每个系统一个 HTML（自适应网页/手机，无需分开维护）。

| 系统 | 中文全称 | 英文全称 | 简称 | 文件 |
|---|---|---|---|---|
| 品牌业务生产平台 | Z-Brand Business Production Platform | ZBP | `dark/zbp.html` |
| 广州太古汇舆情监测系统 | CorTech Lab · Guangzhou Taikoo Hui Public Opinion Monitoring System | CTH-POMS | `dark/cth-poms.html` |
| Z-Brand 品牌监测平台 | Z-Brand Monitoring Platform | ZBMP | `dark/zbmp.html` |
| 研发工程治理中枢 | Development Command Console | DCC | `dark/dcc.html` |
| 智能研究学习中枢 | Intelligent Research & Learning Hub | SICI | `dark/sici.html` |
| 自主智能研发体 | Autonomous Intelligence Development | AI-D | `dark/ai-d.html` |

- 深墨底 + 胶片颗粒 + 暗角 + 灰白朦胧流动光斑（重庆森林式 bokeh，克制不彩色）。
- 中央呼吸大字（简称）+ 中/英文全称；周围 6 张倾斜漂浮「能力卡」，语义色只出现在小色点（green/amber/blue/gray，且同时有文字，不靠颜色单独表意）。
- 约 3.2s（或点击/按键跳过）后浮现 **iOS 式居中密码登录弹窗**：背景高模糊、圆角弱边框、淡入 + 轻微上移，桌面与手机都**页面居中**（非贴底 sheet）。
- 系统名缩小居中固定最底部；`prefers-reduced-motion` 下关闭动效。

> 与主系统 `static/css/splash.css`（CTH-POMS 现用启动海报 v2）同一设计语言，深色版是其多系统推广。

---

## 二、登录交互说明（当前均为前端示意，不做真实鉴权）

- 浅色版：`alert(...)` 示意；深色版：`dark/launch-common.js` 做「账号非空 + 密码≥4位」的前端演示校验，通过后进入占位页。
- **均不含真实密码、不校验真实身份**。将来启用时替换为后端鉴权：
  - CTH-POMS 走本地访问密码 / 现有 Basic Auth；
  - ZBMP 走 `/v4/auth/workspace/unlock`（与 `zbip-shell.js` 密钥门同一接口）；
  - 登录态有效期沿用现有 12 小时会话。

## 三、将来如何启用（暂不执行）
1. 后端在未登录会话时先路由到对应封面，或在 `index.html` 最前置一层启动视图。
2. 把前端示意校验替换为真实接口；补失败态、忘记密码、键盘焦点与 Esc 关闭（对齐苹果"同一时刻只有一个模态"）。
3. 校验通过后再加载主工作台。
4. 确定深 / 浅方向后，只保留一套，避免两套长期并存。

## 四、待你拍板
1. **方向**：用浅色侘寂（A）还是深色 GPT/Codex 工程感（B）作为正式启动页？
2. **ZBMP tagline「品牌传播与市场情报平台」**：是否上封面、置于英文全称下还是工作区内（当前两套均未放入，避免擅自定位）。
3. AI-D 英文全称暂定为 *Autonomous Intelligence Development*，如你有正式命名以你为准。

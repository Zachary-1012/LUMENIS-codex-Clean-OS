# 受控电脑与产品内浏览器：2026-10-08 有界取证

用途：当前蓝图/Experience/SYS-06的支持证据，非新增执行权威。
源码冻结基线：409e6d2c0fe0ae0bfb865b0795f9dfdf655d1703；local/origin/live一致。
保护工作树：本轮不改产品源码、生产DB或服务。其他已恢复Owner的新增工作分别保留。

## 用户输入与实际观看

原视频：ScreenRecording_10-08-2026 06-26-05_1.mp4；SHA256 `516721b6d9e98cf5418cdebe1016a17cdd7ae1f81b89a6caeba13c8a188f2890`；5980707 bytes；12.34秒；1206×2622；HEVC/AAC。
原件locator保留在现有MATERIAL-OWNER-MANIFEST，抽帧在repo外browser-video-20261008。
约0.5秒间隔检查完整12.34秒视觉流程及转换点，未逐个解码帧做人眼检查、未做音频听验。不是仅看封面，也不是全逐帧/声音研究完成声明。

| 时间 | 看见的事实 |
|---|---|
| 0–1.5s | Manus任务对话、返回/菜单、输入区和停止按钮；文字提及浏览器连接与Apple账户页 |
| 2–2.5s | 进入“Manus的电脑”，显示account.apple.com/account |
| 2.5–12.34s | 实际页面/网址、“操控浏览器”、当前动作“正在点击元素”、事件条/前后事件控件/Live；月份下拉框展开 |

没有演示：注册提交成功、浏览器tabs、地址编辑、浏览器历史前后退、外部打开、暂停恢复、通用OS控制。前后事件不是浏览历史。不能从画面推断底层是WebView或远程桌面。视频采用为体验/动线参考，`MODEL_TRAIN=NOT_GRANTED`，不复制第三方品牌/媒体资产。

## 源码事实与现有Owner

| 路径/位置（基线） | 观察 | 责任 |
|---|---|---|
| ai_browser_api.py:146/280/302/341/391/461/493 | 已有session/navigate/observe/action/verify/Evidence/stop入口 | C6 SYSTEM组合，C2调用 |
| ai_browser_runtime.py:75–92,1509–1560 | 已有click/input/select/scroll/keyboard等动作，Firewall/执行前后观察/verify/recovery/Evidence链 | C2/C6复用，不新建runtime |
| lumenis/system/browser/runtime/adapters/cdp_adapter.py:81–92; playwright_adapter.py:168–178 | 已有click/type基础 | C6复用，C1消费 |
| app/lib/features/system/sys06/sys06_screen.dart; sys06_browser_repository.dart:27–138 | 前端readonly，只用navigate/reload/frame；不接click/type/scroll | F与C6 |
| app/lib/core/lumenis_core_client.dart:856–861 | 非loopback Core报BROWSER_LOCAL_CORE_REQUIRED | C6/F补安全远端绑定，不直接删防护 |
| SYSTEM/Shared/app定向OS executor检索 | 未发现通用OS鼠标键盘/应用执行器；浏览器控制不能替代它 | C2/C6在原Agent/SYSTEM Owner闭合此真实缺口 |

当前是SOURCE/PARTIAL；未运行产品浏览器、未操作账户/OS或验证三端运行。SourceTarget v1目前是外部launch兼容路径；新默认内部浏览的源/调用/合同须F/C6同改。旧只读Reader保持当前源事实，不能作为拒绝用户新要求的终态上限。

## 定向官方研究与采用

- [MDN frame-ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors)（2026-10-08读取）：站点规定可嵌入的父来源；ADAPT为Web工作区呈现获准SYSTEM浏览器画面/动作，不依赖任意站点iframe，也不移除第三方CSP。
- [InAppWebView官方说明](https://inappwebview.dev/docs/webview/in-app-webview/)与[ChromeSafariBrowser](https://inappwebview.dev/docs/in-app-browsers/chrome-safari-browser/)（同日读取）：嵌入控件、原生浏览器视图及系统Custom Tabs/SafariController的行为不同。DEFER新增插件；已有产品服务足以作为首选接线基础，若真正缺原生能力再核实际版本、许可和同一session边界。没有安装插件或声称其跨端能力已在序境生效。

## 本次纠偏

原全局暂停仅验证到F窗口转述，没有取得可确定全局适用范围的PO原话。M据此暂停巡检属于处理不当。最新PO直接指出暂停错误并要求继续，已恢复各原生Goal及七窗口，保留手选模型与普通速度。今后局部暂停不可自行扩大，直接PO停止仍立即遵守。

完成标准归Overlay与SYS-06：真实产品执行→实际可见/可操作结果→权限与控制权→取消/恢复→同任务返回→Evidence；OS与browser、三端各自证明，开发工具代操作不通过。

## 本批规则验证

六项当前必需规则/Experience门禁通过；发布分类的13项针对性治理回归通过。修复规则-only分类只认可Markdown而漏掉两个既有材料/设计目标JSON的问题，仅新增两个exact path；运行配置及其他JSON仍被拒绝。审批receipt使用既有批准来源枚举。没有删除/跳过测试或降低产品验收。对保护工作树使用既有隔离验证副本；其他Owner产品改动未暂存。本批尚不构成产品Browser/OS运行通过或same-SHA线上CI通过。

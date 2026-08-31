# BROWSER-RESEARCH · 浏览器自动化与合规拟人研究

> 来源：Playwright（LR-014）、Selenium（LR-015）、Crawlee（LR-016）一手对比，2026-08-31。
> **合规红线（最高）**：研究拟人化是为了"正常业务监测下减少误伤、降低无效请求"，**绝不**用于破解验证码、绕过安全验证、对抗风控或伪造登录。出现验证/300012/IP 风险一律识别→停→熔断→冷却→合法人工验证→恢复。

## 1. 框架对比结论
- **Playwright Python 为主**：自动等待、网络拦截、多 context 隔离、trace、持久化 storageState、官方 CI/Docker。
- Selenium：本仓 0 真实 import，DEPRECATED 候选，Staging 回归后才退出依赖，不现在删。
- Crawlee：学 RequestQueue（去重/重试队列）、AutoscaledPool（按反馈调并发）、SessionPool 隔离——映射到平台独立状态机，不引框架。

## 2. 持久会话与"9222/9223 真人登录一次、Profile 长期复用"
- 用独立用户数据目录（edge-cdp-profile）启动远程调试端口，人工登录一次；自动化通过 CDP 附着，**不读取/导出 cookie 明文**，cookie 由 cookie_vault 加密落盘、不进源码/日志/库。
- 每个平台独立 BrowserContext（独立 cookie jar/cache/会话），实现平台隔离；一个平台熔断不影响其他。
- 反检测只做"去掉自动化标志位的正常化"（如 navigator.webdriver 常态、一致 UA/视口/语言/时区），不做指纹伪造或风控对抗。
- 修复 `-disable-blink-features=AutomationControlled` 不受支持告警：用 Playwright 原生 launch/context 参数与合法 args，不依赖已废弃标志；以真实页面验证为准。

## 3. 拟人化（降低误伤，非绕风控）
- 操作节奏：人类分布延迟（非固定 sleep）、鼠标移动/滚动/聚焦、输入逐键、动作间随机停顿；设置全局速率上限与每日安全上限。
- 页面行为：先等选择器/网络空闲再操作；失败优先回退、不连续重试；单次运行时长固定（XHS 自动≈30min/手动≈20min 为历史参考、非硬编码次数）。
- 按需启动：空闲关闭浏览器、任务到来再附着复用 profile，减少重复浏览器启动（效率+低痕迹）。

## 4. 资源/连接复用
- 浏览器实例复用、context 按平台复用；HTTP 连接 keep-alive；静态资源可拦截非必要请求（图片/字体按任务）降负载，但不破坏页面正常功能。
- 采集与分析解耦：采集器只做发现→获取→解析→标准化→质检→入库；主体/事件/风险/AI 属后续层，AI 不决定是否继续请求平台。

## 5. 风险信号识别与处置（状态机，详见 ARCHITECTURE-PATTERNS P4）
- 识别：验证页/验证码/安全验证/300012/IP 风险/限制页/登录失效。
- 处置：立即停危险请求 → 记录状态与证据 → 熔断/冷却 → 健康检查 → 平台提供的合法验证入口（统一 Auth 弹窗内二维码/入口）→ 小流量恢复。
- 三类分清：A 登录失效=弹码；B NEED_VERIFY/CAPTCHA=提示人工验证；C IP_RISK/300012=熔断冷却（不能伪装成扫码可解，更不能伪装 0 条）。

## 6. 证据
- CDP target 列表、关键页面截图、网络响应状态码入 Evidence（L8）；不记录任何 cookie/token 值。

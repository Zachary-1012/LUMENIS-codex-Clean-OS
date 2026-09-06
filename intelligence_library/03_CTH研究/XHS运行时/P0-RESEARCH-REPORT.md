# P0 小红书 Resident AI Browser Runtime｜研究报告

> **状态：ACTIVE**｜2026-09-02｜完整研究报告（执行摘要、核心决策、14 问题、12 方向、边界、契约）

---

## 一、执行摘要与推荐架构

```
Resident XHS AI Browser Runtime
├── AI Agent Layer（Browser Use 范式 / Plan-and-Execute / 三级失败降级）
├── Browser Layer（Playwright Persistent Context / User Data Directory / CDP 接管 / stealth 三层补丁）
├── Identity Layer（双 Browser Context 硬隔离：Human + AI）
├── Auth Layer（系统内模态弹窗 / 8 级权限粒度 / 三档有效期 / 授权记录签名+审计哈希链）
├── Security Layer（五层 PI 防御 / 输出层硬编码过滤 / 能力白名单 / Circuit Breaker）
├── Collector Layer（常驻采集 / 优先级调度 / 自适应速率 / 三层去重 / 断点续采）
├── Evidence Layer（确定性自动产生 / 截图+DOM快照+哈希链+Merkle Tree+RFC3161+WORM）
├── Health Layer（独立 Watchdog / 三重假死检测 / 五级分级自愈 / 指数退避+熔断）
└── Data Layer（双轨：官方渠道灵犀/蒲公英/聚光 + 浏览器渠道公开UGC ≤200次/天/账号）
```

## 二、核心决策表

| 决策域 | 推荐方案 | 标签 |
|---|---|---|
| Browser Runtime | Playwright (Chromium) + launchPersistentContext + stealth 三层补丁 | ADOPT |
| Session 持久化 | User Data Directory（主）+ 加密 storageState（备份） | ADOPT |
| 小红书签名 | CDP 接管真实浏览器，页面 JS 原生计算 x-s | ADOPT |
| 双身份 | Human Context + AI Context 双 Browser Context 硬隔离 | ADOPT |
| 第三身份 | 硬拒绝（类型约束+Registry冻结+网络拦截+白名单+审计） | ADOPT |
| Auth Modal | 系统内模态弹窗，8 级权限，三档有效期 | ADOPT |
| AI Browser 框架 | Browser Use 范式 + Plan-and-Execute | ADOPT |
| PI 防御 | 五层防御，核心输出层硬编码过滤 + 执行层白名单 | ADOPT |
| Evidence | 确定性自动产生，哈希链+Merkle+RFC3161+WORM | ADOPT |
| Health | 独立 Watchdog + 五级分级自愈 + 断点续采 | ADOPT |
| 长驻测试 | 24h/72h/7d 三级，含故障注入 | ADOPT |
| 官方能力 | 企业专业号+灵犀平台；商业走蒲公英/聚光 | ADOPT |
| Electron | 过度设计（200MB+，单线程瓶颈） | REJECT |
| 纯 JS 逆向 x-s 签名 | 维护成本极高，算法频繁更新 | REJECT |
| 账号轮换/指纹伪装 | 违反平台规则，极验已可识别指纹浏览器 | REJECT |
| 无限制 AI 自主操作 | PleaseFix 漏洞证明系统性安全风险 | REJECT |
| Browserless | 灾备备选，需评估数据中心 IP 风险 | RESEARCH_MORE |
| xiaohongshu-mcp | 2026 平台收紧 AI 托管后需评估风险 | RESEARCH_MORE |
| 区块链上链 | 成本性能需评估，当前时间戳服务已足够 | RESEARCH_MORE |

## 三、14 个 P0 判断问题答案（摘要）

1. **Browser Runtime**：Playwright (Chromium) + launchPersistentContext。Auto-Waiting 与 Context 隔离是长驻稳定基础；Electron 过度设计。
2. **登录长期保存**：双层持久化——User Data Directory（主，指纹一致）+ 加密 storageState（备份，灾难恢复）。web_session Max-Age=1 年但受服务端控制，xsec_token 约 2h 可自动刷新。
3. **扫码弹窗时机**：预触发模式——xsec_token 剩余 <10min 时后台准备二维码并通知用户，扫码成功后热切换 Session，超时 5min 关闭扫码页不中断采集。
4. **Session 失效判断**：多信号融合——最高 `/me` 返回 guest:true；高 401+重定向+业务错误码；中 xsec_token 过期（可刷新）；低 403/验证码（可能是风控，需降频冷却）。关键：风控触发 ≠ Session 失效。
5. **双身份隔离**：Browser Context 级硬隔离，AI 短期 JWT（TTL≤15min）不复用人类 Session，拦截器强制 X-AI-Identity 头，跨 Context 访问被 E_CROSS_CONTEXT_LEAK 拦截。
6. **第三身份硬拒绝**：五层强制（TS 类型约束 + IdentityRegistry Object.freeze + 网络拦截 + 服务端白名单 + 审计）。
7. **AI Browser 边界**：白名单内动作（navigate/scroll/click/read/search/like/favorite/comment/follow 需审批）；硬禁止 publish/dm/account_settings/cookie_read_export/session_export/eval_js/inject_script/modify_whitelist 等。
8. **PI 隔离**：五层防御，输出层硬编码规则过滤最可靠（研究验证 15000 次攻击零泄露），不信任模型能抵抗 PI，用确定性工程边界兜底。
9. **假死发现**：独立 Watchdog 进程（不跑在浏览器事件循环内）三重检测：CDP 心跳 + 资源监控 + 操作响应时间。
10. **Crash 恢复**：五级分级——L1 刷新页 → L2 重建标签页 → L3 重建 Context → L4 重启浏览器 → L5 重建 Session（需人工扫码）；指数退避 + 熔断（1h>5 次停止自动恢复）。
11. **Evidence 产生**：采集执行层确定性自动产生（不经 LLM）：截图+DOM 快照+URL+时间戳+操作日志+环境信息，SHA-256 哈希链+Merkle+RFC3161+WORM。
12. **长驻测试**：24h（每5min，内存增长<200MB）/72h（每2min+故障注入，自愈≤2次）/7d（混合负载，自愈≤5次，无 Profile 损坏）。
13. **OSAI/ZBC 边界**：OSAI 交付 Research/架构/接口契约/测试契约/决策/案例库；ZBC 负责实现/测试/E2E/CI/Release；OSAI 不改 ZBC 生产代码。
14. **Carter 下一步代码**：13 项施工清单，优先 P0（Playwright 启动器 → SessionManager → 双 Context → IdentityManager → Auth Modal → Security 三层 → HealthMonitor → Evidence Collector）。

## 四、12 方向关键发现（摘要）

- **01 Resident Browser**：Playwright 唯一同时满足长驻稳定+持久化 Session+反检测兼容。已知 21h 虚拟内存 24GB OOM，靠自愈体系治理。
- **02 Session 生命周期**：web_session 首次加载即为访客设置，**不是登录信号**——需 `/me` guest:false 确认已登录。xsec_token 约 2h，可自动刷新。异地登录秒级失效。禁止多 Session 备份轮换。
- **03 双身份模型**：AI Context 用短期 JWT（TTL≤15min）而非长期 Cookie；AI 独立限流 qps=2/daily=500；AI 禁止动作硬编码。
- **04 Auth Modal**：参考 OAuth2 Consent Screen + macOS TCC + iOS ATT。授权疲劳保护：同一权限 5min 拒绝 3 次后冷却 30min。持久级授权 P0 不开放。
- **05 AI Browser**：Collector 的智能执行层而非独立组件；首次访问 AI 决策，结构稳定后降级确定性执行；证据/速率控制永远确定性代码。
- **06 AI Browser 安全**：OWASP LLM Top10 2026 PI 连续三年榜首（7714 起 AI 安全事件）；模型层防御不可靠（Gemini/GPT 10 轮内完全披露），唯一可靠防线是输出过滤（15000 次攻击零泄露）；PleaseFix 漏洞证明自主代理系统性风险。
- **07 Collector 2.0**：自适应速率（429/验证码/延迟突增/内容异常）；COOLDOWN 全局暂停；三层去重（URL 规范化+Bloom Filter+SimHash）；优先级 P0>P1>P2。
- **08 Evidence**：绝不包含 Cookie/Token/Session；页面内容视为不可信数据；冷热分层（热30天/温1年/冷归档）；普通保留 2 年，维权争议永久。
- **09 Health**：Watchdog 必须独立进程；五级恢复最小干预；熔断阈值需长驻数据调优；L3 Context 迁移采集任务为 P1 挑战。
- **10 XHS Intelligence**：x-s+x-s-common 双层混淆，纯逆向不可维护；CDP 接管真实浏览器（MediaCrawler 53K stars 验证）为最佳实践；三层风控（网络/设备/行为）；2024-2026 半年封禁超 1000 万黑灰产账号。
- **11 官方能力**：小红书**没有面向公众的通用内容数据开放 API**；官方能力分散在四平台（开放平台 SDK/专业号 600元年/蒲公英/商家平台聚光+灵犀洞察 2025.8 全量免费）；双轨数据架构：官方优先+浏览器补充公开 UGC。
- **12 案例**：22 个案例。ADOPT Browser Use（97K stars）+ MediaCrawler（53K stars）+ Playwright persistent context；ADAPT OpenClaw（31.5K）+ BrowserAct + Crawl4AI；REJECT 纯 JS 逆向/账号轮换/无限制 AI 自主。

## 五、OSAI/ZBC 边界与实施契约（摘要）

- **接口契约**：IResidentBrowser / ISessionManager / IIdentityManager / IAuthModalService / IAIBrowserSecurity / IHealthMonitor / IRecoveryOrchestrator / IEvidenceCollector + Data Model + 20+ 错误码 + 6 状态机 + Policy 规则
- **测试契约**：Unit / Integration / E2E / Security-RedTeam / Long-run（24h/72h/7d）
- **OSAI 不得**：修改 ZBC 生产代码、提交生产 PR、运行生产环境
- **ZBC 不得**：修改架构决策、绕过安全约束、修改身份白名单/Policy/Circuit Breaker

## 六、开放问题与研究 Backlog（摘要）

- **P0**：headed vs headless 反爬差异 / xsec_token 刷新端点 / AI Context 登录态 / CDP 特征检测 / Browser Use 实际成功率 / 内存泄漏根因
- **P1**：扫码热切换 / L3 Context 迁移 / 持久级授权 / Output Filter 小模型 / 多模态 sanitize / xiaohongshu-mcp 可用性
- **P2**：Skyvern CV 对比 / 区块链上链 / 多 Agent Context 方案 / 预触发窗口调优 / 熔断阈值调优

---

**P0 状态：ACTIVE** — 研究阶段完成，ZBC 可同步启动施工（13 项清单，优先 P0 项）。

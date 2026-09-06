# GitHub 行业标杆学习记录 · 2026-09-02（边开发边学习）

> 来源：GitHub live search（browser-use / agent-security / browser-automation 维度）
> 用途：OSAI 学习进化 → ZBC browser_runtime / 安全模块施工参考
> 归属：AI Frontier（Agent Browser + Agent Security）

---

## 一、Browser Agent 基础设施标杆

| 项目 | Stars | 语言 | 关键点 | 与 ZBC 相关性 |
|---|---|---|---|---|
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | 112k | Python | 从 Playwright 封装转向**直接 CDP 实现**降低开销；持久化 profile | **高**：与 ZBC browser_runtime/cdp_adapter 同方向，CDP 优先 |
| [bytedance/UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop) | 38.8k | TS | 多模态 AI Agent 栈（vision + VLM + computer-use） | 中：Agent 栈参考 |
| [jackwener/OpenCLI](https://github.com/jackwener/OpenCLI) | 28.9k | JS | 用登录态浏览器 + CLI 方式调用网站 | 中：登录态复用思路 |

## 二、Agent 安全标杆（OSAI 学习摘要 ADOPT 方向实证）

| 项目 | Stars | 语言 | 关键能力 | 施工参考 |
|---|---|---|---|---|
| [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) | 15.6k | Python | Agent skills 安全扫描：恶意模式/prompt injection/数据外泄/供应链风险 | **高**：ZBC security_scanner.py 增强参考 |
| [luckyPipewrench/pipelock](https://github.com/luckyPipewrench/pipelock) | 828 | Go | AI agent 防火墙：MCP/A2A/WebSocket 流量扫描 SSRF + prompt injection + 签名审计 receipts | 中：evidence 审计链参考 |
| [secureagentics/Adrian](https://github.com/secureagentics/Adrian) | 555 | Python | AARM 运行时 agent 安全：恶意工具调用/prompt injection/policy drift 实时拦截 | 中：Agent Policy Engine 参考 |
| [arcjet/arcjet-js](https://github.com/arcjet/arcjet-js) | 682 | TS | prompt injection 检测 + tool 授权 + 敏感数据脱敏 + 速率限制 | 中：与 intelligence.redact_for_cloud 同思路 |

## 三、对双子库的施工启示（ADOPT/ADAPT）

1. **browser-use 的 CDP 优先转向** → 验证 ZBC browser_runtime/cdp_adapter 方向正确（CDP over Playwright），无需回退。
2. **SkillSpector 静态扫描思路** → 增强 ZBC security_scanner.py：扫描 Agent skill/plugin 目录的 prompt injection 风险模式（OSAI 学习摘要 2.2 项：沙箱+权限为唯一硬防线，输入过滤仅辅助）。
3. **Adrian 运行时拦截** → browser_runtime/policy.py 已实现白名单 Policy Gate，可对照 AARM 思路补"工具调用授权 + 策略漂移检测"。
4. **arcjet 敏感数据脱敏** → 对照 intelligence.redact_for_cloud 的 REDACT_PATTERNS，验证覆盖完整性。
5. **pipelock 签名审计 receipts** → 对照 ZBC evidence_store 的证据链，评估是否需要"外部签名"增强（P1 评估项）。

## 四、决策标注

- browser-use CDP 路线：**ADOPT（方向验证，维持现状）**
- SkillSpector 静态扫描：**ADAPT（纳入 security_scanner 增强候选）** ｜ P1
- Adrian 运行时拦截：**RESEARCH_MORE（对照 policy.py 评估差异）** ｜ P1
- arcjet 脱敏覆盖：**VERIFY（对照 redact_for_cloud 清单）** ｜ P1

*双子星边界保持：OSAI 只研究/判断，不直接修改 ZBC 生产代码。*

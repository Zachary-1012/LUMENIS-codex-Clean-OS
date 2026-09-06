# P0 安全隐患评估：前端硬编码 Basic Auth 凭证

**发现日期**：2026-09-02
**严重度**：🔴 P0 高危
**来源**：双子库全量审计（Shard 3 前端审计）+ 全面核实
**状态**：立即缓解已执行（sessionStorage），完整修复待确认

---

## 一、隐患详情

### 1.1 实际硬编码范围（全面核实后，约 27 处，10 个 JS 文件 + index.html）

| 文件 | 处数 | 行号 | 说明 |
|------|------|------|------|
| static/index.html | 2 | L1050, L1052 | 内联脚本 `window.__Z_AUTH` + 凭证存储（**已缓解：localStorage→sessionStorage**） |
| static/js/app.js | 3 | L18, L65, L1348 | `_auth` 常量 + `api()` 函数 + `exportReportWithVerify()` |
| static/js/architecture_dashboard.js | 8 | L31, L147, L289, L339, L364, L431, L456, L599 | 架构面板多个 API 调用 |
| static/js/badge_manager.js | 7 | L67, L85, L155, L178, L201, L225, L249 | 徽章管理多个 API 调用 |
| static/js/case_deep_analysis.js | 1 | L9 | 案例深度分析 |
| static/js/frontend_enhancement.js | 1 | L10 | 前端增强 |
| static/js/system_controls.js | 1 | L10 | 系统控制 |
| static/js/system_features_ui.js | 1 | L326 | 系统功能 UI |
| static/js/v3_modules.js | 1 | L8 | v3 模块 |
| static/js/zachary_system_knowledge.js | 2 | L124, L137 | 系统知识库 |
| **合计** | **~27** | - | **10 个 JS 文件 + index.html** |

### 1.2 风险分析

- **凭证泄露**：任何能访问前端页面的用户都能在浏览器"查看源代码"中看到明文凭证
- **持久化存储**：凭证以 Base64 编码存入 localStorage（**已缓解为 sessionStorage**），XSS 攻击可窃取
- **无法轮换**：凭证硬编码在 10 个文件中，轮换需要修改 27 处代码并重新部署
- **多入口重复**：27 处独立硬编码，维护不一致风险高
- **审计报告低估**：原审计报告仅标记 3 处，实际核实为 27 处

### 1.3 现有设计权衡

代码注释说明这是为了"401 修复"——避免浏览器原生弹登录框，提升 UX。在本地/内网部署场景下有合理性，但安全隐患真实存在。

---

## 二、已执行的立即缓解（2026-09-02）

### 缓解 1：localStorage → sessionStorage（已完成，已推送 bfde2f5）

- **改动**：static/index.html L1052 `localStorage.setItem` → `sessionStorage.setItem`
- **效果**：凭证在关闭浏览器标签页后即清除，不再跨会话持久化
- **风险**：极低，不影响同一标签页内的功能
- **验证**：git diff 确认，已推送远端

---

## 三、完整修复方案（待用户确认）

### 方案 A：统一凭证来源 + 构建时注入（推荐，短期）

1. 所有 JS 文件从 `window.__Z_AUTH` 读取凭证（而非各自硬编码）
2. index.html 的 `window.__Z_AUTH` 从后端配置动态注入（或构建时环境变量替换）
3. 移除 27 处硬编码，统一为 1 处注入点
4. sessionStorage 保留作为兜底

**工作量**：约 1-2 小时（修改 10 个 JS 文件）
**优点**：凭证不硬编码在代码仓库中，可轮换，维护统一
**缺点**：仍在前端运行时可见（但这是 Basic Auth 机制的固有特性）

### 方案 B：后端 token 机制（推荐，中期）

1. 后端新增 `/api/auth/token` 端点：验证 Basic Auth 后返回短期 session token（JWT，TTL 24h）
2. 前端启动时调用 `/api/auth/token` 获取 token，存入 sessionStorage
3. 所有 API 调用使用 `Authorization: Bearer <token>` 而非硬编码 Basic Auth
4. token 过期自动重新获取（使用浏览器原生 Basic Auth 弹窗或登录页）

**工作量**：约 3-4 小时（后端 + 前端改造）
**优点**：凭证不硬编码、可轮换、短期 token 降低泄露风险、可审计
**缺点**：需要后端改造，中等工作量

### 方案 C：维持现状（不推荐）

- 仅保留 sessionStorage 缓解，不做进一步改造
- 风险：27 处硬编码仍存在，凭证仍在前端源码中可见

---

## 四、建议执行顺序

1. **已完成**：方案 C 立即缓解（sessionStorage）✅
2. **短期（待确认）**：方案 A（统一凭证来源 + 构建时注入）—— 1-2 小时
3. **中期（待确认）**：方案 B（后端 token 机制）—— 3-4 小时

---

## 五、红线检查

- [x] 不修改 SUBJECT_WORDS / 排除词 / subject_hit 权威
- [x] 不删除生产 DB
- [x] 不输出真实密钥值（本评估中凭证值已脱敏为 `***`）
- [x] 不改变现有认证流程的功能（缓解后仍需 Basic Auth 才能访问）
- [x] AI 是增强层非生命线（本修复不涉及 AI 链路）
- [x] 已执行的缓解（sessionStorage）不影响前端功能

---

*本评估待用户确认完整修复方案后执行*
*立即缓解已推送 ZBC bfde2f5*

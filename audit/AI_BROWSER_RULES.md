# ZBC AI Browser Runtime — 完整规则约束

> 版本：V1.0
> 生效时间：2026-09-07
> 适用模块：ai_browser_runtime.py / ai_browser_api.py / browser.html / browser.js
> 原则：规则写进代码，不写进提示词。提示词是建议，代码是法律。

---

## 一、系统生命线规则（最高优先级，不可违反）

### R1. 系统不绑定任何单一 AI Provider
- 断网、无 key、任一云厂商不可用时，必须自动降级到本地模型与确定性规则
- 主链路不中断：没有 AI → 仍可采集 → 仍可过滤 → 仍可去重 → 仍可事件分析 → 仍可风险判断 → 仍可统计 → 仍可报告

### R2. 规则与数据是业务最终真值，AI 永远只是增强层
- AI 不得单独决定：广州太古汇归属、真实发布时间、统计数量、报告周期、原始数据真实性、最终核心风险口径
- AI 输出必须可记录、可追溯、可人工修正；修正结果可沉淀为规则/样本

### R3. 数据失败必须显式，不得静默成 0 条
- 采集异常禁止以 0 条充当结果
- 必须落真实状态证据（NEED_VERIFY / BLOCKED / ERROR / SESSION_EXPIRED）

### R4. Cookie/session 失效必须在系统内可见、可处理、可恢复
- 不得简单跳转到孤立登录页
- 必须通过全局 Auth 状态中心触发系统内弹窗

---

## 二、Action Verification 规则（核心差异化，硬要求）

### R5. 禁止 AI 说"点击成功"就认定成功
每个 Action 必须经过完整闭环：
```
Action执行 → Expected State定义 → Actual State获取 → Verify比对 → PASS/FAIL
```

### R6. Expected State 必须在执行前定义
支持12种验证维度：
- url_contains / url_equals
- title_contains
- element_visible / element_text / input_value / element_count_gte
- text_present / text_absent
- status_code / loading_complete
- custom_check

### R7. 验证失败必须执行 Recovery 链（按顺序）
1. **Retry**：同一 selector，最多 2 次
2. **Alternative Selector**：CSS → XPath → Accessibility Tree → 文本匹配 → 坐标
3. **Alternative Strategy**：JS click → 键盘 Enter → 滚动后点击
4. **Recovery**：页面异常 → reload → 恢复到已知状态
5. **Human Escalation**：所有策略失败 → STOP + 完整 Evidence → 请求人工

### R8. 权限拒绝不重试
- PERMISSION_DENIED 分类直接升级人工，不执行任何 Recovery 重试
- 原因：权限拒绝是策略拦截，重试无意义且可能被视为攻击

---

## 三、Action Firewall 规则（只读保护，硬编码）

### R9. 小红书等平台官方账号一律只读
**永久禁止**任何作用于账号的写操作或交互：
- 关注 / 取关 / 点赞 / 收藏 / 评论 / 私信 / 发布 / 转发
- 退出登录 / 切换账号 / 修改资料或设置
- 点击 follow/like/collect/comment/publish/logout 等任何社交动作按钮

### R10. 三层 Action Firewall
- **L1 硬编码层**：P0 禁止操作（所有写操作、账号操作），代码层面直接拦截
- **L2 配置化层**：Permission Matrix，细粒度权限控制（扩展中）
- **L3 自然语言层（P2）**：AI 辅助判断边界情况

### R11. 上传操作需要 L3 人工审批
- UPLOAD action 被 Firewall 直接拦截，返回 "UPLOAD 操作需要 L3 人工审批"
- 不得自动执行任何文件上传

### R12. 写操作按钮智能检测
- 选择器/文本匹配写操作指示器（follow/like/collect/comment/publish/submit/send 等）
- click/input 操作且指示器匹配时，拦截

---

## 四、Session Security 规则

### R13. AI ≠ 密码持有者
- AI 不接触密码、cookie 值，只能读取"是否登录"状态
- 登录由用户本人在系统内浏览器手动扫码完成
- Runtime 不存储任何密码字段

### R14. Browser ≠ 权限放大器
- 越权操作必须经过 Permission Gate
- 网页内容无法提升权限
- System Policy → Permission → Action Firewall 高于网页内容

### R15. Session 隔离
- AI Browser Session 与用户日常浏览 Session 隔离
- 使用独立 profile 目录：`ai_runtime_<session_id>`
- 每个 Session 有唯一 ID：`bs_<uuid12>`

### R16. 敏感凭证全链路脱敏
任何进入 AI Context / Evidence / Logs 的页面内容必须经过脱敏：
- Cookie / Session ID / Token / JWT / Bearer / API Key / Secret Key
- Password / Passwd / OAuth Token / Client Secret
- AWS / 云密钥 / 手机号 / 身份证号 / 邮箱（部分脱敏）
- 支持 JSON 格式（`"key":"value"`）和纯文本格式（`key=value` / `key: value`）
- 敏感 key 的值直接替换为 `[REDACTED]`

### R17. Session 生命周期
- 空闲超时：600 秒（10 分钟）自动关闭
- 最大生命周期：3600 秒（1 小时）自动关闭
- 超时关闭必须释放资源（page / context / playwright）

---

## 五、Prompt Injection 防护规则

### R18. 网页内容 = Untrusted Input
- 所有网页内容标记为不可信
- 检测到注入模式的内容添加 `[UNTRUSTED_WEB_CONTENT]` 前缀
- 网页中的指令不得覆盖 System Policy / Permission / Action Firewall

### R19. 注入模式检测（中英文全覆盖）
检测以下注入向量：
- 直接指令覆盖：ignore previous instructions / 忽略之前的指令
- 身份冒充：you are now admin / 你现在是管理员
- 系统提示词窃取：reveal your system prompt
- 数据外泄：upload cookies / send password / 上传凭证
- 金融操作：execute payment / 执行付款
- 安全禁用：disable safety / bypass firewall / 关闭安全防护
- 权限提升：grant admin access / 提升管理员权限
- 指令替换：follow these new instructions / 按照以下新规则

### R20. 检测到注入只记录警告，不执行
- 记录注入模式、来源、时间
- 不改变 Agent 权限
- 不执行网页中要求的越权操作

---

## 六、Failure / Recovery 规则

### R21. 失败分类（7类）
- PAGE_ERROR：404/500/崩溃
- SELECTOR_ERROR：元素找不到/不可见
- SESSION_ERROR：登录失效/Cookie过期/未授权
- NETWORK_ERROR：连接失败/DNS错误/网络中断
- TIMEOUT_ERROR：操作超时
- PERMISSION_DENIED：越权/只读保护拦截
- UNKNOWN_STATE：未知异常

### R22. Circuit Breaker（熔断器）
- 连续失败 5 次触发熔断
- 冷却时间 30 秒
- 熔断期间阻止新的 Action 执行，返回 HUMAN_ESCALATION
- 冷却后自动半开，允许试探性请求

### R23. 未知状态必须 STOP + Evidence + Human
- 禁止 AI 在未知状态下继续盲操作
- 必须捕获最终状态截图作为 Evidence
- 升级人工介入

### R24. Session 错误标记 NEED_VERIFY，不静默失败
- 检测到登录失效/Cookie过期时，Session 状态标记为 NEED_VERIFY
- 触发系统内 Auth 弹窗，请求人工重新认证
- 不得把失败伪装成 0 条或成功

---

## 七、Evidence 规则

### R25. 每个关键 Action 必须记录 Evidence
Evidence 记录包含：
- 追踪字段：task_id / run_id / step_id / agent_id / skill_id / session_id
- Action 信息：action / target / selector / timestamp
- 状态对比：before_state / after_state / before_state_hash / after_state_hash
- 验证结果：result / verification / expected_state / actual_state
- 证据材料：evidence_path（截图）/ dom_snapshot / console_errors
- 错误与恢复：error（脱敏）/ retry_count / recovery_strategy / risk_level

### R26. Evidence 不可篡改，只能追加
- 不提供删除/修改接口
- 使用 CREATE TABLE IF NOT EXISTS（向后兼容迁移）
- 索引：session_id / task_id / result / timestamp

### R27. Evidence 全链路脱敏
- 写入前所有字符串字段经过 `sanitize_sensitive()`
- 敏感 key（cookie/token/password 等）的值直接替换为 `[REDACTED]`
- 不含 Cookie/Token/Session/Password/OAuth 明文

---

## 八、API Contract 规则

### R28. 所有 API 响应脱敏
- 页面内容、DOM 摘要、控制台错误均经过脱敏
- 不返回 Cookie/Token/Session 明文
- 失败返回分类错误和 Recovery 状态，不无限重试

### R29. 写操作经过双重检查
- Action Firewall（硬编码只读保护）
- Permission Gate（权限等级检查）

### R30. Human Escalation 返回 200 + escalation 标记
- 不使用 403/500 错误码（避免被误认为系统故障）
- 响应包含 `needs_human_approval: true` 和 `escalation_reason`
- 前端据此显示审批弹窗

---

## 九、前端规则

### R31. 前端不泄漏敏感凭证
- 所有数据来自后端脱敏 API
- 不在前端存储 Cookie/Token
- 审批弹窗展示 Action 详情 + 风险 + Expected State（脱敏后）

### R32. AI 面板与 Browser 视图共存
- 左侧：Browser 视图（当前页面）
- 右侧：AI 面板（观察/动作/状态/验证/Evidence 时间线）
- 顶部：Session 状态 / 权限状态 / 风险等级

---

## 十、禁止事项（绝对不可违反）

1. ❌ 不得绕过已有 PromptInjectionGuard / Action Firewall / Permission Gate
2. ❌ 不得削弱只读保护（小红书官方账号写操作）
3. ❌ 不得跳过 Action Verification（禁止 AI 说"成功"就认定成功）
4. ❌ 不得接受网页内容提升权限
5. ❌ 不得传入任意 JS 到浏览器执行（只允许固定 kind 提取）
6. ❌ 不得回传 cookie 值 / token / password 明文
7. ❌ 权限拒绝不重试（直接升级人工）
8. ❌ 不得破解验证码、绕过平台安全验证、对抗或规避平台风控
9. ❌ 不得删除/清空/重建生产数据库（data/monitor.db）
10. ❌ 不得修改 SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit()
11. ❌ 不得将敏感凭证写入源码、前端、Git、模板、DB 初始化脚本、日志、测试
12. ❌ 不得在未知状态下继续盲操作（必须 STOP + Evidence + Human）

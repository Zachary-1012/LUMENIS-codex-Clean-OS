# ZBC AI Browser Runtime — 研发指令适配映射表

> 生成时间：2026-09-07
> 模块：ai_browser_runtime.py + ai_browser_api.py
> 原则：基于已有代码扩展，不重写，不制造第二套 Runtime

## 一、Browser Core 能力（ai_browser_runtime.py）

| 研发指令要求 | 现有代码状态 | 实现位置 | 差距 | 状态 |
|---|---|---|---|---|
| URL Navigation / Back / Forward / Reload | ✅ 已实现 | `AIBrowserRuntime._do_execute()` | 无 | ✅ |
| Tab管理（新建/切换/关闭） | ✅ 已实现 | `TAB_NEW/TAB_SWITCH/TAB_CLOSE` | 无 | ✅ |
| Window管理 | ⚠️ 部分实现 | 复用CDP连接的context | 独立window管理待扩展 | ⚠️ P2 |
| Page State获取（URL/Title/Loading/错误） | ✅ 已实现 | `BrowserPageState` + `observe()` | 无 | ✅ |
| DOM查询（CSS/XPath/Accessibility Tree） | ✅ 已实现 | `observe(include_dom=True, include_accessibility=True)` | 无 | ✅ |
| Screenshot（全页/可视/元素级） | ✅ 已实现 | `screenshot(full_page=)` | 元素级截图待扩展 | ⚠️ P2 |
| Element Detection（智能多selector） | ✅ 已实现 | `_find_alternative_selector()` | 无 | ✅ |
| Click / Input / Select / Scroll / Keyboard | ✅ 已实现 | `_do_execute()` 各分支 | 无 | ✅ |
| Wait（元素/网络空闲/时间） | ✅ 已实现 | `WAIT` action + `wait_for_load_state` | 无 | ✅ |
| Download / Upload（上传L3审批） | ✅ 已实现 | `UPLOAD` 被 Firewall 拦截要求L3 | 无 | ✅ |
| Page Search（页面内文本搜索） | ✅ 已实现 | `SEARCH` action | 无 | ✅ |

## 二、Action Verification（硬要求）

| 研发指令要求 | 现有代码状态 | 实现位置 | 状态 |
|---|---|---|---|
| Action执行记录（type/target/selector/timestamp） | ✅ | `BrowserEvidenceRecord` | ✅ |
| Expected State定义 | ✅ | `ExpectedState` dataclass（12种检查维度） | ✅ |
| Actual State获取 | ✅ | `observe()` 执行后捕获 | ✅ |
| Verify比对（Expected vs Actual） | ✅ | `ActionVerifier.verify()` | ✅ |
| 输出PASS/FAIL + 差异描述 | ✅ | `VerificationResult.differences` | ✅ |
| Retry（同一selector最多2次） | ✅ | `FailureRecovery.max_retries=2` | ✅ |
| Alternative Selector（CSS→XPath→Accessibility→文本→坐标） | ✅ | `get_recovery_strategies(SELECTOR_ERROR)` | ✅ |
| Alternative Strategy（JS click→Enter→滚动后点击） | ✅ | `scroll_then_click` 等策略 | ✅ |
| Recovery（页面异常→reload→已知状态） | ✅ | `reload_page` / `navigate_back_then_forward` | ✅ |
| Human Escalation（所有策略失败→STOP+Evidence→人工） | ✅ | `HUMAN_ESCALATION` result + `human_escalation_required` | ✅ |

## 三、Browser Evidence

| 研发指令要求 | 现有代码状态 | 实现位置 | 状态 |
|---|---|---|---|
| browser_evidence表（向后兼容迁移） | ✅ | `BROWSER_EVIDENCE_SCHEMA` + CREATE IF NOT EXISTS | ✅ |
| task_id/run_id/step_id/agent_id/skill_id | ✅ | 表字段 + `BrowserEvidenceRecord` | ✅ |
| action/target/selector/timestamp | ✅ | 表字段 | ✅ |
| before_state/after_state（hash/摘要） | ✅ | `before_state_hash`/`after_state_hash` + `hash_state()` | ✅ |
| result（PASS/FAIL/RETRY/HUMAN_ESCALATION） | ✅ | `ActionResult` 枚举 | ✅ |
| evidence（screenshot路径/DOM快照/控制台错误） | ✅ | `evidence_path`/`dom_snapshot`/`console_errors` | ✅ |
| verification（expected vs actual） | ✅ | `verification`/`expected_state`/`actual_state` | ✅ |
| error（脱敏） | ✅ | `sanitize_sensitive()` 全链路脱敏 | ✅ |
| evidence_api.py扩展查询路由 | ✅ | `GET /api/browser/sessions/<id>/evidence` | ✅ |
| 不含Cookie/Token明文 | ✅ | 写入前全字段脱敏 + 敏感key值直接[REDACTED] | ✅ |

## 四、Browser Session Security

| 研发指令要求 | 现有代码状态 | 实现位置 | 状态 |
|---|---|---|---|
| Cookie/Token/Session/LocalStorage/Password/OAuth审计 | ✅ | `_SENSITIVE_PATTERNS`（12类正则） | ✅ |
| 敏感凭证不进入Prompt/LLM/Context/Memory/Logs/Evidence | ✅ | `sanitize_sensitive()` + `sanitize_dict()` 全链路 | ✅ |
| AI≠用户密码持有者 | ✅ | Runtime不存储密码字段，登录由用户手动扫码 | ✅ |
| Browser≠权限放大器 | ✅ | Action Firewall + Permission Gate 双重检查 | ✅ |
| Session隔离（AI与用户日常浏览隔离） | ✅ | 独立profile目录 `ai_runtime_<session_id>` | ✅ |
| 凭证脱敏（进入AI Context的页面内容过滤） | ✅ | `observe()` 返回前 `sanitize_sensitive()` | ✅ |
| Session生命周期（超时/空闲/最大生命周期） | ✅ | `idle_timeout=600s` / `max_lifetime=3600s` | ✅ |
| 只读保护（小红书官方账号硬编码） | ✅ | `ActionFirewall` + `_READONLY_BLOCKED_ACTIONS` | ✅ |

## 五、Prompt Injection 防护

| 研发指令要求 | 现有代码状态 | 实现位置 | 状态 |
|---|---|---|---|
| 网页内容=Untrusted Input标记 | ✅ | `[UNTRUSTED_WEB_CONTENT]` 前缀标记 | ✅ |
| System Prompt明确网页指令不覆盖Policy | ✅ | 安全边界在代码中（Action Firewall），不在Prompt | ✅ |
| 注入模式检测（中英文） | ✅ | `_INJECTION_PATTERNS`（30+模式，含中文） | ✅ |
| 记录警告但不执行 | ✅ | `PromptInjectionGuard.scan()` 记录+标记 | ✅ |
| 越权操作必须经Permission Gate | ✅ | `execute_action()` → Firewall → Permission | ✅ |
| 网页内容无法提升权限 | ✅ | Firewall状态不受网页内容影响 | ✅ |

## 六、Failure/Recovery

| 研发指令要求 | 现有代码状态 | 实现位置 | 状态 |
|---|---|---|---|
| Page Error→Retry→Recovery→Human | ✅ | `PAGE_ERROR` 策略链 | ✅ |
| Selector Error→Alternative Selector→Strategy→Human | ✅ | `SELECTOR_ERROR` 8步策略链 | ✅ |
| Session Error→NEED_VERIFY→Re-auth/Human→不静默 | ✅ | `mark_need_verify` + `SESSION_ERROR` 分类 | ✅ |
| Network Error→指数退避→Recovery→Human | ✅ | `retry_exponential_backoff` | ✅ |
| Unknown State→STOP+Evidence+Human，禁止盲操作 | ✅ | `UNKNOWN_STATE` → `stop_and_capture_evidence` | ✅ |
| Circuit Breaker（连续失败N次熔断，冷却恢复） | ✅ | `CircuitBreaker`（threshold=5, cooldown=30s） | ✅ |

## 七、API Contract

| 路由 | 方法 | 状态 |
|---|---|---|
| /api/browser/sessions | POST | ✅ |
| /api/browser/sessions | GET | ✅ |
| /api/browser/sessions/<id> | GET | ✅ |
| /api/browser/sessions/<id>/navigate | POST | ✅ |
| /api/browser/sessions/<id>/observe | POST | ✅ |
| /api/browser/sessions/<id>/action | POST | ✅ |
| /api/browser/sessions/<id>/verify | POST | ✅ |
| /api/browser/sessions/<id>/stop | POST | ✅ |
| /api/browser/sessions/<id>/evidence | GET | ✅ |
| /api/browser/sessions/<id>/human-approval | POST | ✅ |
| /api/browser/security/status | GET | ✅ |
| /api/browser/evidence/stats | GET | ✅ |

## 八、Frontend AI UI

| 要求 | 状态 | 实现位置 |
|---|---|---|
| 左侧Browser视图 | ✅ | 复用现有 browser-viewport |
| 右侧AI面板（观察/动作/状态/验证/Evidence时间线） | ✅ | panel-ai-agent（sidebar新增tab） |
| 顶部Session状态/权限/风险等级 | ✅ | AI面板内Session状态卡片 |
| 人工确认审批弹窗 | ✅ | ai-approval-modal |
| 全局设计语言（大圆角/毛玻璃/胶囊导航/渐变） | ✅ | 复用现有browser设计系统 |
| 不泄漏敏感凭证 | ✅ | 所有API响应经后端脱敏 |

## 九、测试

| 测试文件 | 测试数 | 状态 |
|---|---|---|
| test_ai_browser_runtime.py | 30+ | ✅ 全部通过 |
| test_browser_action_verification.py | 30+ | ✅ 全部通过 |
| test_browser_evidence.py | 20+ | ✅ 全部通过 |
| test_browser_security.py | 30+ | ✅ 全部通过 |
| test_browser_prompt_injection.py | 30+ | ✅ 全部通过 |
| test_browser_failure_recovery.py | 25+ | ✅ 全部通过 |
| **合计** | **185** | **✅ 全部通过** |

## 十、E2E验收场景

| Case | 描述 | 状态 |
|---|---|---|
| Case2 | 页面操作（定位→点击→验证→Evidence） | ✅ 测试覆盖 |
| Case3 | 失败恢复（Selector Error→Alternative→Human） | ✅ 测试覆盖 |
| Case5 | Prompt Injection（恶意网页注入不执行越权） | ✅ 测试覆盖 |

## 差距与后续计划

| 项目 | 优先级 | 说明 |
|---|---|---|
| Window独立管理 | P2 | 当前复用CDP context，独立window管理待扩展 |
| 元素级截图 | P2 | 当前支持全页/可视，元素级待扩展 |
| Set-of-Mark元素标注 | P2 | 研究报告建议，用于提升AI定位准确率 |
| 冷热分离Evidence存储 | P2 | 当前同步写入，高并发时可改异步 |
| 链式哈希Evidence | P2 | 当前每条独立hash，链式关联待扩展 |
| Task Permission Matrix 6级 | P1 | 扩展现有Permission Gate，增加ACT/WRITE/HIGH_RISK/ADMIN等级 |
| Risk Level L0-L4 | P1 | 新增细粒度风险等级 |
| AI Memory/Learning边界 | P1 | 新增Memory边界，防止敏感信息进入学习资产 |
| Checkpoint/Resume/DLQ | P1 | 扩展Failure Recovery，增加检查点和死信队列 |

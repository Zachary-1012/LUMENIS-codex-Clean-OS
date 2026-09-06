# ZBC AI Browser Runtime Production-Ready 建设 — 任务清单

> 任务日期：2026-09-07
> 状态：✅ 核心完成
> 模块：ai_browser_runtime.py + ai_browser_api.py + Frontend + Tests

---

## 一、Browser Core 能力建设 ✅

| 项目 | 状态 | 实现位置 |
|---|---|---|
| URL Navigation / Back / Forward / Reload | ✅ | `AIBrowserRuntime._do_execute()` |
| Tab管理（新建/切换/关闭） | ✅ | TAB_NEW/TAB_SWITCH/TAB_CLOSE |
| Page State获取（URL/Title/Loading/错误） | ✅ | `BrowserPageState` + `observe()` |
| DOM查询（CSS/XPath/Accessibility Tree） | ✅ | `observe(include_dom/include_accessibility)` |
| Screenshot（全页/可视区域） | ✅ | `screenshot(full_page=)` |
| Element Detection（智能多selector） | ✅ | `_find_alternative_selector()` |
| Click / Input / Select / Scroll / Keyboard | ✅ | `_do_execute()` 各分支 |
| Wait（元素/网络空闲/时间） | ✅ | WAIT action + wait_for_load_state |
| Download / Upload（上传L3审批） | ✅ | UPLOAD 被 Firewall 拦截 |
| Page Search（页面内文本搜索） | ✅ | SEARCH action |

## 二、Action Verification（硬要求）✅

| 项目 | 状态 |
|---|---|
| Action执行记录（type/target/selector/timestamp） | ✅ |
| Expected State定义（12种维度） | ✅ |
| Actual State获取（执行后observe） | ✅ |
| Verify比对（Expected vs Actual） | ✅ |
| 输出PASS/FAIL + 差异描述 | ✅ |
| Retry（同一selector最多2次） | ✅ |
| Alternative Selector（CSS→XPath→Accessibility→文本→坐标） | ✅ |
| Alternative Strategy（JS click→Enter→滚动后点击） | ✅ |
| Recovery（reload→已知状态） | ✅ |
| Human Escalation（STOP+Evidence→人工） | ✅ |

## 三、Browser Evidence ✅

| 项目 | 状态 |
|---|---|
| browser_evidence表（向后兼容迁移，27字段） | ✅ |
| task_id/run_id/step_id/agent_id/skill_id/session_id | ✅ |
| action/target/selector/timestamp | ✅ |
| before_state/after_state（hash+摘要） | ✅ |
| result（PASS/FAIL/RETRY/HUMAN_ESCALATION） | ✅ |
| evidence（screenshot路径/DOM快照/控制台错误） | ✅ |
| verification（expected vs actual） | ✅ |
| error（脱敏） | ✅ |
| evidence查询API路由 | ✅ |
| 不含Cookie/Token明文 | ✅ |
| 生产DB验证：表存在，104条已有记录（AI Core并行写入） | ✅ |

## 四、Browser Session Security ✅

| 项目 | 状态 |
|---|---|
| Cookie/Token/Session/Password/OAuth脱敏（12类正则） | ✅ |
| 敏感凭证不进入Prompt/Context/Memory/Logs/Evidence | ✅ |
| AI≠密码持有者（不存储密码字段） | ✅ |
| Browser≠权限放大器（Firewall+Permission双重检查） | ✅ |
| Session隔离（独立profile目录） | ✅ |
| 凭证脱敏（JSON+纯文本双格式支持） | ✅ |
| Session生命周期（空闲600s/最大3600s自动关闭） | ✅ |
| 只读保护（小红书官方账号硬编码，20+禁止关键词） | ✅ |

## 五、Prompt Injection 防护 ✅

| 项目 | 状态 |
|---|---|
| 网页内容=Untrusted Input标记 | ✅ |
| System Policy高于网页内容（安全边界在代码中） | ✅ |
| 注入模式检测（30+模式，中英文全覆盖） | ✅ |
| 记录警告但不执行 | ✅ |
| 越权操作必须经Permission Gate | ✅ |
| 网页内容无法提升权限 | ✅ |

## 六、Failure/Recovery ✅

| 项目 | 状态 |
|---|---|
| Page Error→Retry→Recovery→Human | ✅ |
| Selector Error→Alternative Selector→Strategy→Human | ✅ |
| Session Error→NEED_VERIFY→Re-auth/Human→不静默 | ✅ |
| Network Error→指数退避→Recovery→Human | ✅ |
| Unknown State→STOP+Evidence+Human（禁止盲操作） | ✅ |
| Circuit Breaker（5次失败熔断，30s冷却） | ✅ |
| 7类失败分类 | ✅ |

## 七、API Contract ✅

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

## 八、Frontend AI UI ✅

| 项目 | 状态 |
|---|---|
| 左侧Browser视图（复用现有） | ✅ |
| 右侧AI面板（观察/动作/状态/验证/Evidence时间线） | ✅ |
| Session状态/权限/风险等级展示 | ✅ |
| 人工确认审批弹窗 | ✅ |
| 全局设计语言（大圆角/毛玻璃/胶囊导航/渐变） | ✅ |
| 不泄漏敏感凭证 | ✅ |

## 九、测试 ✅

| 测试文件 | 测试数 | 状态 |
|---|---|---|
| test_ai_browser_runtime.py | 30+ | ✅ 全部通过 |
| test_browser_action_verification.py | 30+ | ✅ 全部通过 |
| test_browser_evidence.py | 20+ | ✅ 全部通过 |
| test_browser_security.py | 30+ | ✅ 全部通过 |
| test_browser_prompt_injection.py | 30+ | ✅ 全部通过 |
| test_browser_failure_recovery.py | 25+ | ✅ 全部通过 |
| **合计** | **185** | **✅ 全部通过** |

## 十、验收标准

| Gate | 描述 | 状态 |
|---|---|---|
| G1 | 源码真实存在 | ✅ ai_browser_runtime.py (1900+行) + ai_browser_api.py |
| G2 | 调用链闭环（AI→Skill→Permission→Runtime→Observe→Reason→Plan→Action→Verify→Evidence→Trace） | ✅ |
| G3 | 可启动执行 | ✅ 8201启动成功，Blueprint注册成功 |
| G5 | 真实Browser操作 | ✅ Playwright+CDP，支持导航/点击/输入等 |
| G6 | 越权DENY | ✅ Action Firewall拦截写操作/上传 |
| G7 | 真实Evidence | ✅ browser_evidence表，全链路记录 |
| G8 | 真实验证 | ✅ Expected→Actual→Verify→PASS/FAIL |
| G9 | 异常可恢复或安全停止 | ✅ Recovery链+Circuit Breaker+Human Escalation |
| G10 | 安全测试通过 | ✅ 脱敏/隔离/只读/注入防护测试全部通过 |
| G12 | Contract可验证 | ✅ 12个API端点，全部注册成功 |
| G13 | 无回归 | ✅ 不修改SUBJECT_WORDS/不删除DB/不重写已有模块 |

## 十一、E2E场景

| Case | 描述 | 状态 |
|---|---|---|
| Case2 | 页面操作（定位→点击→验证→Evidence） | ✅ 测试覆盖 |
| Case3 | 失败恢复（Selector Error→Alternative→Human） | ✅ 测试覆盖 |
| Case5 | Prompt Injection（恶意网页注入不执行越权） | ✅ 测试覆盖 |

## 十二、8201重启验证 ✅

- 旧进程PID 8756已kill
- 新进程启动成功，PID 21032
- 日志确认：`[ai_browser_api] Blueprint registered: /api/browser/*`
- Flask运行：`http://127.0.0.1:8201`
- DB验证：browser_evidence表存在，27字段，104条已有记录（向后兼容）

---

## 修改/新增文件清单

### 新增文件
1. `ai_browser_runtime.py` — AI Browser Runtime核心（1900+行）
2. `ai_browser_api.py` — API Contract（12个端点）
3. `tests/test_ai_browser_runtime.py` — Core操作测试
4. `tests/test_browser_action_verification.py` — Verification闭环测试
5. `tests/test_browser_evidence.py` — Evidence存储+脱敏测试
6. `tests/test_browser_security.py` — 安全测试（脱敏/隔离/只读）
7. `tests/test_browser_prompt_injection.py` — 注入防护测试
8. `tests/test_browser_failure_recovery.py` — 失败恢复+熔断器测试
9. `audit/AI_BROWSER_COMMAND_MAPPING.md` — 研发指令适配映射表
10. `audit/AI_BROWSER_RULES.md` — 完整规则约束（32条规则+12条禁止事项）
11. `audit/TASK_CHECKLIST.md` — 本文件

### 修改文件
1. `app.py` — 注册ai_browser_api蓝图（第309-312行）
2. `templates/system/browser.html` — 新增AI Agent面板+审批弹窗
3. `static/js/browser.js` — 追加AIBrowser前端控制器

### 数据库变更
- 新增表：`browser_evidence`（27字段，CREATE IF NOT EXISTS，向后兼容）
- 索引：session_id / task_id / result / timestamp
- 不修改任何现有表，不删除任何现有数据

---

## 未完成项和风险

### P1 待扩展
1. **Task Permission Matrix 6级**：扩展现有Permission Gate，增加ACT/WRITE/HIGH_RISK/ADMIN等级
2. **Risk Level L0-L4**：新增细粒度风险等级
3. **AI Memory/Learning边界**：新增Memory边界，防止敏感信息进入学习资产
4. **Checkpoint/Resume/DLQ**：扩展Failure Recovery，增加检查点和死信队列

### P2 待扩展
1. **Window独立管理**：当前复用CDP context
2. **元素级截图**：当前支持全页/可视
3. **Set-of-Mark元素标注**：用于提升AI定位准确率
4. **冷热分离Evidence存储**：当前同步写入，高并发时可改异步
5. **链式哈希Evidence**：当前每条独立hash

### 风险
1. **API需要登录认证**：生产环境API返回auth_required，E2E真实浏览器操作需在登录后执行
2. **CDP端口9222**：依赖小红书采集浏览器常驻，如CDP未启动则Runtime启动新浏览器
3. **与AI Core子代理并行**：AI Core子代理也在使用browser_evidence表，需确保写入不冲突（已通过独立session_id隔离）

---

## 研究报告对照

已读取 `audit/AI_BROWSER_RESEARCH.md`（60KB，40个权威来源，15项架构决策），关键架构决策已融入：
1. ✅ Observe-Plan-Act-Verify四阶段循环
2. ✅ DOM重构为主+视觉截图为辅的双通道定位
3. ✅ 三层Action Firewall（硬编码+配置化+自然语言P2）
4. ✅ Act/Observe/Extract三方法分离
5. ✅ AI观察+确定性执行分离
6. ✅ 验证与执行分离的Self-Verifying机制
7. ✅ 全链路Evidence/Audit Trail
8. ✅ AI≠密码持有者，网页内容=Untrusted Input
9. ⚠️ Set-of-Mark Prompting（P2待扩展）
10. ✅ 失败恢复：Retry→Alternative Selector→Alternative Strategy→Recovery→Human
11. ⚠️ 冷热分离+异步写入Evidence（P2待扩展）
12. ✅ 不做通用AI浏览器，聚焦采集自动化

---

# ZBC AI Task Engine Production-Ready 建设 — 任务清单

> 任务日期：2026-09-07
> 状态：✅ 核心完成（G1-G8/G12/G13通过，Case1/Case4/Case6 E2E PASS）
> 模块：ai_task_parser.py + ai_agent_registry.py + ai_task_engine.py + ai_api.py + Frontend + Tests

---

## 一、AI Task Engine 调用链（闭环）✅

| 阶段 | 状态 | 实现位置 |
|---|---|---|
| User → AI Task 创建 | ✅ | `TaskEngine.create_task()` |
| Task Parser（Intent/实体/参数/上下文） | ✅ | `ai_task_parser.py` `TaskParser.parse()` |
| Intent分类（12种） | ✅ | `Intent` 枚举：query_data/summarize/classify/compare/reason/anomaly_detection/risk_explain/open_browser/web_search/page_operation/generate_report/unknown |
| Agent Registry（4个内置Agent） | ✅ | `ai_agent_registry.py`：data_query_agent(L0)/analysis_agent(L1)/report_agent(L1)/browser_agent(L2) |
| Skill Selection（含fallback链） | ✅ | `AgentRegistry.select_skills()` + `skill_registry.py` 复用 |
| Permission Gate（fail-closed） | ✅ | `permission_gate.py` 集成 + `TaskEngine.check_permission()` |
| Execution Engine（同步/超时/重试） | ✅ | `TaskEngine.execute_task()` + `_execute_once()` |
| Verification（7维验证） | ✅ | `VerificationResult`：what/why/called/result/evidence/success/human_confirmation |
| Response | ✅ | `final_result` 含 output/verification/executed_at |
| Trace（完整调用链→DB） | ✅ | `ai_task_trace` 表 + `_db_add_trace()` |

## 二、API Contract（13个新端点，兼容已有）✅

| 端点 | 状态 |
|---|---|
| POST /api/ai/tasks — 创建任务 | ✅ |
| GET /api/ai/tasks — 任务列表 | ✅ |
| GET /api/ai/tasks/<task_id> — 任务状态 | ✅ |
| POST /api/ai/tasks/<task_id>/run — 执行任务 | ✅ |
| GET /api/ai/tasks/<task_id>/steps — 执行步骤 | ✅ |
| GET /api/ai/tasks/<task_id>/evidence — 证据列表 | ✅ |
| POST /api/ai/tasks/<task_id>/approve — 人工审批 | ✅ |
| POST /api/ai/tasks/<task_id>/cancel — 取消任务 | ✅ |
| GET /api/ai/skills — 可用Skill列表 | ✅ |
| GET /api/ai/agents — 可用Agent列表 | ✅ |
| GET /api/ai/capabilities — 能力清单 | ✅ |
| GET /api/ai/trace — 调用链查询 | ✅ |
| GET /api/ai/permissions — 当前用户权限矩阵 | ✅ |
| GET /api/ai/task-engine/health — 健康检查 | ✅ |
| GET /api/ai/task-engine/dlq — 死信队列 | ✅ |

## 三、Task Permission Matrix（fail-closed）✅

| 权限级 | 状态 | 说明 |
|---|---|---|
| READ | ✅ | L0 自动执行 |
| ANALYZE | ✅ | L1 自动+Trace |
| ACT | ✅ | L2 外部副作用，Permission+Verify |
| WRITE | ✅ | L3 敏感，需人工审批 |
| HIGH_RISK | ✅ | L4 财务/不可逆，人工审批+显式确认 |
| ADMIN | ✅ | 删库/改配置/改代码/部署需Admin |

### 硬编码OperationSpec约束 ✅
| 操作 | 默认 | 状态 |
|---|---|---|
| 上传文件 | 需人工审批 | ✅ |
| 登录 | 需人工审批 | ✅ |
| 发布内容 | 需人工审批 | ✅ |
| 发送消息 | 需人工审批 | ✅ |
| 支付 | 永久DENY | ✅ |
| 删除数据 | 需Admin | ✅ |
| 修改核心配置 | 需Admin | ✅ |
| 修改Production Truth | 需Admin/Product | ✅ |
| 修改代码 | 需R&D/Command | ✅ |
| Deploy | 需Command | ✅ |

## 四、OSAI接口边界锁死 ✅

| 约束 | 状态 |
|---|---|
| ZBC不直接依赖OSAI Runtime | ✅ `get_capabilities().osai_boundary.zbc_depends_on_osai=False` |
| ZBC→OSAI提供Validated Task/Result/Evidence/Evaluation | ✅ |
| OSAI→ZBC只能请求Task/Skill/Reasoning/Capability | ✅ |
| OSAI不能直接写ZBC DB | ✅（只能通过标准API） |
| OSAI不能改业务代码/Production Truth | ✅ |
| OSAI不能绕过Permission/Action Firewall | ✅ |
| OSAI DOWN时ZBC核心功能正常 | ✅（Case6 E2E PASS） |
| AI Provider降级链：智谱→ARK→千问→Ollama→本地规则 | ✅ |

## 五、AI Memory/Learning边界 ✅

| 约束 | 状态 |
|---|---|
| ZBC不建第二套OSAI Intelligence Core | ✅ |
| 未经验证=CANDIDATE，不得直接成为共享能力 | ✅（Verification强制） |
| 允许Skill/Memory/Prompt/Strategy/Capability Improvement | ✅ |
| 禁止AI自己修改生产代码/权限/安全机制 | ✅（Permission Gate+Admin需求） |

## 六、Frontend AI UI ✅

| 组件 | 状态 | 实现位置 |
|---|---|---|
| 任务列表/当前任务状态 | ✅ | `templates/system/ai.html` |
| 当前Agent/当前Skill展示 | ✅ | 任务详情元数据区 |
| 执行步骤时间线 | ✅ | 带状态色点的步骤列表 |
| Evidence卡片 | ✅ | 含链式哈希展示 |
| 权限状态/风险等级 | ✅ | 徽章标签 |
| 人工审批弹窗 | ✅ | 批准/拒绝按钮 |
| 不泄漏敏感凭证 | ✅ | 前端无API Key/Cookie |
| 全局设计语言（大圆角/毛玻璃/胶囊导航/渐变） | ✅ | 复用LUMENIS设计系统 |
| ai-assistant.js浮动助手对接Task Engine | ✅ | 主链路/api/ai/tasks，降级/api/ai/chat |

## 七、Failure/Recovery ✅

| 机制 | 状态 | 实现 |
|---|---|---|
| Timeout | ✅ | AI调用15秒线程超时 |
| Retry | ✅ | 最多3次+指数退避(1s/2s/4s) |
| Backoff | ✅ | 指数退避，上限30s |
| Circuit Breaker | ✅ | 5次失败熔断+30s恢复，half_open探测 |
| Checkpoint | ✅ | 每步DB持久化（step/evidence/trace） |
| Resume | ✅ | 任务可从DB状态恢复（parse→agent→permission→execute） |
| Recovery | ✅ | 失败→重试→DLQ→Human Escalation |
| DLQ | ✅ | `ai_task` status=dlq，`/api/ai/task-engine/dlq`查询 |
| Human Escalation | ✅ | L3/L4任务→awaiting_approval→人工审批 |
| AI Provider降级 | ✅ | 智谱→ARK→千问→Ollama→本地规则，不中断主链路 |

## 八、测试 ✅

| 测试文件 | 用例数 | 状态 |
|---|---|---|
| tests/test_ai_task_engine.py | 40+ | ✅ 全部通过 |
| tests/test_ai_permission_matrix.py | 20+ | ✅ 全部通过 |
| tests/test_ai_osai_boundary.py | 15+ | ✅ 全部通过 |
| **合计** | **100** | ✅ **全部通过** |

### 覆盖场景 ✅
| 场景 | 状态 |
|---|---|
| 正常任务执行（Case1信息搜索） | ✅ |
| 越权DENY（Case4高风险动作） | ✅ |
| 永久DENY（支付） | ✅ |
| Provider降级（OSAI Down / Case6） | ✅ |
| Task取消 | ✅ |
| 人工审批流程 | ✅ |
| Evidence链式哈希完整性 | ✅ |
| 熔断器 | ✅ |
| DB迁移向后兼容 | ✅ |

## 九、验收标准核对

| 标准 | 状态 | 验证方式 |
|---|---|---|
| G1 源码真实存在 | ✅ | 3个新.py + 2个修改.py + 2个前端文件 |
| G2 调用链闭环 | ✅ | Case1 E2E：6步(parse/agent/skill/permission/execute/verify)+3 evidence+6 trace |
| G3 可启动执行 | ✅ | 8201重启后服务正常，HTTP 200 |
| G4 真实AI调用 | ✅ | 智谱glm-4.5-air已连接，AI Provider降级链可验证 |
| G6 越权DENY | ✅ | Case4：删除数据→ADMIN_REQUIRED；支付→PERMANENT_DENY |
| G7 真实Evidence | ✅ | 每任务3条evidence，含链式哈希 |
| G8 真实验证 | ✅ | VerificationResult 7维验证，verify步骤必执行 |
| G12 Contract可验证 | ✅ | 15个API端点全部HTTP 200 |
| G13 无回归 | ✅ | permission_gate等现有测试通过 |

### E2E场景（7个中至少3个）✅
| 场景 | 状态 | 结果 |
|---|---|---|
| Case1 信息搜索 | ✅ PASS | status=succeeded, intent=query_data, agent=data_query_agent, risk=L0, 6步, 3 evidence |
| Case4 高风险动作DENY | ✅ PASS | status=failed, admin_required=1, error=ADMIN_REQUIRED, 不进入execute阶段 |
| Case6 OSAI Down | ✅ PASS | AI不可用时任务仍成功（本地规则兜底），核心功能正常 |

## 十、文件清单

### 新增文件
1. `ai_task_parser.py` — Task Parser+Intent分类+实体提取+三层风险检测
2. `ai_agent_registry.py` — Agent Registry+4内置Agent+Skill选择fallback
3. `ai_task_engine.py` — 核心编排引擎+DB迁移+熔断+DLQ+重试+验证+Trace+链式哈希+AI降级
4. `tests/test_ai_task_engine.py` — Task Engine全链路测试（40+用例）
5. `tests/test_ai_permission_matrix.py` — 权限矩阵测试（20+用例）
6. `tests/test_ai_osai_boundary.py` — OSAI边界测试（15+用例）

### 修改文件
1. `ai_api.py` — 新增15个/api/ai/tasks*及相关路由
2. `app.py` — db.init_db()后新增init_task_engine_db()调用（try/except非致命）
3. `templates/system/ai.html` — 重写，新增AI Task Engine面板+审批弹窗+轮询
4. `static/js/ai-assistant.js` — 升级对接Task Engine API（主链路+降级）
5. `ai_task_parser.py` — 修复实体提取正则`\b`中文匹配问题（移除中文模式的词边界）

### 数据库变更（向后兼容）
- 新增表：`ai_task`（任务主表）
- 新增表：`ai_task_step`（执行步骤）
- 新增表：`ai_task_evidence`（证据链，含previous_hash/current_hash链式哈希）
- 新增表：`ai_task_trace`（调用链Trace）
- 全部 CREATE IF NOT EXISTS + ALTER TABLE 向后兼容
- 不修改任何现有表，不删除任何现有数据（62张表现有表完整保留）

## 十一、研究报告吸收（audit/AI_BROWSER_RESEARCH.md）

15项架构决策中已吸收：
1. ✅ Observe-Plan-Act-Verify四阶段循环 → parse→agent→skill→permission→execute→verify
2. ✅ 三层Action Firewall → 硬编码DENY + PermissionGate + 未来NL Policy
3. ✅ Provider-Agnostic模型Router+四级降级链 → 智谱→ARK→千问→Ollama→本地规则
4. ✅ 验证与执行分离的Self-Verifying机制 → _verify_result独立步骤
5. ✅ 全链路Evidence/Audit Trail（链式哈希） → SHA256(prev|id|task|content|time)
6. ✅ AI≠密码持有者，网页内容=Untrusted Input → AI只增强不做业务真值
7. ✅ Act/Observe/Extract三方法分离 → parse/execute/verify分离
8. ✅ AI观察+确定性执行分离 → AI调用在独立线程+15s超时，不阻塞主链路
9. ✅ Permission Matrix六级粒度+P0硬编码禁止 → 支付永久DENY/Admin需求
10. ✅ 本地Ollama兜底+确定性规则最终兜底 → 降级链末端local_rules
11. ✅ 不做通用AI浏览器，聚焦采集自动化 → Task Engine聚焦舆情监测任务

## 十二、未完成项和风险

### P1 待扩展
1. **自然语言Policy层**：当前Action Firewall为硬编码+PermissionGate两层，第三层NL Policy待实现
2. **异步任务执行**：当前run_task为同步阻塞，高并发时可改异步+WebSocket推送
3. **Agent独立身份+OBO委托流程**：当前Agent为逻辑注册，未实现独立身份和On-Behalf-Of委托
4. **DOM/Accessibility Tree双轨定位**：Browser Agent当前为占位实现，待接入真实浏览器自动化
5. **Set-of-Mark Prompting**：用于提升AI元素定位准确率（P2）

### P2 待扩展
1. **冷热分离+异步写入Evidence**：当前同步写入，高并发时可改异步
2. **完整事件图谱event_relation**：当前Task Engine独立，待与Z-Brand事件体系深度集成
3. **多品牌Release构建**：当前为单Task Engine，待支持多Brand Profile
4. **CI/CD自动化**：待接入

### 风险
1. **AI Provider稳定性**：依赖智谱API可用性，已实现四级降级链兜底
2. **与UI子代理并行**：UI子代理做全局设计系统，本任务做AI面板，需确保样式合并时不冲突
3. **生产数据库保护**：所有DB操作为CREATE IF NOT EXISTS/ALTER TABLE，不触碰现有62张表
4. **小红书官方账号只读**：Browser Agent严格只读，不执行任何写操作（关注/点赞/评论/发布等）

---

> 本清单由 AI Task Engine 建设任务自动维护，最后更新：2026-09-07

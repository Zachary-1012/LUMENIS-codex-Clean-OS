# ZBC V2.0 双域隔离 × 当前真实代码 适配核对与补强清单 V1.0

> 基准：用户《ZBC 全量闪电落地指令 V2.0》23 条；事实来源：当前分支 lumenis-dual-domain-v3 真实代码核查（2026-09-06）。
> 原则：共享技术底座，不共享错误业务语义。导航以用户**最新拍板**为准，不回退到 V2.0 第 6 节的建议目录。
> 状态：✅已具备(有代码/测试)　🟡部分(需贯穿或补覆盖)　🔲待建。禁止把 🟡/🔲 报成 VERIFIED。

## 0. 导航口径（覆盖 V2.0 第6节，以拍板为准）
- ZBMP：Overview / Brand / Content / KOS / Competition / Risk / Reports（Growth 整合进 Overview+Brand 页内 Tab；Competition 独立）
- CTH：Overview / Real-time / Events / Risk / Xiaohongshu / Reports（199品牌/9业态=Overview Tab + Real-time 筛选器，不独立占导航）
- SYSTEM：Runtime / Collector / AI / Database / Security / **Settings(新增，账户/技能/栏目自定义/关于/域名/开发者都收这里)**
- 栏目可在 Settings 自定义显隐/排序/重命名/恢复默认（按 用户+域 持久化，受权限与双域约束）。

## 1. 逐条款核查（V2.0 → 真实状态 → 补强动作）
| V2.0 条款 | 真实代码证据 | 状态 | 补强动作 |
|---|---|---|---|
| §3 双域隔离 ZBMP≠CTH | domain_isolation.py(DomainContext/线程本地/assert_cth_protection/cross_domain_access_allowed/domain_summary)、subject_context.py(CTH 强制 brand_key=guangzhou_taikoo_hui)、test_request_domain_context.py | ✅ | 保留红线；新增跨域读取尝试必须被拒并记审计 |
| §8 Runtime 任务带域 | runtime_guardian.py workers/checkpoints/dlq 三表均有 domain_id/product_id(幂等迁移)、enqueue_dlq 强制带域 | ✅ | 确认 worker 认领/心跳/恢复全程透传不丢域；System Runtime 页按 product/domain 分组显示 |
| §10 数据层 Raw→Norm→Canonical→Domain | canonical_data.py/database_migrations.py/evidence_chain.py/ai_call_logger.py 均有 product_id/domain_id 列 | 🟡 | 端到端核查 采集入库→canonical→domain→AI→risk→evidence→report 每跳实际写域，缺列补列、缺值禁止静默落 SYSTEM |
| §9 Collector 带域、CTH 规则不成 ZBMP 隐式过滤 | collector 链路 + domain_isolation | 🟡 | 采集任务强制带 collector_id/source_id/product_id/domain_id/task_id；加测试证明 ZBMP 采集不被 199品牌/9业态隐式过滤 |
| §11 AI 双 Context、规则不被 AI 覆盖 | ai_domain_context.py(validate_prompt_domain_isolation/mark_ai_result_with_domain/DomainMismatchError)、ai_governance.py 已接 prompt 域校验 | ✅/🟡 | AI 结果落全字段(provider/model/prompt_version/input/output/confidence/final_result/human_correction + product/domain/trace)；补跨 prompt 注入被拒测试 |
| §12 Risk 双 Policy 不混阈值 | risk_engine.py + tests/test_risk_dual_domain.py | ✅/🟡 | 核对 ZBMP(声誉/竞品/传播异常/负反馈/危机) 与 CTH(扩散/安全/歧视/集中负面/KOC集中) 阈值分表配置；unknown 保持 unknown，禁止 critical=high、0/0=0 |
| §13 Report 双模板 | report_engine.py 带域；CTH daily/special/weekly 齐；brand_report_generator.py | 🟡 | 补全 ZBMP 六类报告(Brand/Performance/Competitive/Growth/Content/BrandRisk)各自模板；共享引擎+各自数据，生成后校验文件存在/非空/大小合理 |
| §14 Evidence 四层追溯 | evidence_chain.py/evidence_store.py/app_evidence.py + zbc_evidence 表，带域列 | ✅/🟡 | 保证 Raw→Normalized→Domain→Decision 每跳 evidence_id/trace_id/source_id/timestamp 可回溯到结论 |
| §15 Permission 带 product/domain | permission_gate.py(功能映射表标注仅2处调用) | 🟡 | 写操作与页面访问全面过 PermissionGate；规则=ZBMP Analyst 不天然拥有 CTH 权限；成员 1 Owner+3 Admin+5 Member 按产品授权 |
| §16 API 域契约 + 兼容层 | api_dual_domain.py、/api/domain/context、app.py 含 /api/zbmp|cth|system | 🟡 | 成体系收敛 /api/zbmp/* /api/cth/* /api/system/*；旧 /api/xhs、/api/v4/api-keys 等保留 deprecated 兼容层，不机械重命名、不断旧链 |
| §18 产品切换必须真重载 | 仅 7 模板(cth industries/evidence/kos、zbmp intelligence/evaluation、system evaluation、cth brands)出现域上下文 | 🔲/🟡 | **P0**：在全局 layout/公共 JS 统一注入 X-Product-Id/X-Domain-Id，切换 ZBMP↔CTH 时重载 Context/指标/数据/权限/报告；覆盖全部 20+ 页；加测试禁止"标题变了数据还是另一域" |
| §19 两条全量运行链 | 单元/模块测试较多 | 🟡 | 补两条端到端链路测试(ZBMP: Data→Canonical→Domain→AI→Risk→Evidence→Report→UI；CTH: Xiaohongshu→Subject→Domain→…→UI) |
| §20 六态验收 | P1-E 进行中 | 🟡 | 每页齐 Loading/Empty/Error/Success/Degraded/PermissionDenied；禁 Mock/假成功/死按钮/不存在 API/字段猜测/旧 UI/无限滚动 |
| §21 性能隔离防互拖 | — | 🔲 | Runtime 任务隔离+资源配额：CTH 大规模采集不得使 ZBMP UI/API 不可用；加并发/限流保护与验证 |
| §17 System Control Center | system_health_api.py/lumenis_agg_api.py | 🟡 | SYSTEM 页显示 RUNNING/HEALTHY/DEGRADED/FAILED/RECOVERING + product_id/domain_id/task_id，能定位是哪个域出问题 |
| §22 验收矩阵 无证据不 VERIFIED | — | 🟡 | 按 ZBMP/CTH/System × Startup/DB/Collector/AI/Risk/Evidence/Reports/UI/Runtime/Recovery/Security/Tests 出矩阵，外部缺凭证一律 BLOCKED |

## 2. 本轮新增（与 V2.0 并列执行，不得遗漏）
- 设置双域隔离：当前域设置(按 product 过滤)+全局/SYSTEM 设置两层；CTH 设置不见 ZBMP 项；ZBMP=TOTP、CTH=账号密码，分域显示。
- 栏目可配、Skill 统一收进 Settings 按需启用（不选不显示不加载）。
- 视觉：去素加浓但不花（同色系渐变卡/大数字层级/实底选中/六态微交互），采集表格保持专业模板，No-Scroll+横向叠层，增量不大重构。
- 数据精准红线：缺失显式 null/unknown/missing，禁估算/默认值填充；publish_datetime 与 collected_at 分离；content_hash+platform_id 精准去重；AI 与原始数据分离、人工修正可追溯。

## 3. 绝对禁止（沿用 V2.0 §20 + 用户红线）
假测试/假数据/假成功；改测试让其通过；删失败测试；注释吞异常；大重写；删历史数据/表；恢复旧 UI；让 OSAI/LUMENIS Command 成为 runtime 依赖；把 BROKEN 粉饰成 PARTIAL、把 PARTIAL/BLOCKED 写成 VERIFIED；破坏 SUBJECT_WORDS/EXCLUDE/subject_hit()。

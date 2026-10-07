# 全产品语义校准清单 — 2026-10-07

性质：现有 Product Architecture / 各 Owner 合同的索引与校准证据，不是第二权威。
冻结源码基线：`f6dac9216cbb331e730329a70513e0c90c306e73`；本地差异按各行 SHA 分开。完整字段和固定提交链接见同名 JSON。

覆盖 47 项术语/状态；覆盖全部指定语义族。没有遍历或改写历史数据、私有配置、Cookie、生产 DB；未证明所有运行界面已完成迁移。

## 已安全校正

- 旧“生产安全默认”改为“待迁移兼容回退”，保留行为，避免被当作授权依据。
- BMP 的兼容 ProductContext 显示名改为 LUMENIS Brand & Market；ZBMP/zbmp ID 保留。
- 历史 CROSS_REPO_CONTRACT_BOUNDARY 的 ACTIVE/Dual-Core 标识纠正为 HISTORICAL/SUPERSEDED，原文保留并指向当前合同。
- 旧测试改用准确名称：只验证未知值不映射 SYSTEM，未证明拒绝未知域；原断言未弱化。
- Architecture、AGENTS、README、CURRENT 和 Owner Index 同步接续位置。治理机器合同/model-routing 不变。

## 需要后续行为审批与整合的缺口

| ID / 优先级 | 当前事实 | 接续与通过标准 |
|---|---|---|
| S-01 / P0 | product_to_domain(BMP/bogus)、domain_to_product(bmp/bogus) 返回 CTH；通用请求 resolver 同样回退 | C3/C6：区分缺省旧调用与显式非法值；统一已批准别名；拒绝冲突请求头。先冻结 callers、现有 ID、旧存储含义，再改 API 行为；无权限提升、合法旧调用兼容。 |
| S-02 / P0 | DomainContext 对 CTH 强制参考主体；全局 hook 可受 ZBC_PRODUCT_ID 环境覆盖 | C1/C3/C6：把参考主体模式限制为明确旧入口，正常 GLOBAL 不带隐式主体；新旧调用、跨城/品牌隔离和权限分别验收。不得本轮直接改持久化解释。 |
| S-03 / P1 | 同一 NEED_VERIFY/READY/VERIFIED 在 guard、计划、缓存、治理中含义不同 | C1/C2/C6/F：组合/呈现时保留 Owner/字段、reason、scope、时间；合法验证码挑战与元数据待验证分别表达；不批量替换枚举。 |
| S-04 / P1 | ARK/doubao 注册仍写 ACTIVE_FALLBACK；owned 正常入口明确不可fallback且未绑定 | C2/C6：查清历史可调用路线及获准范围，UI只消费真实owned状态。禁止把登记状态或工程模型当作产品可用。 |
| S-05 / P1 | 旧函数/测试固定了 CTH 默认语义 | 与 S-01/S-02 同一成果更新调用和断言；不能删测试求绿，也不能只改测试名宣称行为修复。 |

复现：`SEMANTIC-REPRODUCTION-20261007.json` 为从当前源码 AST 取出的纯函数演练。没有请求生产 API 或运行权限链，不能据此断言越权。三个领域 blueprint 会在各自 before_request 中重新强制自身域，因此通用 resolver 的结果不能直接等同这三个端点的最终域。

## 逐项文字表格

| 当前词 | 定义 | Owner | 用户文案 | 技术标识 | 历史词 | 保留兼容 | 禁止混用 | 源码/调用定位 | 迁移 | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| 序境 / LUMENIS | 唯一当前产品；内含 CTH/BMP/Shared/SYSTEM | Product Architecture | 序境 / LUMENIS | LUMENIS | ZBC / Z-Brand-Core / 母平台 | YES | 旧名不是当前独立产品层级 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:13` | NO | CALIBRATED |
| ZBC | 历史包、环境变量和协议前缀 | C6 / SYSTEM | 不作产品标题 | ZBC_DB_PATH / ZBC_PRODUCT_ID | Z-Brand-Core | YES | 变量前缀不是新产品或第二数据库 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:272` | NO | CALIBRATED |
| ZBMP | BMP 的持久化兼容标识 | C3/C6 / domain owner | BMP | product_id=ZBMP; domain_id=zbmp | Multi-Subject Brand Management Platform | YES | 不能把兼容 ID 当第二产品 | `subject_context.py:16` | NO_ID_RENAME | LABEL_CORRECTED_IDS_PRESERVED |
| Z-Brand-Core | 历史仓库/协议命名 | C6 / API compatibility | 序境 / LUMENIS | 已有 contract_version 字符串 | Z-Brand-Core | YES | 旧协议字符串不决定当前产品身份 | `app.py:2613` | CALLER_REVIEW_BEFORE_SCHEMA_CHANGE | COMPATIBILITY_RETAINED |
| 母平台 | 历史解释性用词，不是当前产品层级 | Product Architecture | 序境 / LUMENIS | NONE | 母平台 | NO | 不可推导额外子产品/权限层 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:13` | NO | CALIBRATED |
| APP ONLY | 已替代的历史交付方向 | F / Experience | 四 Surface | NONE | App-only / Web-only / Website-login | NO | 历史方向不能缩减四端 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:148` | NO | HISTORICAL_ONLY |
| CTH | 商业主体运营域；Subject-first | C3 / CTH | 商业运营 | CTH / cth | 原广州太古汇限定 | YES | CTH 不等于某一家商业体 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:78` | NO | CALIBRATED |
| BMP | 品牌市场域；Brand/Market-first | C3 / BMP | 品牌市场 | ZBMP / zbmp（兼容）；部分合同 BMP | ZBMP | YES | BMP不是另一个产品；不要跨合同直接替换ID | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:80` | NO | CALIBRATED |
| product_id | 历史接口中的业务域/系统标识 | C3/C6 / context | 按上下文显示商业运营或品牌市场 | CTH / ZBMP / SYSTEM | PRODUCT_CTH / PRODUCT_ZBMP | YES | 字段名不意味着多个产品 | `subject_context.py:15` | PERSISTED_AND_API_MAPPING_REVIEW | BEHAVIOR_REVIEW_REQUIRED |
| domain_id | 调用与数据合同中的领域标识 | C3/C6 / domain isolation | 领域 | cth / zbmp / system；合同限定别名 | bmp | YES | UNKNOWN/BMP别名不得静默成为CTH | `domain_isolation.py:39` | PERSISTED_CALLER_AND_API_REVIEW | BEHAVIOR_REVIEW_REQUIRED |
| Subject | 具体商业主体及其稳定身份与范围 | C1/C3 / registry | 商业主体 | subject_id / scope.subject_id | CTH_SUBJECT_ID | YES | 同名/跨城/商场/门店不合并 | `subject_context.py:19` | REFERENCE_DEFAULT_CALLER_REVIEW | BEHAVIOR_REVIEW_REQUIRED |
| BrandFocus | 品牌任务的显式聚焦范围 | C1/C3 / registry/context | 品牌聚焦 | brand_key / brand_focus | 旧 brand_scope | YES | 不是Subject随意别名；聚焦不授予权限 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:86` | NO | CALIBRATED |
| GLOBAL / ALL | 默认未聚焦，受当前权限限制的全域工作范围 | C1/C3/C6 / context | 全部 / 全局 | GLOBAL / ALL / GLOBAL_ALL（各现有合同） | 隐式参考主体 | YES | 不是无限权限、隐式Subject或全球覆盖已完成 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:86` | NO | CALIBRATED |
| Clear focus | 清当前聚焦，保留历史任务范围和版本 | F/C3/C5 / context+SavedWork | 清除聚焦 | 现有 clear 行为 | 清空资料 | NO | 不能删除来源/旧成果/授权档案 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:86` | NO | CALIBRATED |
| Source | 可定位的输入来源及原始版本 | C1/C5 / source owner | 来源 | source_id / source_url / source hash | source note | YES | URL存在不是已读取，也不是Evidence准入 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:68` | NO | CALIBRATED |
| Evidence | 带来源、时间、范围、身份的证据 | C1/C5 / Shared Evidence | 证据 / 引用 | evidence_id / source identity | 摘要/笔记 | YES | 相同内容不合并不同来源身份 | `lumenis/shared/evidence/store.py:19` | NO | CALIBRATED |
| Canonical | 通过当前准入合同的规范业务数据 | C1/C5/C6 / canonical owner | 规范记录 | canonical_data / canonical_id | zbc_canonical_data | YES | AI输出/Mock/缓存/旧报告不自动成真相 | `canonical_data.py:241` | NO_HISTORICAL_ROW_REWRITE | LOCAL_OWNER_REPAIR_RETAINED |
| Metric | 特定单位、期间、分母下的测量/计算值 | C3 / metric owners | 指标 | 现有指标字段与MetricSnapshot | 热度/满意率概括 | YES | missing≠0；平台热度≠样本热度 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:38` | NO | CALIBRATED |
| Truth Table | 由规范事实和指标支撑的业务解释表 | C3 / truth owners | 业务数据表 | 现有 truth table 合同 | 任意AI表格 | YES | 表格生成不证明事实成立 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:38` | NO | CALIBRATED |
| ViewModel | 将已有事实与状态按任务呈现 | C6/F / experience_runtime | 任务/内容/结果 | 现有 JSON ViewModel | 前端fixture | YES | 不建立第二业务真相 | `experience_runtime.py:920` | NO | CALIBRATED |
| Artifact / SavedWork | 任务成果的可保存版本与可重开引用 | C4/C5 / Shared Artifact | 成果 / 已保存作品 | artifact_id / version / parent / hash | 文件存在 | YES | 有文件≠正式保存/发布/用户验收 | `lumenis/shared/reporting/saved_work.py:419` | NO | CALIBRATED |
| Outcome / Evaluation | 实际结果和对结果的评价 | C3/C2/C5 / existing owners | 结果 / 评价 | 现有 Outcome/Evaluation 对象 | task completed | YES | Action已执行不代表商业效果已知 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:78` | NO | CALIBRATED |
| UNKNOWN | 未建立事实或当前证据不足 | 各现有数据/运行Owner | 未知 / 待核实 | UNKNOWN / null（按字段） | 0 / healthy | YES | 未知不能推为0、CTH、正常或拒绝 | `collector_status_api.py:11` | NO | CALIBRATED |
| NOT_CONFIGURED | 所需适配/配置未建立 | C1/C2 / adapter/Gateway | 未配置 | CollectionStatus.NOT_CONFIGURED | UNAVAILABLE | YES | 未配置不是内容为空 | `lumenis/system/collector/adapters/base.py:13` | NO | CALIBRATED |
| NEED_VERIFY — auth metadata | 已有认证元数据但未核当前连通 | C1 / legacy status API | 登录状态待检查 | cookie_status=NEED_VERIFY | NEED_VERIFY | YES | 不能直接等同平台验证码挑战 | `collector_status_api.py:9` | PRESENTATION_REASON_BINDING_REVIEW | QUALIFIER_REQUIRED |
| NEED_VERIFY — collector guard | 平台要求合法人机验证，受影响路径等待 | C1/C6 / risk guard | 需要平台验证 | guard.state=need_verify | NEED_VERIFY | YES | 不能解释成可继续自动请求 | `lumenis/system/collector/guard/state.py:23` | NO_ENUM_RENAME | QUALIFIER_REQUIRED |
| READY — query plan | 计划及有效查询已形成，仍须执行准入 | C1 / acquisition plan | 查询计划已准备 | plan.status=READY | READY | YES | 计划就绪≠Session/GPU/成果就绪 | `lumenis/system/collector/acquisition_plan.py:25` | NO_ENUM_RENAME | QUALIFIER_REQUIRED |
| RUNNING — collection attempt | 某次已认领采集尝试运行中 | C1/C6 / task queue | 采集中 | tasks.status=running + run_id/lease | RUNNING | YES | 进程存在/窗口运行不代表采集运行 | `lumenis/system/collector/guard/task_queue.py:87` | NO_ENUM_RENAME | LOCAL_OWNER_REPAIR_RETAINED |
| RUNNING — live dispatch | 当前任务已派工并通过准入 | M / local live dispatch | 当前任务执行中 | dispatch.roles.*.state=RUNNING | active/enabled | YES | 发布拓扑和ELIGIBLE不表示正在工作 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:119` | NO | CALIBRATED |
| BLOCKED | 具体依赖、身份或权限阻塞，带原因与范围 | 各Owner | 受阻：具体原因 | BLOCKED / blocked（按Owner） | FAILED | YES | 一条路径受阻不扩散成全平台停止 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:148` | NO | CALIBRATED |
| COOLDOWN | 风险/频率触发的停止请求和冷却阶段 | C1/C6 / guard | 冷却等待 | cooldown | BLOCKED | YES | 不是服务器健康或已恢复 | `lumenis/system/collector/guard/state.py:20` | NO | CALIBRATED |
| PARTIAL | 只完成明确范围，注明已知/缺失部分 | 对应资料/覆盖Owner | 部分完成 | PARTIAL | 成功/全覆盖 | YES | 几条样本不能代表全平台或市场 | `00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md:139` | NO | CALIBRATED |
| VERIFIED — historical connection | 某时点的历史验证结果 | C1 / status cache | 上次验证结果及时间 | last_check + cached VERIFIED | 当前VERIFIED | YES | 历史连通不等于当前Session可用 | `collector_status_api.py:8` | NO | CALIBRATED |
| VERIFIED — product completion | 有适用Runtime/E2E证据的行为验证阶段 | C6/M / completion contract | 已验证（注明版本/范围） | VERIFIED | TESTED | YES | 不是JOB_CLOSED/USER_VERIFIED | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:162` | NO | CALIBRATED |
| JOB_CLOSED | 完整所分配Owner用户成果通过适用验收 | M/Owner / completion | 本任务已验收 | JOB_CLOSED | 函数完成 | YES | 不是发布，不接受仅代码/测试成功 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:167` | NO | CALIBRATED |
| RELEASED | 适用发布门禁及同版本证据成立 | C6/M / release | 已发布 | RELEASED | git push / green CI | YES | 不是持续运行或市场效果 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:169` | NO | CALIBRATED |
| OPERATING | 真实持续操作产生要求的运行证据 | C6 / runtime+outcome | 运行中（有运行依据） | OPERATING | health=200 | YES | 不是只启动一次或已发布 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:165` | NO | CALIBRATED |
| PUBLISHED_STATE | GitHub/current 已发布事实与职责 | M/C6 / repository | 已发布状态 | HEAD / CURRENT | 全窗口当前活跃 | YES | 不能当实时调度 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:114` | NO | CALIBRATED |
| ELIGIBLE | 角色可接受派工，没有隐含任务 | M / dispatch | 待命 | ELIGIBLE | 恢复拓扑=开工 | YES | ELIGIBLE不等于RUNNING | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:117` | NO | CALIBRATED |
| WAITING_DEPENDENCY | 等待已列明依赖/用户指令，恢复不扩范围 | M / dispatch | 等待依赖 | WAITING_DEPENDENCY + resume_condition | 自动扩任务 | YES | 条件满足不授权新功能/新效果 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json:126` | NO | CALIBRATED |
| Product AI | 已有单一Gateway中的获准自有推理 | C2 / AI Gateway | 序境 AI（状态如实） | provider=owned; service_binding | 工程模型 | YES | Provider注册/训练文件不是产品可用 | `lumenis/system/ai_gateway/owned_inference.py:27` | SERVICE_BINDING_REQUIRES_OWNER_EXECUTION | UNAVAILABLE_IN_SOURCE_CONTRACT |
| Engineering models | Codex研发资源，用户手动设置优先 | M/F/C1-C6 / engineering | 不作为产品Provider选项 | Astra/Sol/Luna; .codex/model-routing.toml | Product AI | YES | 模型切换不改变Owner/Permission | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:185` | NO | CALIBRATED |
| Provider registry status | 兼容路由的登记状态 | C2 / providers+channel | 不能代替产品推理可用性 | ACTIVE_FALLBACK / AVAILABLE / DISABLED | configured=working | YES | 旧ARK兜底登记不证明owned执行或授权 | `lumenis/system/ai_gateway/providers.py:14` | CALLER_AND_APPROVAL_REVIEW | LEGACY_STATUS_DEBT |
| Public Website | 一个产品在该目标端的体验；共用Core与事实 | F/C6 / Experience | 官网 | 现有 website/ 或 app/ 路由 | 历史单端部署词 | YES | 端存在不代表业务闭环；不同端不建重复真相 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:92` | NO | CALIBRATED |
| Web Workspace | 一个产品在该目标端的体验；共用Core与事实 | F/C6 / Experience | Web工作区 | 现有 website/ 或 app/ 路由 | 历史单端部署词 | YES | 端存在不代表业务闭环；不同端不建重复真相 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:93` | NO | CALIBRATED |
| Desktop | 一个产品在该目标端的体验；共用Core与事实 | F/C6 / Experience | 桌面端 | 现有 website/ 或 app/ 路由 | Desktop App | YES | 端存在不代表业务闭环；不同端不建重复真相 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:40` | NO | CALIBRATED |
| Mobile Companion | 一个产品在该目标端的体验；共用Core与事实 | F/C6 / Experience | 移动伴随端 | 现有 website/ 或 app/ 路由 | 历史单端部署词 | YES | 端存在不代表业务闭环；不同端不建重复真相 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:95` | NO | CALIBRATED |

## 覆盖与限制

源码事实优先；所有行有当前文件 SHA、行号、固定基线链接。若 same_bytes_as_published=false，不能把本地行号/内容宣称已在该固定提交发布。历史原件与现存 ID 保留；本轮不执行数据库枚举迁移。未进行四端逐屏实机验证、完整请求权限链重放或全部 Provider 调用追踪；这些对应上表待执行的现有 Owner 工作，不是本轮研究已完成的能力。

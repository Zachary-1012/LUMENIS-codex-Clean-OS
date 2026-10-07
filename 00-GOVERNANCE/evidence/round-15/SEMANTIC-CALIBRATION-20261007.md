# 全产品语义校准清单 — 2026-10-07

性质：现有 Product Architecture / 各 Owner 合同的索引与校准证据，不是第二权威。
冻结源码基线：`f6dac9216cbb331e730329a70513e0c90c306e73`；本地差异按各行 SHA 分开。完整字段和固定提交链接见同名 JSON。

覆盖 47 项术语/状态；覆盖全部指定语义族。没有遍历或改写历史数据、私有配置、Cookie、生产 DB；未证明所有运行界面已完成迁移。

## 2026-10-08 已授权的实际行为修复

本轮 Product Owner 明确要求把已记录错误修复，不再只保留语义债。修复基线为
`6ff2cc0b68d8b9c3ae8ea658678242df8deac7dc`。原 10 月 7 日复现与报告仍由历史提交保留；
本节覆盖其“等待后续行为审批”状态。没有改写生产 DB、迁移持久化 ID、启用退役 Provider、
租赁 GPU 或自动恢复 C1–C6/F。

| ID | 实际修复与复用入口 | 当前验收边界 |
|---|---|---|
| S-01 / P0 | `domain_isolation`统一 BMP/ZBMP 别名，非法/矛盾域拒绝；通用与蓝图 HTTP 入口用同一解析；DomainAdapter 与实际下游不再以未知值选 CTH。 | 明确合法域正常返回；非法值在业务处理前失败；Context 不授予权限。 |
| S-02 / P0 | CTH 不再强制广州 Subject；GLOBAL 不含隐式焦点；环境不覆盖请求；线程与嵌套 scope 成对恢复；旧聚合改用现有 scoped Canonical，参考过滤器不伪装全域读取。 | 正常 GLOBAL/FOCUS、其他商业体、SYSTEM、失配拒绝、跨请求/中断恢复分别验证；历史数据不迁移。 |
| S-03 / P1 | 两条 retained Collector status 路由共用原 owner；认证元数据、历史验证/挑战、计划和 runtime 生命周期保留各自来源与时间。 | 路由注册顺序不能改变含义；配置/缓存不升级成当前平台健康；未发真实平台请求。 |
| S-04 / P1 | ARK/Doubao 标为 LEGACY/compatibility_only；Provider日志状态读同一Registry；不根据密钥存在/断路器推断可用。 | Owned未绑定保持UNAVAILABLE；未调用或恢复外部Provider。 |
| S-05 / P1 | 合法显式旧调用与断言一并校准；新反例覆盖未知值、矛盾pair、跨域、丢焦点、SYSTEM、旧环境覆盖。 | 不删/跳过有效测试求绿；有限组合检查不等于所有产品功能已验收。 |
| S-06 / P1 | 深读 Math/Comparator 方法时发现并修复已有 Learning 缺陷：RAW修正被立即消费、重启丢样本；消费端只读已晋升状态，归档/持久化失效不能复活旧缓存。 | 原Learning owner与晋升流程保留；真实临时DB覆盖记录、晋升、重启、归档与失败；不是模型训练或真实业务推理完成。 |

### Codex研发与产品实际采用

冻结含义与接受条件 → 对照当前caller → 先找能证伪旧行为的输入 → 修既有owner →
检验正常业务结果及反例 → 对同一发布树执行受影响检查。该方法本轮已用于域/焦点、
状态与Learning修复。C1–C6/F直接消费这些共享合同，复用固定版本证据；
仍需完成各自真实任务/界面的验收，不需要重新修或重新研究本轮已落地边界。

Math原文及适用条件见[实际采用记录](OPENAI-MATH-ADOPTION-20261007.md)。方法启发不冒充
数学定理对社媒总体、商业因果或LLM准确率的保证；没有执行Lean/Comparator proof replay。

### 验证记录

本轮完整受影响检查与发布回执写入同名JSON的`repair_verification`。较早的纯AST复现
`SEMANTIC-REPRODUCTION-20261007.json`仍是历史证据；本轮新增测试实际经过Flask入口、
既有Scope/Permission/Canonical与Learning临时DB，仍不等于已重载生产进程或用户验收。

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
| product_id | 历史接口中的业务域/系统标识 | C3/C6 / context | 按上下文显示商业运营或品牌市场 | CTH / ZBMP / SYSTEM | PRODUCT_CTH / PRODUCT_ZBMP | YES | 字段名不意味着多个产品 | `subject_context.py:15` | PERSISTED_AND_API_MAPPING_REVIEW | REPAIRED_AFFECTED_VERIFICATION |
| domain_id | 调用与数据合同中的领域标识 | C3/C6 / domain isolation | 领域 | cth / zbmp / system；合同限定别名 | bmp | YES | UNKNOWN/BMP别名不得静默成为CTH | `domain_isolation.py:39` | PERSISTED_CALLER_AND_API_REVIEW | REPAIRED_AFFECTED_VERIFICATION |
| Subject | 具体商业主体及其稳定身份与范围 | C1/C3 / registry | 商业主体 | subject_id / scope.subject_id | CTH_SUBJECT_ID | YES | 同名/跨城/商场/门店不合并 | `subject_context.py:19` | REFERENCE_DEFAULT_CALLER_REVIEW | REPAIRED_AFFECTED_VERIFICATION |
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
| NEED_VERIFY — auth metadata | 已有认证元数据但未核当前连通 | C1 / legacy status API | 登录状态待检查 | cookie_status=NEED_VERIFY | NEED_VERIFY | YES | 不能直接等同平台验证码挑战 | `collector_status_api.py:9` | PRESENTATION_REASON_BINDING_REVIEW | OWNER_QUALIFIED_IN_API |
| NEED_VERIFY — collector guard | 平台要求合法人机验证，受影响路径等待 | C1/C6 / risk guard | 需要平台验证 | guard.state=need_verify | NEED_VERIFY | YES | 不能解释成可继续自动请求 | `lumenis/system/collector/guard/state.py:23` | NO_ENUM_RENAME | OWNER_QUALIFIED_IN_API |
| READY — query plan | 计划及有效查询已形成，仍须执行准入 | C1 / acquisition plan | 查询计划已准备 | plan.status=READY | READY | YES | 计划就绪≠Session/GPU/成果就绪 | `lumenis/system/collector/acquisition_plan.py:25` | NO_ENUM_RENAME | OWNER_QUALIFIED_IN_API |
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
| Provider registry status | 兼容路由的登记状态 | C2 / providers+channel | 不能代替产品推理可用性 | ACTIVE_FALLBACK / AVAILABLE / DISABLED | configured=working | YES | 旧ARK兜底登记不证明owned执行或授权 | `lumenis/system/ai_gateway/providers.py:14` | CALLER_AND_APPROVAL_REVIEW | COMPATIBILITY_ONLY_NOT_CALLABLE |
| Public Website | 一个产品在该目标端的体验；共用Core与事实 | F/C6 / Experience | 官网 | 现有 website/ 或 app/ 路由 | 历史单端部署词 | YES | 端存在不代表业务闭环；不同端不建重复真相 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:92` | NO | CALIBRATED |
| Web Workspace | 一个产品在该目标端的体验；共用Core与事实 | F/C6 / Experience | Web工作区 | 现有 website/ 或 app/ 路由 | 历史单端部署词 | YES | 端存在不代表业务闭环；不同端不建重复真相 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:93` | NO | CALIBRATED |
| Desktop | 一个产品在该目标端的体验；共用Core与事实 | F/C6 / Experience | 桌面端 | 现有 website/ 或 app/ 路由 | Desktop App | YES | 端存在不代表业务闭环；不同端不建重复真相 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:40` | NO | CALIBRATED |
| Mobile Companion | 一个产品在该目标端的体验；共用Core与事实 | F/C6 / Experience | 移动伴随端 | 现有 website/ 或 app/ 路由 | 历史单端部署词 | YES | 端存在不代表业务闭环；不同端不建重复真相 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:95` | NO | CALIBRATED |

## 覆盖与限制

源码事实优先；所有行有当前文件 SHA、行号、固定基线链接。若 same_bytes_as_published=false，不能把本地行号/内容宣称已在该固定提交发布。历史原件与现存 ID 保留；本轮不执行数据库枚举迁移。未进行四端逐屏实机验证、完整请求权限链重放或全部 Provider 调用追踪；这些对应上表待执行的现有 Owner 工作，不是本轮研究已完成的能力。


## 2026-10-08 同版本收尾证据

- 在基线 `6ff2cc0b68d8b9c3ae8ea658678242df8deac7dc` 的临时验证目录只叠加本轮获准修复；原有 dirty 实现没有混入。使用显式空种子 SQLite、离线模式，不以生产数据运行测试。
- 50 个受影响/邻接测试模块覆盖 **1,092** 个用例。首次 **1,082 通过、10 失败**；10 项是底层测试未选域及退役Provider旧断言。保留正常成功、审批、幂等和fallback语义后，分别复验Permission App全模块 **40通过**、Provider相关类 **11通过**，逐项对照首次失败的用例ID全部已解决。不把复验重复用例累加为新覆盖量。
- 宪章、治理机器合同、CURRENT接管治理、数据库权威、单产品五项强制门禁通过。精确JUnit散列、已解决用例ID和源码散列见同名JSON `repair_verification`；完整本机日志保存在 `序境-convergence-backups/semantic-repair-20261008-002702`。
- 原有21项未发布本地资产完整保留。其中app.py仅独立发布4处本轮必要调用改动；其他原有改动未混入。任务途中另一路治理提交 `3f9a9840` 已发布，作为本提交父版本保留；其新增检查已补齐提交前 `--staged` 与提交后HEAD分离，13项测试及26个子断言通过。
- 本轮同步代码、README、AGENTS、CURRENT、架构语义、Owner入口及Math采用记录。运行进程未重启加载、Production DB未改、未训练、未触发网络采集，完整产品和用户重复验收仍单列。

## 发布后 CI 的调用链回归收尾

提交 `288f222decb48e2c8e9217c712e7af6f6c1aa9ce` 的
[App Gate](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/37662512015)
通过；同提交的
[Product Gate](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/37662512186)
在第一个 hermetic shard 失败。上述 1,092 项局部覆盖不等于完整 CI 通过。

新增失败分为两类：独立 PermissionGate 用例未声明域；通用统计、笔记与系统状态的旧调用仍依赖隐式主体。前者必须补齐真实测试上下文并保留原权限断言；后者必须修复实际读取链，不能恢复默认广州主体、放宽权限或用空响应冒充正常结果。

同类检查同时校准否定用例：断言拒绝时也须具备正确域，以免实际因 `DOMAIN_NOT_SELECTED` 拒绝，却误认为验证了目标权限规则。继续使用显式隔离数据库；原有 21 项未发布本地资产按 `CI-FOLLOWUP-PROTECTED.json` 冻结保护。后续验证结果在此记录，原失败证据保留。

### CI 调用链修复验证

在 `288f222d` 的干净归档中叠加精确获准源码，26 个受影响模块执行 515 项：510 通过、5 失败。五项分别是旧 API 无域断言、状态兼容字段遗漏、L4 正常任务夹具未建正式注册/授权/来源记录、PPTX 测试运行环境缺已声明的可选依赖。现已修复；34 项受影响复验全部通过，复验与原集合重叠，不累加覆盖数量。FFmpeg/ffprobe 使用已安装工具的明确路径，图像/音视频15项通过，未把环境缺工具误报为素材损坏。

实际产品修复保留显式业务域、签名 Canonical 范围和 Permission：旧笔记投影不跨 Subject；查询/统计超过1000条仍按真实范围，未知指标不补0；报告/提案入口不暗用广州参考主体；SYSTEM不伪装业务域。L4 正常路径使用隔离库中的注册主体、真实授权、Source/Evidence/Canonical记录，成功返回原有业务结果。否定用例同样补齐域，避免因无关拒绝掩盖真正权限缺陷。

八项适用治理/数据/体验门禁通过。各运行日志与JUnit保留于原备份目录；新提交的线上CI以实际run为准。此处证明工程修复，没有启动产品Core、修改Production DB、运行Owned模型或完成人工用户验收。

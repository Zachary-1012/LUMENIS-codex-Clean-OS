# 历史数据与业务规则 · 适配性融合迁移规范 V1.0（不是搬数，按规划/规则与当前双域功能适配）

> 用户强调：不是把东西写进来就行，必须和功能结合、按既有规划与规则、与现在双域架构适配，严禁整包灌入/恢复旧版/搞乱。

## 一、数据源真实盘点（先备份，只读盘点）
- 当前主库 `data\monitor.db`：72 表/13170 行（notes=6、events/comment 空、kos/schedule/v4/intelligence 等有数据）——**迁移目标，结构以此为准**。
- 历史富矿 `D:\Taikoo-staging-ui\staging\monitor.staging.db`：53 表/13187 行，**notes=957、note_comments=141、events=427、web_mentions=79、topic_campaign_notes=120**。
- `data\backups\before_recovery_*` 5 个（5958–7077 行，notes=3，多为运行/调度/业务表，逐表甄别有用数据）。
- `data\` 60 个原始采集 JSON（search_*/xhs_live_*/rednote_cdp_*、collector-metrics.jsonl，共 1.1MB）。
- 规则来源：当前代码 + staging/security/backups 里实现过的规则 + intelligence_library/OSAI/ADRH 研究成果。

## 二、铁律：适配融合 ≠ 搬数（违者返工）
1. 禁止 raw dump、禁止照搬旧 53 表 schema、禁止用旧库/旧 UI/旧逻辑覆盖当前主线；当前 72 表 schema 是唯一目标结构，旧字段做**映射适配**（缺的补、废弃的不硬塞）。
2. 每条历史数据必须走当前**完整功能管线**并绑定到消费它的具体功能/API/页面，不为存而存。
3. 只增不删、幂等可重跑（note_id/platform_id/content_hash 做 upsert），先整库备份当前 monitor.db。
4. 拿不准域归属/规则命中的标 unknown 列清单，不硬归、不编。

## 三、历史数据迁移管线（每批必走，和功能结合）
Raw(旧库/JSON) → Normalize(**字段映射到当前 schema**) → **subject_rules 红线重判(SUBJECT_WORDS/EXCLUDE/subject_hit，不沿用旧判定标签)** → data_quality_gate 质量门禁(失败显式记录) → Canonical → **Domain Adapter 打 product_id/domain_id** → 风险/Evidence → upsert 入库 → **后端函数实时驱动前端**。
- **双时间铁律**：publish_datetime=平台发布时间、captured_at/collected_at=采集时刻，严格分离；相对时间(几分钟前/昨天/日期)可靠归一化到绝对时间；缺失按 tests/_patch_logs 的回填规则补 publish，**绝不允许 publish_datetime=captured_at**。
- **精准去重**：content_hash+platform_id（跨旧库/文件/现网合并不重复、不因标题相似误删）；评论/详情失败显式记录不丢。
- 缺失显式 null/unknown/missing，禁 0/"未知"静默填充、禁估算。

## 四、双域归属（不串域、不污染）
- 小红书·太古汇/199 品牌/9 业态/太古汇事件 → **CTH**；web 品牌传播/竞品/品牌声量 → **ZBMP**；Canonical/Evidence/Runtime 等底座 → **Shared**。
- 199 品牌/9 业态过滤只作用于 CTH，不得成为 ZBMP 隐式全局条件；域归属规则固化为可测函数并加用例。

## 五、业务规则全量找回 + 功能映射（规则不丢、不冲突）
统一做一张《规则功能映射表》并逐项适配：每条规则记录「来源(旧实现/研究文档路径) → 当前对应模块/函数 → 现状(已具备/缺失/冲突) → 适配动作 → 所属域」。覆盖：双时间口径、subject 主体、平台采集口径、去重、风险阈值与状态枚举(unknown 不并 negative、critical≠high、0/0≠0)、KOS 平台规则(官方规则+研究、不写死公式)、指标口径、报告结构、AI 判定与 prompt、证据/评估、账户权限。当前已具备的保留不重写，缺的按当前架构补，冲突的以当前双域规划为准。

## 六、安全步骤与对账（先方案后执行，不出错）
1. 先出《源表→目标表/字段映射 + 域归属 + 规则命中 + 对账口径》方案，再动手。
2. 整库备份当前 monitor.db；小批量试迁（如 20–50 条/表）→ 校验字段、双时间、subject 与域打标、去重 → 对账通过再全量。
3. 逐表对账并回报：源计数 / 成功新增 / 重复跳过 / 失败(带原因) / 各域各表最终计数；总数对不上必须能解释。
4. 迁完由现有后端函数/API 真实读出并在 ZBMP/CTH 功能页呈现与计算指标，验证前后端契约一致、无 Mock/写死。
5. 全程不删任何源数据与备份；废弃代码清理与数据迁移严格分开，清理绝不碰 data 与 db。

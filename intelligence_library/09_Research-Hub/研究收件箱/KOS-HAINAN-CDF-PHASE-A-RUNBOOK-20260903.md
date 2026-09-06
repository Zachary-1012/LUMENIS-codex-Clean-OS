# KOS 中免海南 Phase A 采集执行清单（Runbook）

> 研究侧（OSAI）交付 · 供生产侧（Z-Brand-Core）执行
> 日期：2026-09-03 · 品牌案例：中国旅游集团中免 / cdf 海南免税

## 一、物料就绪状态

| 项 | 状态 | 说明 |
|----|------|------|
| 品牌 profile | ✅ 已就绪 | `config/kos_monitor_profiles/hainan_cdf.json`（ACTIVE_TEST_PROFILE） |
| subject_terms | ✅ 12 项 | 中免/cdf/三亚国际免税城/海口国际免税城/海南免税等 |
| exclude_terms | ✅ 3 项 | 韩国/日本免税、机场免税店攻略（非中免） |
| 实体消歧 | ✅ 5 项 | 海免/海旅/深免/中服/海控 不合并（无证据不合并） |
| KOS 候选规则 | ✅ | 身份+相关内容双要件；禁止无证据虚构雇佣关系 |
| SABC 分层 | ✅ | 6 维度权重（质量/互动/相关/一致/事件/风险） |
| 采集引擎消费入口 | ✅ 已开发 | `collector_v2/run_profile.py`：profile 驱动采集（--brand hainan_cdf 或激活品牌）；`python -m collector_v2.run_profile --dry-run` 预览关键词 |

## 二、采集范围（建议）

- 平台：小红书（主平台，platform_priority）
- 账号：双账号 XHS_CN_PRIMARY / XHS_RETINAUT（第三身份 DENY）
- 检索词（基于 subject_terms 展开）：
  - 品牌：中免、cdf、中国免税、中免海南、海南免税
  - 门店：三亚国际免税城、海口国际免税城、中免集团三亚市内免税店
  - 场景：海南免税购物、免税店攻略、离岛免税、封关后免税
  - 活动：中免海南免税购物节、双11、店庆
- 排除：韩国/日本免税、非中免机场免税店攻略、海免/海旅/深免/中服主体内容（消歧，不合并进中免）

## 三、运行前置检查（启动采集前逐项确认）

1. 双账号登录态就绪（XHS_CN_PRIMARY / XHS_RETINAUT），无 AUTH_REQUIRED
2. 采集身份白名单仅两账号，第三身份 DENY
3. 遵守安全冻结边界：不模拟真人、不代理/IP 切换、不账号轮换绕过平台安全
4. 确认采集任务绑定 hainan_cdf profile（或按 profile 生成任务）
5. 采集频率/配额符合平台限制（ai-quota、collector_guard）

## 四、验收标准（首采产出）

- KOS 候选：按 profile 规则识别（身份+相关内容双要件），不虚构雇佣
- 分层分布：S/A/B/C 计数 + 高/低产出画像
- Top 内容与 Top 主体：按互动/相关度排序
- 新兴主题/风险主体：识别并标注
- 溯源：每条结论可回源到笔记 URL
- 手动回填项（WeCom/Sales/Boosting 预算）：通过 `/api/kos/manual` 录入（Phase A 无官方 API 前）

## 五、遗留与依赖

- 真实采集需用户在场启动（双账号登录态 + 账号授权）：`python -m collector_v2.run_profile --cdp-url <ws>`（ZBC 侧）
- Phase B 聚光自动归因：用户提供凭证（JUGUANG_CLIENT_ID/SECRET/ACCESS_TOKEN/ADVERTISER_ID 环境变量）后激活，`juguang_api.py` 已预留对接点（未配置返回 pending）
- 成本/转化指标在 Phase A 用 `/api/kos/manual` 手动回填（KM-02，前端已提供回填表单 UI），聚光认证后自动归因
- 主体口径已品牌化：`subject_sql_and_values_for('hainan_cdf')` / `collect_keywords_for('hainan_cdf')` 已就绪

## 六、与已有资产的关系

- 中免研究基线：`research-inbox/CDF-HAILAN-DEEP-RESEARCH-20260903.md`
- KOS 基线/规则：`KOS-BASELINE-HAILAN-CDF-20260903.md`、`KOS-RULES-CONTENT-ENGAGEMENT-20260903.md`
- 测量契约：`contracts/CTR-KOS-METRICS-P1-01.md`（ZBC 已施工 KM-01~06）
- 对标基准：DFS Y26 H1 真实标杆（CPL ¥57.32 / OA ¥9.36，已内置 channel_roi）

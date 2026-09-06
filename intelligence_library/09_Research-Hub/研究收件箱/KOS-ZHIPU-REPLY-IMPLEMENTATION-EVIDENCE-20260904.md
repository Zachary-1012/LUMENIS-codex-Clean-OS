# KOS 评论回复 / 私信触达 · 智谱 AI 接入 — Implementation Evidence

> 日期：2026-09-04
> 双库：OSAI（Intelligence）→ Contract/规格 → ZBC（Core）→ Evidence → 回 OSAI
> 依据：用户指令「继续加速推进，别忘了智谱设定好的模式」+「按 P0 级别最高标准执行」

---

## 1. 变更（ZBC）

| 文件 | 变更 |
|---|---|
| `kos_engine.py` | `generate_reply` / `generate_outreach` 由纯规则模板升级为「智谱 AI 生成建议 + 规则兜底」；新增 `_ai_generate_reply` / `_ai_generate_outreach`；返回新增 `ai_source` 标记 |
| `CHANGELOG.md` | 追加 5.9.9-t3 施工记录（AGENTS §16 十要素） |
| `tests/test_kos_reply_zhipu.py` | 新增正式回归测试（14 用例，mock 智谱，CI 可复现） |

## 2. 智谱模式（唯一外接 AI provider）

- `AI_PROVIDER=zhipu`；云智(ARK) 已删除
- 分层：默认 `glm-4.5-air`（ZHIPU_MODEL）；negative_feedback / purchase_intent 走 `glm-5.3`（ZHIPU_STRONG_MODEL）；视觉 `glm-4.6v`（ZHIPU_VISION_MODEL）
- 网关：`intelligence._chat`（脱敏 redact_for_cloud、glm-5.3 思考模型 reasoning_content 兜底、失败回退 rule）
- 资源包：glm-4.5-air 31.8M tokens、glm-4.7 5M、glm-4.6v 6M（ai-quota.json）

## 3. 边界合规（红线）

- AI 只生成建议，`auto_reply=False` / 触达 `DRAFT`，不自动发送
- 高风险评论 → `NO_REPLY`（规则优先，AI 不得越权）
- 不虚构事实、不承诺未确认权益/报酬
- 官方账号只读红线不受影响（无任何账号写操作）
- 失败回退规则模板，不崩溃
- 测试数据已清理（生产库无污染）

## 4. 测试证据

| 层 | 结果 |
|---|---|
| 静态 | `py_compile kos_engine.py` OK |
| 单测 | `tests/test_kos_reply_zhipu.py` **14 passed**（规则层 5 + 智谱集成层 6 + 触达层 4） |
| E2E（真实 API + 真实智谱） | POST /api/kos/reply/generate：正面→200 SUGGEST_REPLY ai_source=True auto_reply=False；购买意向→200 ai_source=True；高风险→200 NO_REPLY。POST /api/kos/outreach：→200 DRAFT ai_source=True |
| 智谱真实调用 | ai_status=True zhipu glm-4.5-air；strong_model=glm-5.3；`_chat` 返回真实内容 |
| 全量回归 | `pytest tests/` **750 tests collected，全量执行 exit=0（全部通过）**；含 security_scanner_s2（单独跑 5 passed） |
| 安全 | 提交文件无密钥（ZHIPU_API_KEY 等仅存 .env 未跟踪）；.env 被 .gitignore 拦截 |

## 5. Commit（ZBC · main）

- `8ede00f` feat(kos): 评论回复/私信触达接入智谱AI生成建议（+71/-2）
- `9d9fc05` docs(changelog): 5.9.9-t3 施工记录
- 后续：用户并行线 `a57c864`（V3/AppEvidence 懒加载收敛）在 9d9fc05 之后，本地=远端同步

## 6. 未完成项 / 风险

- 前端评论回复面板「AI 生成」按钮可后续接（kos_routes.py 已暴露 /api/kos/reply/generate）
- 聚光 Boosting/私信线索自动归因待用户提供 JUGUANG_CLIENT_ID/SECRET/ACCESS_TOKEN/ADVERTISER_ID 环境变量（juguang_api.py 已预留）
- 智谱网关依赖 app.py 启动时 `_load_dotenv` 注入 .env（独立脚本需手动加载）

## 7. 下一步

- 中免首采回填后启用真实评论批量建议（run_profile.py 已就绪，遵守采集门：手动≤30min / 自动 00:00·12:00）
- 接入前端回填 UI（评论回复建议 → 人工确认 → 留资/私信 DRAFT）
- 聚光 Phase B 凭证到位后激活自动归因

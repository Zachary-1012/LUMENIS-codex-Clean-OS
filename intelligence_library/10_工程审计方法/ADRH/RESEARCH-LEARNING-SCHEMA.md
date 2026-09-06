# Research Learning Schema

> Hub 研究记录数据契约。兼容 DDC `zachary.platform.research-learning.v1` schema，并扩展 Research ID 与三方验证字段。

## 1. Schema 版本

- Hub schema：`zachary.hub.research.v1`
- 兼容 DDC schema：`zachary.platform.research-learning.v1`（来源：DDC `tools/research_learning.py`，commit `878ebbf`）

## 2. DDC 已有能力（不重复实现）

DDC `tools/research_learning.py` 已提供：
- JSONL 文件存储，无依赖
- 状态枚举：`candidate / shadow / review / verified / hold / rejected / promoted`
- 类型枚举：`research / experiment / shadow / evidence / review / capability`
- 必填字段校验：`id / record_type / created_at / source / owner / summary / status`
- `verified` / `promoted` 必须有 `evidence_refs`
- 敏感信息自动过滤（token / password / cookie / secret / api_key）
- commit SHA 格式校验

Hub 通过 `src/adapters/ddc_research_adapter.py` 读写兼容格式，**不复制 DDC 实现**。

## 3. Hub 扩展字段

在 DDC schema 基础上，Hub Research Record 增加：

| 字段 | 类型 | 说明 |
|---|---|---|
| `research_id` | string | `R-YYYY-NNNN` 格式，Hub 唯一标识 |
| `ai_agent` | string | `ChatGPT` / `豆包` / `both` |
| `review_by` | string | Review 方 AI |
| `review_opinion` | string | Review 具体意见 |
| `zbrand_validation` | object | Z-Brand 业务验证结果 |
| `ddc_validation` | object | DDC 工程验证结果 |
| `sici_validation` | object | SICI 移动验证结果 |
| `hypothesis` | string | 研究假设 |
| `findings` | string | 研究发现 |
| `learning_result` | string | 学习成果 |

## 4. 状态机

```text
research → hypothesis → candidate → shadow → evidence → review → verified → promoted
                              └────────→ hold / rejected
```

与 DDC 状态映射：

| Hub 阶段 | DDC status | 说明 |
|---|---|---|
| Research | `candidate` (record_type=research) | 初始研究 |
| Hypothesis | `candidate` | 假设形成 |
| Candidate | `candidate` | 候选能力 |
| Shadow | `shadow` | Shadow 运行中 |
| Evidence | `shadow` → 收集 evidence_refs | 证据收集 |
| Review | `review` | AI 互相 Review |
| Verify | `verified` | 三方验证通过 |
| Promotion Candidate | `verified` | 待晋级 |
| Reusable Capability | `promoted` | 进入 Capability Registry |

## 5. 文件格式

存储位置：`data/research/records.jsonl`（每行一个 JSON 对象）

示例：

```json
{
  "schema": "zachary.hub.research.v1",
  "research_id": "R-2026-0001",
  "id": "RL-COMPAT-ID",
  "record_type": "research",
  "created_at": "2026-08-31T15:00:00+00:00",
  "source": "hub-initialization",
  "owner": "hub",
  "ai_agent": "豆包",
  "summary": "Hub 仓库创建与基础架构",
  "status": "verified",
  "repository": "Zachary-1012/AI-Development-Research-Hub",
  "commit_sha": "<commit-sha>",
  "evidence_refs": ["tests/test_research_record.py"],
  "test_refs": ["tests/test_research_record.py"],
  "hypothesis": "独立 Hub 可减少三仓库重复研究",
  "findings": "DDC 已有 research_learning 栈，Hub 通过 Adapter 复用",
  "zbrand_validation": {"status": "not_applicable", "note": "Hub 初始化不影响业务"},
  "ddc_validation": {"status": "pass", "note": "兼容 DDC schema"},
  "sici_validation": {"status": "not_applicable", "note": "Hub 初始化不影响移动端"}
}
```

## 6. 验证规则

1. `research_id` 必须匹配 `^R-\d{4}-\d{4}$`
2. `status` 为 `verified` 或 `promoted` 时，`evidence_refs` 不能为空（继承 DDC 规则）
3. `ai_agent` 必须是 `ChatGPT` / `豆包` / `both` 之一
4. 三方验证字段中，至少一方为 `pass` 才能进入 `verified`
5. 敏感字段自动过滤（继承 DDC `sanitize`）

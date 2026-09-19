# Global → OSAI Contribution Bridge

> FINAL CLOSEOUT 收口文档。Global 不创建 Contribution Adapter/Outbox，本文档定义字段映射、生命周期映射与一行转换命令，确保 Global 的 research records 可被人工或脚本转换为 OSAI Receiver 兼容格式。

## 1. 决策：不创建 Global Contribution Adapter

### 理由

| # | 理由 | 说明 |
|---|------|------|
| 1 | Global 是研究契约/适配器库，非运行时服务 | 无 event loop、无 worker、无 outbox 语义；research records 是 append-only 研究产物，不是待投递的 contribution |
| 2 | ZBC 已完整覆盖 E2E 链路 | ZBC 的 `evidence_exporter` 可产出 OSAI 兼容 outbox JSONL，满足 `ZBC → Contribution → Local Outbox → OSAI Receiver` 完整链路要求 |
| 3 | 两域概念不同，强行适配会混淆 | Global research record 是研究过程台账（含 hypothesis/findings/reviews/validation），OSAI contribution 是可泛化学习资产的投递单元；二者粒度与语义不同 |
| 4 | 增加 Adapter 引入不必要复杂度 | 新代码路径 + 测试 + 维护负担，用于一个 ZBC 已满足的用例，违反"不重复实现"基线 |
| 5 | 转换可由一行命令完成 | Global records 结构稳定（`zachary.hub.research.v1`），字段映射确定，无需专用模块 |

### 边界

- 本文档**不**改变 Global 任何业务逻辑、契约或现有数据
- 转换是**离线、只读**操作：读取 `data/research/records.jsonl`，输出到指定 outbox 路径，不回写 Global
- 若未来 Global 需要成为 OSAI contribution 的一等来源，可基于本文档映射表新建 adapter，但当前 FINAL CLOSEOUT 不要求

## 2. 字段映射表

OSAI Receiver 期望的 contribution 格式（最小集）：

```json
{
  "contribution_id": "string",
  "title": "string",
  "content": "string",
  "source": "string",
  "schema_version": "1.x"
}
```

Global research record（`zachary.hub.research.v1`）→ OSAI contribution 映射：

| OSAI 字段 | Global 来源字段 | 转换规则 | 示例 |
|-----------|----------------|----------|------|
| `contribution_id` | `research_id` | 直接使用，保持唯一性 | `R-2026-0001` |
| `title` | `research_question` → 回退 `summary[:120]` | 优先取 research_question；为空时取 summary 前 120 字符 | `"建立三产品共享的 AI 研发中枢 Hub..."` |
| `content` | `summary` + `findings` + `learning_result` | 三段拼接，用 `\n\n---\n\n` 分隔；空段跳过 | 见下方示例 |
| `source` | `"global-hub:" + source` | 加 `global-hub:` 前缀以区分来源系统 | `"global-hub:zachary-ai-platform-co-development"` |
| `schema_version` | 常量 `"1.0"` | OSAI contribution schema 版本 | `"1.0"` |

### content 拼接示例

```
[summary]
Hub 验证闭环：Review机制...

---

[findings]
DDC commit 878ebbf 已有完整 research_learning.py...

---

[learning_result]
建立了完整闭环样板：Research ID → Review → Case Index...
```

### 可选扩展字段（OSAI Receiver 可忽略，不影响兼容）

如需保留更多 Global 元数据，可在 contribution 中附加以下字段（OSAI Receiver 应容忍未知字段）：

| 扩展字段 | Global 来源 | 用途 |
|----------|------------|------|
| `global_status` | `status` | Global 生命周期状态，便于溯源 |
| `global_repository` | `repository` | 关联仓库 |
| `global_observed_sha` | `observed_sha` | 研究时的 commit SHA |
| `global_evidence_refs` | `evidence_refs` | 证据引用列表 |
| `global_created_at` | `created_at` | 研究记录创建时间 |

## 3. 生命周期状态映射表

Global ShadowLifecycle 与 OSAI LearningAssetRecord 是**不同域**的状态机，不需要统一。下表提供可理解的对应关系，用于人工溯源与跨系统理解。

### Global ShadowLifecycle 状态（`src/contracts/research_record.py` STATUSES）

```
research → hypothesis → candidate → shadow → evidence → review → verified → promotion_candidate → reusable
                                                                                              ↳ hold / rejected
```

### OSAI LearningAssetRecord 状态

```
RECEIVED → VALIDATED → GENERALIZABLE → ADMITTED → LEARNING_ASSET
                                                    ↳ REJECTED
```

### 映射表

| Global 状态 | 含义 | OSAI 对应状态 | 映射说明 |
|------------|------|---------------|----------|
| `research` | 研究问题已提出，初步探索 | `RECEIVED` | 研究刚启动，相当于 contribution 刚被接收 |
| `hypothesis` | 假设已形成，待验证 | `RECEIVED` | 仍在早期，未进入验证 |
| `candidate` | 候选方案，待 shadow 验证 | `VALIDATED`（弱） | 有初步结构，但尚未实证 |
| `shadow` | Shadow 模式运行中，收集数据 | `VALIDATED` | 有运行数据，但未形成证据 |
| `evidence` | 已有证据，待 review | `GENERALIZABLE`（弱） | 有实证结果，但是否可泛化待审 |
| `review` | 正在接受 AI/人工 review | `GENERALIZABLE` | 评审中，判断是否可泛化 |
| `verified` | 已验证通过 | `ADMITTED` | 验证完成，可被系统接纳 |
| `promotion_candidate` | 候选推广，待最终审批 | `ADMITTED` | 已接纳，待晋升为正式资产 |
| `reusable` | 已成为可复用能力 | `LEARNING_ASSET` | 最终态，可被三产品反哺复用 |
| `hold` | 暂停，待条件满足 | （无直接对应） | Global 特有暂停态，OSAI 无对应 |
| `rejected` | 被拒绝 | `REJECTED` | 直接对应 |

### 映射原则

1. **非严格双射**：两个状态机粒度不同，Global 更细（9 个正向态），OSAI 更粗（5 个正向态）
2. **多对一**：Global 的 research/hypothesis 都映射到 OSAI RECEIVED；verified/promotion_candidate 都映射到 ADMITTED
3. **hold 无对应**：Global 的 hold 是研究暂停态，OSAI 没有暂停概念，转换时可忽略或映射为 RECEIVED（保留待处理）
4. **终态对应**：Global `reusable` ↔ OSAI `LEARNING_ASSET`，Global `rejected` ↔ OSAI `REJECTED`，这两组是严格对应
5. **不自动晋级**：状态映射仅用于展示/溯源，不触发任何自动状态流转

## 4. 一行转换命令

### 前置条件

- Python 3.10+（Global 运行环境）
- 工作目录为 Global 仓库根目录
- 输入文件：`data/research/records.jsonl`（已存在，8 条记录）

### 转换命令（PowerShell / cmd 通用）

```powershell
python -c "import json,pathlib; src=pathlib.Path('data/research/records.jsonl'); out=pathlib.Path('outbox/osai_contributions.jsonl'); out.parent.mkdir(parents=True,exist_ok=True); [out.open('a',encoding='utf-8').write(json.dumps({'contribution_id':r['research_id'],'title':r.get('research_question') or r.get('summary','')[:120],'content':'\n\n---\n\n'.join([f'[{k}]\n{v}' for k,v in [('summary',r.get('summary','')),('findings',r.get('findings','')),('learning_result',r.get('learning_result',''))] if v]),'source':'global-hub:'+r.get('source','unknown'),'schema_version':'1.0'},ensure_ascii=False)+'\n') for r in [json.loads(l) for l in src.read_text(encoding='utf-8-sig').splitlines() if l.strip()]]; print(f'Converted {sum(1 for _ in src.read_text(encoding=\"utf-8-sig\").splitlines() if _.strip())} records -> {out}')"
```

### 可读版（建议保存为 `tools/convert_to_osai.py` 时使用）

```python
"""Convert Global research records to OSAI contribution JSONL (offline, read-only)."""
import json
from pathlib import Path

SRC = Path("data/research/records.jsonl")
DST = Path("outbox/osai_contributions.jsonl")

def to_contribution(r: dict) -> dict:
    parts = []
    for key in ("summary", "findings", "learning_result"):
        val = r.get(key, "")
        if val:
            parts.append(f"[{key}]\n{val}")
    return {
        "contribution_id": r["research_id"],
        "title": r.get("research_question") or (r.get("summary", "") or "")[:120],
        "content": "\n\n---\n\n".join(parts),
        "source": "global-hub:" + r.get("source", "unknown"),
        "schema_version": "1.0",
    }

def main():
    records = [json.loads(l) for l in SRC.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    DST.parent.mkdir(parents=True, exist_ok=True)
    with DST.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(to_contribution(r), ensure_ascii=False) + "\n")
    print(f"Converted {len(records)} records -> {DST}")

if __name__ == "__main__":
    main()
```

### 验证转换结果

```powershell
# 检查输出文件存在且行数与输入一致
python -c "import json,pathlib; src=sum(1 for l in pathlib.Path('data/research/records.jsonl').read_text(encoding='utf-8-sig').splitlines() if l.strip()); dst=sum(1 for l in pathlib.Path('outbox/osai_contributions.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()); print(f'src={src} dst={dst} match={src==dst}')"

# 抽查第一条 contribution 的字段完整性
python -c "import json; r=json.loads(open('outbox/osai_contributions.jsonl',encoding='utf-8').readline()); print(json.dumps({k:r[k] for k in ('contribution_id','title','source','schema_version')},ensure_ascii=False,indent=2)); print(f'content_length={len(r[\"content\"])}')"
```

## 5. 输出示例

转换后 `outbox/osai_contributions.jsonl` 第一条（R-2026-0001）：

```json
{
  "contribution_id": "R-2026-0001",
  "title": "建立三产品共享的 AI 研发中枢 Hub，继承三方永久基线，不重复实现 DDC 已有能力，推进到验证闭环",
  "content": "[summary]\nHub 验证闭环：Review机制(reusable必须approved review)、Case Index(11案例)、Capability Registry v2(5能力+新字段)、repository_matrix、2个研究案例+ADR、68测试通过；R-2026-0001 经 ChatGPT 独立 Review = APPROVED\n\n---\n\n[findings]\nDDC commit 878ebbf 已有完整 research_learning.py/test/docs 栈；Hub 通过 adapter 兼容其 schema。...\n\n---\n\n[learning_result]\n建立了完整闭环样板：Research ID → Review → Case Index → Capability Registry v2 → 三方矩阵 → 测试 → Evidence，并通过双 AI 独立 Review。后续研究可直接复用此流程。",
  "source": "global-hub:zachary-ai-platform-co-development",
  "schema_version": "1.0"
}
```

## 6. 与 ZBC E2E 链路的关系

FINAL CLOSEOUT 要求至少一条完整 E2E 链路：`ZBC 或 Global → Contribution → Local Outbox → OSAI Receiver`。

- **ZBC 路径（已满足）**：ZBC `evidence_exporter` → outbox JSONL → OSAI Receiver
- **Global 路径（本文档启用）**：Global `records.jsonl` → 一行转换命令 → outbox JSONL → OSAI Receiver

两条路径独立，Global 路径不依赖 ZBC，反之亦然。Global 路径是**离线手动/脚本触发**，不进入 Global 的运行时流程。

## 7. 不做的事

- 不创建 `src/adapters/osai_contribution_adapter.py`
- 不创建 outbox 目录作为 Global 的永久组件（转换输出路径由调用方指定）
- 不修改 `data/research/records.jsonl`
- 不修改任何现有契约、适配器或测试
- 不增加 HTTP 服务、Docker、Worker、数据库、消息队列、第三方依赖
- 不自动触发转换（转换是显式手动操作）

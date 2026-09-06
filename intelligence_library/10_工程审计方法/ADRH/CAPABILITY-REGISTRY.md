# Capability Registry

> 经过完整生命周期验证的 reusable 能力注册中心。只有经过 Research → Experiment → Shadow → Evidence → Review → Verification 的能力才能进入 reusable 状态。

## 1. 注册条件

能力必须满足以下全部条件才能注册为 `reusable`：

1. 拥有唯一 Research ID
2. 完成 Shadow Learning 全生命周期
3. 拥有真实 Evidence（非 AI 输出）
4. 通过相关方三方验证
5. 定义了清晰的 Contract / Adapter 接口
6. 有测试覆盖
7. 不复制三仓库核心实现
8. 不扩大任何仓库的职责边界

## 2. 能力状态

| 状态 | 说明 |
|---|---|
| `proposed` | 已提议，未开始研究 |
| `researching` | 研究中 |
| `candidate` | 候选，实验中 |
| `shadow` | Shadow 运行中 |
| `verifying` | 三方验证中 |
| `reusable` | 可复用，三仓库可通过 Contract 使用 |
| `deprecated` | 已废弃，保留记录 |
| `rejected` | 已拒绝，保留失败记录 |

## 3. 注册表格式

存储位置：`data/learning/capability_registry.json`

```json
{
  "schema": "zachary.hub.capability.v1",
  "capabilities": [
    {
      "capability_id": "CAP-2026-0001",
      "name": "research-id-generator",
      "description": "生成唯一 Research ID (R-YYYY-NNNN)",
      "status": "reusable",
      "research_id": "R-2026-0001",
      "owner": "hub",
      "contract": "src/contracts/research_record.py",
      "adapter": null,
      "implementation": "tools/research_id.py",
      "tests": ["tests/test_research_record.py"],
      "evidence_refs": ["data/research/records.jsonl"],
      "validations": {
        "zbrand": "not_applicable",
        "ddc": "pass",
        "sici": "not_applicable"
      },
      "promoted_at": "2026-08-31T15:00:00+00:00",
      "used_by": []
    }
  ]
}
```

## 4. 能力使用规则

- 三仓库通过 Contract / Adapter 按需使用，不复制实现
- 使用方在 `used_by` 中登记（仓库名 + 用途）
- 能力变更必须经过新的 Research ID 和生命周期
- 废弃能力保留记录，不删除（只增不减）

## 5. 当前已注册能力

| Capability ID | 名称 | 状态 | Research ID | 说明 |
|---|---|---|---|---|
| CAP-2026-0001 | research-id-generator | reusable | R-2026-0001 | 唯一 Research ID 生成与校验 |
| CAP-2026-0002 | shadow-lifecycle | reusable | R-2026-0001 | Shadow Learning 状态机 |
| CAP-2026-0003 | ddc-research-adapter | reusable | R-2026-0001 | DDC research_learning 兼容适配器 |

## 6. 失败记录

失败的能力也保留记录，用于学习：

| Capability ID | 名称 | 状态 | 失败原因 |
|---|---|---|---|
| （暂无） | | | |

**目标：减少重复研究、减少重复失败。** 失败过的方向，后续研究必须先读取 Failure Record。

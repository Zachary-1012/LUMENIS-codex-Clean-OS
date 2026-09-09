# LUMENIS 自主优化集成门 V1

## 定位

Auto Research、Performance Race、Execution Efficiency Lab 是隔离研发能力，不是业务大模型，不是第三产品线，也不是 Production Truth Authority。

## 固定闭环

`Target → Baseline → Hypothesis → Isolated Experiment → Benchmark → Evidence → KEEP / REJECT → Human Review`

硬边界：

- 只能在 Shadow/隔离目录和隔离数据库副本运行。
- 不自动修改生产数据、生产规则、正式模型 Registry 或主分支。
- 质量、Evidence、安全任一下降即 `REJECT`；速度提升不能覆盖正确性下降。
- 必须限制 iterations、runtime、model calls、memory、concurrency 和 queue。
- 每项优化保留 Before、After、质量等价、资源变化、结论与未解决风险。
- 进入正式配置前必须通过测试、Git diff、Codex Review 与人工确认；禁止自动 merge/deploy。

## 当前方法来源

- `karpathy/autoresearch`：只采用固定时间预算、单一可变目标、测量后 KEEP/REJECT 的方法。
- `karpathy/nanochat`：只采用固定质量下比较 wall-clock 与可复现实验记录的方法。
- `ScalingIntelligence/KernelBench`：只借鉴正确性先于速度的验证思想；当前节点无真实 GPU workload，状态为 `NOT_REQUIRED_FOR_CURRENT_NODE`。

未复制上述项目源码。版本与许可见 `autonomous_engineering_research/research_projects.json`。

## Interaction Model 预留

`INTERACTION_MODEL_FUTURE` 只有 Adapter Contract 和 Provider Slot，状态固定为 `RESEARCH_ONLY`。在官方 Runtime、API、许可、部署条款和真实调用链全部验证前，不得宣称可用于生产。

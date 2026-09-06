# Platform Baseline — AI-Development-Research-Hub

> **IMMUTABLE BASELINE**
>
> 本文档定义 Hub 的平台基线。只增不减，不覆盖三方永久基线。

## 1. 继承的三方永久基线

Hub 完整继承并遵守以下永久基线（来源：DDC PLATFORM_README 第18节、SICI PLATFORM_README 第16节）：

> **三方反哺、互相验证、边界不破、能力共享、责任分明。**
>
> Z-Brand-Core 提供业务/生产真相；DDC 提供工程控制与验证真相；SICI-Core 提供移动交互与真实使用反馈。三方通过 Contract + Evidence + Test + Learning 形成闭环，任何一方都不能成为另外两方的无边界上级。

Hub 是三方共享的研发能力中枢，**不改变三方权责关系**，不成为第四方上级。

## 2. Hub 的角色边界

### Hub 是
- 三产品共享的研究 workspace
- 实验与 Shadow Learning 的隔离环境
- 案例库与基准测试的集中地
- Evidence 索引与跨仓库引用的协调层
- 经过验证的 reusable 能力的注册中心
- 公共研发工具（Research ID 生成、能力查询等）的宿主

### Hub 不是
- 生产 Runtime（三个产品不依赖 Hub 运行）
- 业务逻辑所有者（归 Z-Brand）
- 工程控制/权限/Release 门禁所有者（归 DDC）
- 移动 UI / 设备交互所有者（归 SICI）
- 凭证存储地
- AI 自动写生产代码的通道

## 3. 与三仓库的关系

```text
         ┌──────────────────────────────────┐
         │  AI-Development-Research-Hub     │
         │  Research / Experiment / Shadow  │
         │  Case Library / Benchmark        │
         │  Evidence Index / Capability Reg │
         └──────┬──────────┬──────────┬─────┘
                │ Contract │ Contract │ Contract
                │ /Adapter │ /Adapter │ /Adapter
        ┌───────▼───┐ ┌────▼─────┐ ┌─▼──────────┐
        │ Z-Brand   │ │ DDC      │ │ SICI       │
        │ 业务/生产  │ │ 工程控制  │ │ 手机端      │
        └───────────┘ └──────────┘ └────────────┘
```

- Hub → Z-Brand：提供业务适用性研究、品牌案例、市场情报研究
- Hub → DDC：复用 research_learning 契约、提供工程研究案例、能力晋级需 DDC 验证
- Hub → SICI：提供移动交互研究、设备约束实验、工作流案例
- 三仓库 → Hub：反馈研究需求、提供真实 Evidence、验证 reusable 能力

## 4. 能力流动规则

```text
研究需求（任一仓库）
  ↓
Hub Research（Research ID）
  ↓
Experiment / Shadow
  ↓
Evidence（来自真实运行/测试）
  ↓
三方 Review（Z-Brand 业务 + DDC 工程 + SICI 移动）
  ↓
Verification
  ↓
Capability Registry: reusable
  ↓
三仓库通过 Contract/Adapter 按需使用
```

**一个仓库验证成功，不代表另外两个自动成功。**

## 5. 数据隔离

- `data/research/`：研究记录，JSONL 格式，兼容 DDC schema
- `data/experiments/`：实验原始数据
- `data/shadow/`：Shadow 运行记录，**只读、不影响生产**
- `data/evidence/`：Evidence 索引（引用三仓库的真实 Evidence，不复制）
- `data/learning/`：学习成果沉淀

**所有数据文件不得包含 token、password、cookie、secret、API key。**

## 6. 不可变规则

1. Hub 不得成为任何正式产品的运行时依赖
2. Hub 不得复制三仓库的核心实现（通过 Adapter 引用）
3. Hub 不得自动改变生产行为
4. Hub 不得绕过 DDC 的工程验证门禁
5. Hub 不得覆盖或削弱三方永久基线
6. Hub 的 reusable 能力必须经过完整生命周期验证

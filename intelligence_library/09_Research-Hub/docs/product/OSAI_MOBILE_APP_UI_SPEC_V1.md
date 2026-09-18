# Zachary OSAI｜Mobile App UI / UX Specification V1

> P0 product-design baseline｜2026-09-02
>
> 目标：建立 Zachary OSAI 独立的移动端 AI Operating System 体验。它与 Z Brand Core 共享视觉 DNA，但不缩小复制 ZBC 的桌面后台。

## 1. 产品定位

**Zachary OSAI = Personal AI R&D Operating System**

移动端不是“聊天窗口”，而是用户随时查看世界、项目、研究、经验与 AI 状态的指挥入口。

核心体验：

> **Quiet Intelligence｜安静地思考，主动地工作。**

## 2. 与 ZBC 的关系

```text
ZBC
Professional Intelligence
Production Workspace

OSAI
Living Intelligence
Personal AI Operating System
```

共同 DNA：

- 侘寂黑白灰
- 高级留白
- 10 / 14 / 20px 圆角
- 六语义状态色
- 140 / 220 / 360ms 动效基线
- 高密度低装饰
- Evidence-first

差异：OSAI 允许更明显的“认知状态”和轻微空间感；不得变成霓虹科技风。

## 3. App Information Architecture

底部导航保持 5 个一级入口：

```text
Home
Research
Projects
Memory
Me
```

### Home｜当前世界

第一屏优先显示：

1. 今日重要事项
2. OSAI 主动洞察
3. 系统健康
4. P0 状态
5. 最近研究 / 学习
6. Ask Zachary

首页不是聊天历史列表。

## 4. Home 首屏模型

```text
Good morning.

TODAY
03 Important
07 Research
02 System

OSAI INSIGHT
发现一个可能影响 ZBMP 的新趋势。

[查看]

SYSTEM
ZBC Runtime      READY
CTH Collector    READY
OSAI Research    ACTIVE

Ask Zachary
```

数据必须来自真实 Runtime / Evidence；禁止静态伪造状态。

## 5. Research

Research 是 OSAI 的核心差异化入口。

分层：

```text
AI FRONTIER
PRODUCT INTELLIGENCE
MARKET INTELLIGENCE
COMPETITIVE INTELLIGENCE
CUSTOMER INTELLIGENCE
```

每条研究对象至少展示：

```text
NEW / MONITOR / RESEARCH / ADAPT / ADOPT / REJECT
↓
Why it matters
↓
Evidence
↓
Possible action
```

## 6. Projects

一级项目：

- Zachary OSAI
- Z Brand Core
- CTH-POMS
- ZBMP

但移动端不允许把 CTH/ZBMP 拆成新的代码仓库概念；它们仍属于 ZBC Core。

Project Detail 优先展示：

```text
Health
P0/P1/P2
Current Work
Evidence
Recent Changes
Next Decision
```

## 7. Memory / Experience

Memory 不以“记住了多少条”作为主体验。

优先展示：

```text
EXPERIENCE
↓
OUTCOME
↓
LEARNING
↓
FUTURE BEHAVIOR
```

示例：

> Experience #0231
>
> Browser Alive，但 Session Invalid 时，优先执行 Session Verify，而不是直接 Restart Browser。
>
> Evidence：3 次真实运行验证。

任何 Learned Rule 必须带来源与可信状态；未经验证的经验不得自动升级为生产规则。

## 8. AI Core / Chat

聊天是 OSAI 的一个入口，不是整个产品。

消息对象允许包含：

- Answer
- Research Card
- Evidence Card
- Tool Activity
- Decision Proposal
- Approval Request

AI 状态：

```text
IDLE
THINKING
RESEARCHING
VERIFYING
WAITING_APPROVAL
COMPLETED
FAILED
```

禁止使用无法对应 Runtime 的假进度。

## 9. Proactive Intelligence

OSAI 可以主动向 Home 投递 Insight，但必须经过：

```text
Signal
↓
Context
↓
Importance
↓
Evidence
↓
Actionability
↓
Interruption Policy
```

用户必须能：

- 查看证据
- 稍后处理
- 忽略
- 调整通知偏好

不能因为“主动”而骚扰用户。

## 10. AI Browser / Runtime 状态

移动端主要承担观察、授权和控制，不默认承担复杂浏览器操作。

例如小红书：

```text
READY
SESSION_EXPIRED
AUTH_REQUIRED
VERIFYING
COOLDOWN
BLOCKED
```

`AUTH_REQUIRED` 时，在 OSAI App 内展示明确的授权入口/弹窗状态；实际认证必须在受控 Browser Profile 中完成。

两个允许采集身份只能显示：

```text
XHS_CN_PRIMARY
XHS_RETINAUT
```

未知身份永远不出现在可选身份列表。

## 11. Experience Cards

OSAI 采用“智能对象”作为核心 UI 单元：

### Research Card

研究发现 + 证据 + 相关项目 + 下一动作

### Experience Card

经历 + 结果 + 学到什么 + 可信度

### Evidence Card

来源 + 时间 + 版本 + 结果 + 可复现状态

### Runtime Card

健康状态 + 最近心跳 + 最近成功 + 当前任务

### Opportunity Card

市场信号 + 产品缺口 + 价值 + 建议验证

卡片必须能进入详情，而不是仅展示装饰信息。

## 12. Motion Language

OSAI 比 ZBC 多一层“生命感”：

- Idle：极弱呼吸
- Thinking：缓慢扩散
- Researching：节点建立连接
- Learning：节点收拢形成 Experience
- Alert：只使用语义状态反馈，不使用震撼动画

默认 140 / 220 / 360ms；认知过程可使用 600–900ms，但必须尊重 `prefers-reduced-motion`。

## 13. Light / Dark Splash

### Light

`#F7F7F5` 米白画布 + `#171717` Z 标识 + 极淡灰信号节点。

### Dark

`#111111` 近黑画布 + 暖白标识 + 石墨层级 + 极低亮度信号节点。

视觉上与 ZBC `static/launch-screens/` 的品牌语言呼应，但不得直接复制 ZBC 页面布局。

## 14. 手机端交互原则

- 一屏一个主要意图
- 触控目标优先
- P0 / 风险优先于普通资讯
- 所有异步操作都有状态
- 所有失败都有解释与恢复入口
- 重要动作必须可撤销或二次确认
- 不让用户为了看一个状态进入多层后台
- 支持系统级深色模式
- 支持动态字体和辅助功能

## 15. Security / Permission UX

用户看到的不是“AI 拥有全部权限”，而是：

```text
Task
↓
Requested Capability
↓
Permission Scope
↓
Expiry
↓
Evidence
```

例如：

> 本次任务请求：读取 ZBC 测试结果
>
> 范围：当前任务
>
> 写入生产：DENY

任务结束自动回收临时权限。

## 16. 与 ZBC 的双向边界

```text
OSAI
Research / Learn / Plan / Contract
        ↓
ZBC
Implement / Test / Runtime / Release
        ↓
Evidence
        ↓
OSAI
Learn / Re-evaluate
```

OSAI 移动端可以观察 ZBC，但不得通过 UI 绕过生产权限直接修改核心业务真相。

## 17. MVP → V1 路线

### P0

- Splash Light/Dark
- Home
- Research
- Projects
- Memory/Experience
- AI Core
- Runtime Health
- Evidence
- Auth Required 状态
- Permission UX

### P1

- Proactive Insight
- Opportunity Cards
- Research Radar
- Experience DNA 浏览
- Voice / multimodal input

### P2

- 更丰富的 AI Browser 可视化
- Cognitive Map
- Autonomous Experiment Lab 可视化
- 个性化工作流

## 18. 验收标准

必须在真实设备上验证：

1. Light / Dark
2. iPhone 小屏 / 大屏
3. 网络慢 / 断网
4. AI Processing / Failed
5. Runtime Healthy / Degraded
6. Auth Required / Verify / Resume
7. P0 / Risk / Critical
8. Reduced Motion
9. Dynamic Type / Accessibility
10. 所有状态均来自真实数据或明确 Mock 层，不得伪装生产状态

## 19. 禁止

- 不做 ChatGPT Clone
- 不把桌面 ZBC 缩小成手机后台
- 不用大量渐变/霓虹/玻璃拟态
- 不用 AI “假思考”欺骗用户
- 不把未经验证的 Memory 变成规则
- 不把 AI 推测显示成事实
- 不在移动端暴露 Cookie / Token / Session 原文
- 不允许第三 XHS 身份
- 不通过 UI 绕过 Policy / Review / Evidence Gate

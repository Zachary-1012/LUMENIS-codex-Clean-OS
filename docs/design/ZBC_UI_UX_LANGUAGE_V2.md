# Z Brand Core｜UI / UX Design Language V2

> P0/P1 设计基线补充｜2026-09-02
>
> 本文是 Z Brand Core 当前视觉与交互语言的规范补充。它不改变生产业务真相、数据口径或架构 Owner；任何 UI 升级必须保持现有生产功能兼容。

## 1. 定位

**核心词：克制的智能感 / Professional Intelligence / Wabi-sabi / Evidence-first**

ZBC 不是消费级 AI 玩具，也不是传统数据后台。视觉目标是：安静、精准、可信、高密度但不拥挤，让用户感知系统正在工作，但不靠炫技表达智能。

## 2. 视觉 DNA

```text
侘寂黑白灰
+ 高级留白
+ 信息空间化
+ 微弱景深
+ 数据密度
+ 状态语义色
+ 轻量动效
+ Evidence 可见性
```

参考外部视觉案例时，吸收空间感、漂浮信息对象、层级和动态叙事；不得直接复制其品牌色、布局或视觉资产。

## 3. 色彩

### Light

- Canvas: `#F7F7F5`
- Surface: `#FFFFFF`
- Primary: `#171717`
- Secondary: `#6B6B68`
- Border: `#E6E5E1`
- Muted: `#A5A49F`

### Dark

- Canvas: `#111111`
- Surface: `#171717`
- Elevated: `#202020`
- Primary: `#F7F7F5`
- Secondary: `#B8B7B2`
- Border: `#30302E`
- Muted: `#777771`

### 六语义状态色

`SUCCESS / INFO / ATTENTION / RISK / CRITICAL / UNKNOWN`

状态色只用于表达状态，不用于大面积装饰。风险颜色必须有明确语义；禁止为了视觉冲击泛用红色。

## 4. 形态与层级

- 圆角基线：10 / 14 / 20px；仅在明确的浮层/系统对象中使用更大圆角。
- 卡片从“静态矩形”升级为 **Intelligence Card**：信息、状态、证据、动作在一个对象中表达。
- 可使用极轻微的层级阴影、透明度与景深，但不得形成玻璃拟态堆叠。
- 信息面板应优先通过层级、间距、边界和排版表达结构，而不是颜色。
- Dashboard 避免“Card Wall”；优先采用主事件 + 关联节点 + 证据 + 下一动作的空间化布局。

## 5. 动效

现有 140 / 220 / 360ms 基线继续保留。

建议：

- 120–160ms：hover、press、状态微变化
- 180–240ms：panel、card、tab
- 300–420ms：页面进入、modal、空间层级变化
- 600–900ms：仅用于 AI thinking / research / learning 等认知状态

所有动画必须回答“它在告诉用户什么”。禁止无意义循环动画、弹跳、霓虹光效和高频闪烁。

## 6. AI 交互语言

AI 不再只显示 `Loading...`。

统一使用可解释状态：

```text
AI_PROCESSING
AI_RESEARCHING
AI_VERIFYING
AI_NEEDS_REVIEW
AI_COMPLETED
AI_FAILED
```

示例：

> 正在分析｜正在关联 23 条相关情报
>
> 验证完成｜发现 3 个异常关联
>
> 需要进一步验证｜当前证据不足

AI 状态必须与真实 Runtime 状态绑定，禁止伪造进度。

## 7. 交互闭环

每一个用户动作至少要能理解：

```text
Intent
↓
Acknowledged
↓
Processing
↓
Result
↓
Next Action
```

错误状态必须提供：原因、影响、可恢复动作；空态必须解释为什么为空；重试必须有边界。

## 8. P0｜小红书 Auth / Session 交互

UI 必须把认证生命周期留在系统内部表达，不应因为 Session 失效而把用户突然踢到陌生浏览器页面。

```text
READY
 ↓
SESSION_EXPIRED / NEED_VERIFY
 ↓
系统内 AUTH_REQUIRED Modal
 ↓
正常扫码 / 登录
 ↓
SESSION_VERIFY
 ↓
READY
 ↓
RESUME TASK
```

两个允许采集身份 `XHS_CN_PRIMARY`、`XHS_RETINAUT` 必须始终独立显示、独立状态、独立 Browser Profile；未知身份不得出现在采集任务选择器中。

安全信号出现时 UI 必须明确显示 `STOP → COOLDOWN → HUMAN REVIEW`，不得用“采集 0 条”掩盖阻断。

## 9. Dashboard 信息空间

推荐结构：

```text
                Core Event
              /      |      \
          Brand   Consumer   Risk
             \       |       /
                Evidence
                    ↓
               Next Action
```

空间化仅用于帮助理解关系，不得牺牲数据可读性。

## 10. Light / Dark 启动页

### Light

米白画布、黑色 ZBC 标识、极淡灰色信号节点、编辑感排版、充足留白。

### Dark

近黑画布、暖白标识、石墨层级、低亮度信号节点；核心节点可做极弱呼吸效果。

两者必须是同一设计系统的 Light/Dark 变体，不得成为两套品牌。

## 11. 移动端 / Web

### Mobile-first

- 触控目标优先于桌面密度
- 核心状态和 P0 告警优先
- 复杂表格采用分层/横向滚动/详情抽屉，不强行压缩
- 操作结果必须可回退

### Web

- 多面板用于同时观察事件、证据、Runtime
- 支持键盘导航
- 不以移动端卡片堆叠替代桌面信息架构

## 12. 可访问性

- 不得仅依赖颜色表达状态
- 状态必须有文字/图标辅助
- 保持键盘焦点可见
- 支持 `prefers-reduced-motion`
- 动效不能阻断操作

## 13. 保护规则

UI 重构不得：

- 修改主体过滤规则
- 修改生产统计口径
- 修改报告周期定义
- 绕过 Auth / Policy / Circuit Breaker
- 隐藏 Runtime 错误
- 把 AI 推测显示成系统事实
- 删除已有生产功能仅为追求视觉简洁

## 14. 验收标准

任何 UI V2 变更至少验证：

1. Light / Dark 双主题
2. Desktop / Mobile
3. Loading / Empty / Error / Retry
4. AI Processing / Verify / Failed
5. Session Expired / Auth Required / Resume
6. P0 / Risk / Critical 状态
7. 键盘与 reduced-motion
8. 现有业务功能无回归
9. 无敏感信息进入 DOM、截图、日志或 Evidence

## 15. 与 OSAI 的关系

ZBC 保持：**Professional Intelligence / Production Workspace**。

Zachary OSAI 使用同一品牌 DNA，但拥有更强的“Living Intelligence”表达：Memory、Experience、Research、Proactivity、World Model。

二者共享 Design Tokens 与基础组件原则，不共享产品信息架构。

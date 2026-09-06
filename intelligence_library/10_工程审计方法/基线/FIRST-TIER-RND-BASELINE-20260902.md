# ZACHARY × ZBC 双子库第一梯队研发基线

> 状态：架构基线确认，已写入仓库（等待后续 AI 编程基线指令）
> 归档：OSAI 研究侧（双子星架构事实层）
> 原始来源：用户提供《ZACHARY × ZBC双子库第一梯队研发基线.docx》（2026-09-02）
> 重要：本文件用于建立研发事实与施工边界，不代表立即进行代码重构。写入完成后，必须等待后续 AI 编程基线指令，再进入代码审计与施工。

---

## 一、总目标

Zachary 当前仍处于：内部学习、内部进化、跟随产品研发成长阶段。
Zachary 暂时不是独立对外销售产品。

当前通过 ZBC 等实际产品研发过程，让 Zachary 持续获得：
- 真实研发任务 / 真实业务场景 / 真实用户行为反馈 / 真实执行结果
- 真实失败案例 / 真实测试 Evidence / 真实行业资料 / 真实案例学习 / 真实工具使用经验

最终形成：**Zachary 独立 AI Runtime**。未来成熟后，再单独将 Zachary 产品化。

---

## 二、最重要的架构原则

1. **Zachary 是通用 AI Runtime**
   Zachary 可以服务：ZBC、播客、未来产品、未来通用工具、用户个人任务、研究任务、内容任务、浏览器任务、数据任务、学习任务。
   但：Zachary 是**通用能力层**，不是任何一个产品的业务层。

---

## 三、严格禁止跨产品架构污染

必须建立 **Context Isolation**：

```
Zachary
├── ZBC Context
├── Podcast Context
├── Future Product Context
├── Personal Task Context
└── General Knowledge Context
```

允许共享：通用能力、技术知识、行业知识、工具能力、浏览器 Skill、通用方法论、已脱敏通用经验。

禁止自动共享：产品 Truth、产品业务规则、产品数据库、产品权限、产品配置、产品私有数据、产品 Runtime State、产品专属 Prompt、产品专属决策规则。

---

## 四、Zachary 与 ZBC 的关系

```
                 ZACHARY
                    │
          通用 AI Runtime
                    │
        ┌───────────┴───────────┐
        ↓                       ↓
      ZBC                  其他产品
```

ZBC 使用 Zachary；ZBC 生产过程产生的经过治理的数据、Evidence、Evaluation、反馈，可以成为 Zachary 的学习信号。

形成闭环：Zachary → 提供通用能力 → ZBC → 实际生产 → 用户使用 → 行为数据 → Evaluation → Learning Signal → Zachary。

**但必须经过**：隔离 → 脱敏 → Policy → Evaluation → Learning。不能把 ZBC 原始业务数据直接灌入 Zachary 全局记忆。

---

## 五、Browser Runtime Independence（P0-BR）

正式提升为：**P0-BR：Zachary Browser Runtime Independence**

目标：Zachary 自己拥有统一 Browser Contract，不依赖任何单一浏览器框架。

禁止：
- Zachary = Browser Use
- Zachary = Playwright
- Zachary = PinchTab

正确关系：

```
Zachary
 ↓
Browser Contract
 ↓
Browser Router
 ↓
Browser Provider
 ↓
具体 Runtime
```

---

## 六、浏览器技术分层

```
Layer 0  Browser Runtime
Layer 1  Browser Provider
Layer 2  Browser Adapter
Layer 3  Browser Contract
Layer 4  Browser State Machine
Layer 5  Browser Policy
Layer 6  Browser Skill Registry
Layer 7  Agent Planner
Layer 8  Evidence
Layer 9  Evaluation / Learning
```

---

## 七、第三方项目定位（第一梯队）

**Playwright** — 确定性 Browser Execution + Testing + Evidence 基础设施
- 承担：页面打开/等待/元素定位/点击/输入/上传/下载/截图/DOM & Accessibility State/Trace/Test/Replay
- 原则：能用确定性代码完成的动作，不让 LLM 每一步重新思考。

**PinchTab（第一梯队候选）** — Browser Control Plane
- 研究：Browser Instance / Profile / Session / HTTP API / CLI / 多实例 / 长生命周期 Browser / Accessibility Snapshot / 本地运行 / Remote Browser
- 不得让 ZBC 直接依赖 PinchTab API，必须通过：Zachary → Browser Contract → PinchTab Adapter

---

## 八、第二梯队

**Browser Use** — Agent Browser Capability（重点学习：Agent Loop / Planning / Replanning / Failure Recovery / Loop Detection / Structured Output / Fallback Model / Judge / Step Limit / Browser State）
- 原则：吸收设计思想，不绑定核心架构。

**Browser Harness** — Research / CDP / Adaptive Browser
- 重点：CDP / Existing Browser / Browser Attachment / Runtime Workspace / Domain Skill / Helper / Research Agent
- 不能直接获得无限生产权限。

---

## 九、实验层

**CloakBrowser** — 定位正式改为：Optional Browser Compatibility / Fingerprint Runtime Provider
- 禁止定义为：风控破解器。
- 可研究：Chromium-level compatibility / Browser fingerprint consistency / Profile / Locale / Timezone / GPU / WebGL consistency / Browser automation compatibility
- 必须进行：License Audit / Version Audit / Compatibility Test / Security Audit / Runtime Benchmark。未经测试不进入生产依赖。

---

## 十、Adaptive Decode & Compatibility

保留"自适应破解/解码"核心诉求，但产品正式术语统一为：**Adaptive Decode & Compatibility Engine（自适应解析与兼容引擎）**

能力包括：编码识别/编码转换/文件格式识别/数据格式解析/HTML 解析/JSON/XML/CSV 等结构解析/图片视频字幕等合法数据解析/用户拥有权限的数据解码/页面结构变化适配/DOM 变化适配/Accessibility Tree 变化适配/Browser Provider 自适应选择/Parser 自适应选择/失败后的重新观察/重新规划/结果验证。

---

## 十一、Adaptive Execution Policy

任何自适应行为必须经过：

```
Unknown → Detect → Classify → Policy Check → Permission Check → Safe?
  ├── YES → Adapt → Execute → Verify
  └── NO  → Safe Stop → Evidence
```

---

## 十二、安全边界

允许：用户自己的文件、用户明确授权的数据、公开网页、合法 API、合法公开数据、编码解码、格式转换、页面结构适配、浏览器兼容性调整、用户授权环境中的自动化测试、合法的数据解析。

禁止自动执行：第三方账号破解、密码破解、窃取 Cookie、窃取 Session、绕过身份认证、绕过 CAPTCHA、绕过 DRM、绕过付费权限、绕过明确访问控制、绕过平台安全限制、无限重试安全机制、针对平台风控持续规避。

遇到上述情况：**Safe Stop + Evidence + Human Review**。

---

## 十三、Browser Execution Protocol（BEEP）

正式建立 **BEEP（Browser Execution & Evidence Protocol）**：

```
PRECONDITION → OBSERVE → PLAN → ACTION → POST-CONDITION → EVIDENCE → DECISION → NEXT
```

---

## 十四、打开网页标准

禁止：打开网址。必须：
1. 检查 Browser 状态
2. 打开目标页面
3. 等待页面状态稳定
4. 读取 URL / Title / Page State
5. 确认是否进入预期页面
6. 成功后才执行下一步
7. 记录 Evidence

---

## 十五、点击标准

```
Locate → Confirm → Click → Observe → Verify → Evidence
```
禁止：点击后直接假定成功。

---

## 十六、输入标准

```
Locate Field → Validate → Input → Read Back → Verify → Evidence
```
必须确认：实际输入值是否进入正确字段。

---

## 十七、Browser State Machine

```
INIT → BROWSER_READY → PAGE_READY → SESSION_VALID → TASK_READY → ACTION → VERIFY → SUCCESS
```

异常状态：`VERIFY_FAILED → CLASSIFY_FAILURE`，分类：transient / session / page_changed / permission / platform_risk / unknown。

---

## 十八、Failure Recovery

- transient → 有限次数 Retry
- page_changed → Re-observe
- session → Re-auth / Stop
- platform_risk → Cooldown / Stop / Human Review
- unknown → Evidence + Safe Stop
- **禁止：无限重试。**

---

## 十九、Browser Health

必须区分：Browser Alive 和 Task Successful。至少记录：browser_status / session_status / page_status / task_status / last_action_at / last_success_at / last_failure_at / failure_reason / retry_count / provider / runtime。

---

## 二十、Evidence

Zachary 不允许只说"成功了"。必须能够形成：URL / Timestamp / Browser / Profile / Session / Action / Before State / After State / Screenshot / Snapshot / Result / Provider / Error / Retry Count。

原则：AI 声称成功 ≠ 系统成功。必须：Verification → Evidence → Success。

---

## 二十一、Browser Skill Registry

建立统一 Skill Registry。例如：XHS_SEARCH / XHS_OPEN_NOTE / XHS_EXTRACT_NOTE / XHS_PARSE_AUTHOR / XHS_PARSE_ENGAGEMENT / XHS_CHECK_SESSION / XHS_CHECK_PLATFORM_STATE。

**Skill ≠ Business Rule**。Skill 只代表如何执行一个动作。不能把小红书业务规则硬编码到通用 Zachary Browser Runtime。

---

## 二十二、Skill 晋级制度

```
Task Success → Skill Candidate → Sandbox → Test → Evaluation → Evidence → Review → Registry → Production
```
禁止：一次成功 → 自动永久写入生产 Skill。

---

## 二十三、Provider Router

Browser Task → Policy → Router → Provider Selection。根据：Task Type / Reliability / Cost / Speed / Browser Compatibility / Platform / Session / Risk / Evidence Requirement 自动选择。

---

## 二十四、Model Runtime 与 Browser Runtime 双解耦

```
                     ZACHARY
                        │
             ┌──────────┴──────────┐
             ↓                     ↓
       Model Runtime         Browser Runtime
             ↓                     ↓
       Model Router           Browser Router
             ↓                     ↓
      Local / Cloud         Playwright
      Future Models         PinchTab
                            Harness
                            Future
```
任何一个 Model 或 Browser Provider 可以替换；Zachary 不应该被替换 Provider 绑死。

---

## 二十五、ZBC 的职责边界

ZBC：专业产品生产系统。负责品牌传播/舆情监测/内容生产/数据采集/行业逻辑/品牌逻辑/客户逻辑/报告/专业业务规则。

Zachary：通用 AI 能力层。负责理解/推理/学习/工具调用/Browser/Resource/Skill/Evaluation/Learning。

禁止 ZBC 把产品专属业务规则写进 Zachary 通用核心。

---

## 二十六、资源库统一原则

学习资料、案例、文件、外部资料统一进入 **Resource Library / 资源库体系**。不再人为拆成学习库/案例库/资料库三个独立系统。可用 Category / Type / Tag / Source / Domain / Product Scope 分类，但底层资源体系统一。

---

## 二十七、Zachary Resource Access

User/Product → Zachary → Resource Query → Policy → Context → Resource → Learning/Production。
ZBC 可通过 Zachary 获取资源、案例、方法、知识和工具能力，但必须遵守 Context Isolation。

---

## 二十八、用户行为与个性化

未来加入 User Behavior Learning，目标实现"千人千篇"。

可以改变：表达风格/推荐偏好/信息密度/交互习惯/操作路径/内容呈现方式。
不可以改变：物理性质/核心业务规则/安全边界/权限边界/数据真实性/系统事实/产品架构。

即：**个性化改变 Style，不改变 Truth。**

---

## 二十九、学习闭环

Resource → Zachary → Production → User → Behavior → Evaluation → Learning Signal → Zachary。
必须加入：Validation / Policy / Context Isolation / Data Governance，防止错误经验进入核心能力。

---

## 三十、Zachary 成熟路线

- Stage 1：内部 AI（学习 + 辅助研发 + 产品生产）
- Stage 2：拥有 Model Runtime / Browser Runtime / Resource / Skill / Evidence / Evaluation
- Stage 3：独立执行任务/独立调用工具/独立选择 Provider/独立验证结果/独立处理失败
- Stage 4：形成独立 Zachary AI Runtime
- Stage 5：再考虑 Zachary 独立产品化

---

## 三十一、App Gate

现在禁止提前进入 App 开发。必须满足：Model Independence + Browser Independence + Resource System + Context Isolation + Evidence + Evaluation + Stable ZBC Runtime + Release Gate，全部通过后：

Zachary Runtime → Unified API / Contract → Web / PC / iOS / Android。
App 只是 Client Layer，不重新复制核心 AI 和业务逻辑。

---

## 三十二、第一梯队施工矩阵（P0-BR）

| ID | 项 |
|---|---|
| P0-BR-01 | Browser Contract |
| P0-BR-02 | Browser State Machine |
| P0-BR-03 | BEEP Execution Protocol |
| P0-BR-04 | Browser Policy Engine |
| P0-BR-05 | Permission Scope |
| P0-BR-06 | Session/Profile Isolation |
| P0-BR-07 | Failure Classification |
| P0-BR-08 | Safe Stop |
| P0-BR-09 | Evidence |
| P0-BR-10 | Playwright Adapter |
| P0-BR-11 | Browser Health |
| P0-BR-12 | ZBC Browser Decoupling |

---

## 三十三、第二梯队（P1-BR）

| ID | 项 |
|---|---|
| P1-BR-13 | PinchTab Adapter |
| P1-BR-14 | Browser Use Adapter |
| P1-BR-15 | Browser Harness Adapter |
| P1-BR-16 | Skill Registry |
| P1-BR-17 | Skill Sandbox |
| P1-BR-18 | Browser Replay |
| P1-BR-19 | Adaptive Decode & Compatibility |
| P1-BR-20 | CloakBrowser Compatibility Lab |
| P1-BR-21 | Provider Benchmark |
| P1-BR-22 | Browser Cost / Token Router |

---

## 三十四、研发原则

1. 先审计现有代码。
2. 禁止为了新功能破坏旧功能。
3. 禁止大规模重构，除非 Evidence 证明必要。
4. 新增能力必须通过 Contract。
5. Provider 必须可替换。
6. 业务规则和通用能力必须隔离。
7. AI 输出不能直接成为 System Truth。
8. 所有关键执行必须可以验证。
9. 失败必须可记录。
10. 异常必须可以 Safe Stop。
11. 所有新增功能必须有测试。
12. 所有关键修改必须有 Evidence。

---

## 三十五、双子库审计要求

**Zachary-OS-AI** 审计：Runtime / Model Provider / Browser Provider / Tool System / Context / Resource / Memory / Skill / Evaluation / Evidence / Security / Dependency。

**Z-Brand-Core** 审计：Zachary 接口 / Browser 调用 / AI 调用 / Resource 调用 / 数据流 / Context / API / Collector / Runtime / Monitoring / Guardian / CI / Tests。

---

## 三十六、双子库关系

```
Zachary-OS-AI
       │ Contract
       ↓
Z-Brand-Core
```
禁止：Zachary ↔ ZBC 互相直接读取内部代码。必须通过 Contract / API / Adapter / Evidence 交互。

---

## 三十七、施工前必须建立事实基线

下一轮 AI 编程开始前，必须输出：Current HEAD / Branch / Version / Runtime / Dependencies / Tests / CI / Working Tree / Existing Architecture / Existing APIs / Existing Contracts / Existing Evidence，并形成 Baseline Snapshot。未经确认不直接修改核心代码。

---

## 三十八、代码施工顺序

Repository Audit → Architecture Audit → Dependency Audit → Contract Audit → Runtime Audit → Test Baseline → Minimal Implementation → Unit Test → Integration Test → E2E → Evidence → Regression → Cross-Repo Audit → Release Gate。

---

## 三十九、绝对禁止

- 为了"看起来先进"引入不必要依赖。
- 复制第三方项目核心代码而不进行 License 审计。
- 将第三方项目直接变成 Zachary 核心。
- AI 自己修改产品 Truth。
- Provider 与业务逻辑耦合。
- Browser 无限重试。
- 失败后假装成功。
- 未验证直接进入生产。
- 为了新功能破坏现有 ZBC。
- 在 App 阶段之前提前固化客户端架构。

---

## 四十、最终架构目标

```
                         ZACHARY
                    General AI Runtime
                            │
       ┌────────────┬───────┼────────┬──────────┐
       ↓            ↓       ↓        ↓          ↓
     Model        Browser Resource  Skill    Evaluation
    Runtime       Runtime  Runtime  Runtime    Runtime
       │            │       │        │          │
       ↓            ↓       ↓        ↓          ↓
    Providers    Providers  Library  Registry   Evidence
       │            │
       ↓            ↓
 Local/Cloud    Playwright
 Future         PinchTab / Harness / Future
                            │
                            ↓
                         Context → Policy → ZBC → Real Production → Feedback → Evaluation → Learning Signal → Zachary
```

---

## 四十一、最终一句话定义（必须写入双子库）

**Zachary 是通用 AI Runtime；ZBC 是专业产品 Runtime。Zachary 可以通过统一 Contract 为 ZBC 提供通用智能、资源、浏览器、工具、学习与执行能力；ZBC 可以通过经过治理的生产数据、用户反馈、Evaluation 和 Evidence 反哺 Zachary，但任何产品的业务 Truth、架构、权限和专属数据都不得无边界进入 Zachary。**

**Zachary 的 Browser 能力必须独立于任何单一第三方浏览器框架，并采用 Contract + Router + State Machine + Policy + Evidence 架构。**

**Adaptive Decode & Compatibility 可以作为 Zachary 的通用自适应能力，但必须在授权、合法、安全和 Policy Gate 范围内执行；无法安全处理的任务必须 Safe Stop，而不是无限尝试绕过安全控制。**

---

## 四十二、当前执行状态

现在只执行：将本文件作为研发基线/架构事实写入双子库。

现在不要执行：大规模代码重构 / Browser Runtime 正式开发 / App 开发 / 第三方依赖正式接入 / 替换现有 Collector / 替换现有 AI Provider / 修改 ZBC 核心业务逻辑。

写入完成后：停止施工，等待下一轮「Zachary × ZBC AI 编程基线」指令，届时才进入源码级审计 → 现状映射 → 差距矩阵 → 最小改造 → 编码 → 测试 → Evidence → 双库交叉验证 → Release Gate。

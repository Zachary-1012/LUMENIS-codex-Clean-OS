# 序境 LUMENIS — 全产品文字草图汇总（草稿 2026-10-14，待 PO 审核）

> 44 屏现有规格按屏汇总 + 全部新增能力草图（原文附后）。屏位已按屏幕索引校正。全部闭环内；上线后仅真实用户验证与付费/授权来源。前端建设顺序见 FRONTEND-BUILD-PLAN.md；剪辑与播客工程能力见 product-plan-full.md §14。

## A. 44 屏总表

| 屏 | 名称 | 任务（摘自规格 §1） | 新增草图 | 前端步骤 |
|---|---|---|---|---|
| ACC-01 | Workspace entry and account boundary | - User job: confirm that the internal-beta workspace entry is available and continue through the host-provided route. - Read route: `GET /api/experience/runtime | account-settings、sign-in | F1/F2 |
| ACC-02 | Subject and view-lens selection | - Read current view: `GET /api/settings/context` via `settingsContext()`. - Read CTH directory: `GET /api/settings/subjects?domain_id=CTH` via `settingsSubjects | — | F3 |
| ACC-03 | Product home | Open the product and begin real work: write or open a task draft, continue an actually visited page, or open an existing business/creation workflow. This is an  | — | F1 |
| ACC-04 | Guard and recovery | - Read route: `GET /api/experience/screen/ACC-04` via `CoreAcc04Repository`. - Current runtime reports this target as unbound; the page must show unavailable ra | — | F1 |
| AI-01 | AI intent entry | - Role and scope: no selected Subject or BrandFocus means GLOBAL_ALL. FOCUS is optional and only narrows the existing scope. Opening the product, reading global | intelligent-cards、tool-permission-confirm | F4 |
| AI-02 | Governed task stages and artifacts | - Read route: `GET /api/experience/screen/AI-02` via `LumenisCoreClient.screen('AI-02')`. - Current response contract: `ok`, `screen`, `source`, `bound`, `bindi | — | F4 |
| AI-03 | Source-first analysis thread | - Read route: `GET /api/experience/screen/AI-03` via `CoreAi03Repository`. - Current response can expose `thread` / `messages`, `binding`, `generated_at`, `sour | — | F4 |
| AI-04 | Registered Product Skill Store | - Read route: `GET /api/experience/shared-skills` via `LumenisCoreClient.sharedSkillsCatalog()`. - A row is shown only when: `ok=true`; safe `skill_id`, semver  | github-mcp-connectors、skills-store | F5 |
| AI-05 | AI service topology diagnostic | - Primary read: `GET /api/experience/screen/AI-05`. - Explicit fallback only when the primary response is valid `AI-05` with `bound=false`: `GET /api/experience | byo-api | F5 |
| BMP-01 | 品牌市场总览 | - Role and authorized context: A brand or market operator working in BMP. A trusted actor and an authorized BrandFocus are required before showing brand-level t | — | F8 |
| BMP-02 | 品牌组合与竞品谱系 | - **Role / context:** A BMP operator compares one authorized BrandFocus with its owned brands, sub-brands and competitor entities. - **User task / completion:** | — | F8 |
| BMP-03 | 市场情报与机会雷达 | - **Role / context:** A BMP operator needs to identify market opportunities for one authorized BrandFocus and understand why each opportunity is present. - **Us | — | F8 |
| BMP-04 | 品牌传播路径 | - **Role / context:** A BMP operator traces how a selected BrandFocus moves through channels toward response or conversion. - **User task / completion:** compar | — | F8 |
| BMP-05 | 创作者生态 | - **Role / context:** A BMP operator evaluates creators relevant to one authorized BrandFocus across KOS, KOL, KOC and UGC tiers. - **User task / completion:**  | kos-funnel | F8 |
| BMP-06 | 内容生产台 | - A brand operator needs to move an approved content idea through drafting, review and authorized release while retaining version and source context. - BMP owns | video-editing-studio | F8 |
| BMP-07 | 活动工作台 | - A brand operator needs to connect an activity objective to audience, channel milestones and observed outcomes without confusing a plan with a result. - BMP ow | marketing-calendar | F8 |
| BMP-08 | 播客制作室 | - A brand operator needs to turn approved source material into a reviewable spoken episode while keeping script, source, audio version, publication and rights d | podcast-studio | F8 |
| BMP-09 | 品牌评估 | - A brand operator needs to understand movement by evaluation dimension, confidence and source coverage using actual observed results. - Evaluation is derivativ | public-mmm | F8 |
| BMP-10 | 品牌风险响应 | - A brand operator needs to see which brand-risk incidents need attention, how severity/spread/recency affect triage, and what response step is next. - BMP Bran | — | F8 |
| BMP-11 | 品牌基准 | - A brand operator needs normalized comparisons with metric definitions visible beside values, while incomparable items remain explicitly withheld. - The curren | — | F8 |
| CTH-01 | Commercial Operations Overview | - **Role / authorized context:** CTH commercial operator. The screen reads only the Product Core's current Subject context from `GET /api/experience/runtime/ide | — | F7 |
| CTH-02 | 经营主体与关联信息 | - **Role / authorized context:** CTH operator. The CTH Subject Registry returns rows only after an authenticated account and `subject_registry` / `read` permiss | — | F7 |
| CTH-03 | 实时监测 | - **User task:** a CTH operator needs to see what has recently changed, which returned source lanes are available, and inspect one returned signal without losin | — | F7 |
| CTH-04 | 事件关系 | - **User task:** understand the order of returned CTH events and inspect one event without mistaking chronology for causality. - **Context:** use the same `sett | — | F7 |
| CTH-05 | 舆情日历 | - **User task:** find days with returned sentiment or event density, inspect one selected day, and switch to a precise list for keyboard use. - **Context:** `GL | — | F7 |
| CTH-06 | 负面监测与反馈 | - **User task:** triage returned negative feedback, understand whether it is public opinion, customer feedback, a confirmed incident or not yet classified, and  | — | F7 |
| CTH-07 | 趋势分析 | - **User task:** understand how a returned CTH metric changed over one stated window, what its numerator/denominator mean, and which returned series is selected | — | F7 |
| CTH-08 | 案例工作台与可复用知识 | - **Role / context:** CTH operator in either `GLOBAL / ALL` or an authorized CTH Subject focus. Selection changes working context only; it never grants access o | — | F7 |
| CTH-09 | 风险与决策工作台 | - **Role / context:** CTH operator working in `GLOBAL / ALL` or an authorized focused CTH Subject. - **User task:** inspect the basis of a risk, review a separa | math-result-card | F7 |
| CTH-10 | 报告与运营简报工作台 | - **Role / context:** CTH operator in `GLOBAL / ALL` or an authorized focused CTH Subject. - **User task:** choose a verified period, inspect a report/brief as  | — | F7 |
| SH-01 | Shared Capability Catalog | SH-01 is the existing Shared entry for independently usable research and creation capabilities, also consumed by CTH and BMP. It is not a third product, and cat | video-editing-studio、podcast-studio（同编辑器，无前置入口） | F9（剪辑/播客入口同 F8） |
| SH-02 | Evidence Library | SH-02 is a read-only material library for provenance-bearing items used by Shared Capability workflows. Its space and list are alternate ways to browse the same | — | F9 |
| SH-03 | Canonical Data and Metric Explorer | SH-03 is a read-only explorer for verified Canonical data metrics. It explains a metric’s business definition, state, cadence, lineage and sampled values; it do | — | F9 |
| SH-04 | Reopenable Report Export Center | SH-04 is an output queue and artifact inspector. It does not create a fake export, download a path that was never persisted, or treat a report listing as proof  | — | F9 |
| SH-05 | Versioned Learning and Evaluation Assets | SH-05 presents versioned learning assets and their evaluation/promotion history. An asset is derivative input, not Canonical Truth, Permission truth or Evidence | — | F9 |
| SH-06 | Notification and Task Center | SH-06 is a read-only operational inbox with distinct lanes for tasks, notifications and alerts. It reports the state of verified work items; it does not create  | — | F9 |
| SYS-01 | Runtime health / RuntimeGuardian slice | - Role and authorized context: SYSTEM operator, after the App's current authentication boundary permits the GET request. This page reports infrastructure state  | — | F10 |
| SYS-02 | Collector status | - Authorized context: SYSTEM operator permitted to read the current screen envelope. - Real task: determine which collection lanes are verified, partial, missin | manual-collect | F6 |
| SYS-03 | Database and truth chain | - Authorized context: SYSTEM reader with permitted access to a read-only system screen. - Real task: understand which schema/check/chain facts are returned and  | — | F10 |
| SYS-04 | Security and permission | - Authorized context: operator permitted to inspect a safe security posture. - Real task: understand the visible permission level and whether an audit decision  | keys-compliance、user-developer-mode | F10/F11 |
| SYS-05 | Device appearance | The user changes how the current LUMENIS workspace is presented, then returns to the same work with the same route, scroll position, selection, and unsaved draf | visual-brand-roles | F0/F12 |
| SYS-06 | Internal browser capability | - Authorized context: SYSTEM operator allowed to read a filtered capability report. - Real task: know whether controlled browser capacity is available and what  | browser-tabs、login-recovery-sheet | F6 |
| SYS-07 | Evaluation and acceptance | - Authorized context: SYSTEM/security operator reading returned evaluation checks. - Real task: see which checks actually returned and whether evidence-backed p | founder-developer-mode | F10/F11 |
| SYS-08 | Observability and logs | - Authorized context: SYSTEM operator permitted to read a sanitized observability summary. - Real task: understand whether logs/trace records are available with | ops-workspace-lifecycle | F10 |

## B. 新增能力草图全文

---

### ACC-01 — 草图增补：账号设置 rev3（类 ChatGPT）

> 草稿，待 PO 审核。依据：G18、G19、G20、AI-05。闭环内。

## 5. Desktop
```
设置                                                      [×]
┌────────────┬────────────────────────────────────────────┐
│ 通用       │ 主题 · 语言 · 时区 · 通知 · 减少动态效果    │
│ 账号       │ 头像 显示名 邮箱[更改]                      │
│            │ 登录方式：邮箱✓ Apple[关联] Google[关联]    │
│            │  （至少保留一种）                           │
│ 安全       │ 设备与会话：设备/位置/最近活动 [退出]       │
│            │  当前会话标「当前」                         │
│            │  [退出所有设备]（含本机，二次确认）         │
│            │  新设备登录邮件提醒 ✓                       │
│ 模型与API  │ (●) 自有模型 ( ) 我的 API → AI-05           │
│ 连接器     │ GitHub / MCP → AI-04 · 平台登录 → SYS-06    │
│ 用量       │ 模型调用 · 采集任务 · 存储；未统计=数据缺失 │
│ 数据控制   │ 改进模型 [允许/不允许]（首次使用时你选的）  │
│            │ [导出全部数据] 完成后通知，链接限时有效     │
│            │ [备份账号数据] [从备份恢复]                 │
│            │ [删除全部对话]                              │
│            │ [删除账号] 输入邮箱确认 → 30 天内可撤销     │
│ 开发者     │ 用户开发者模式 → SYS-04（需先接受协议）     │
│ 关于       │ 版本 · 条款 · 隐私    [退出登录]            │
└────────────┴────────────────────────────────────────────┘
未登录：账号/安全显示「未登录 · [登录或注册]」；其余分区照常可用（本地导出/备份）。
```
## 5A. Web：同桌面，会话含浏览器会话。
## 6. Mobile：一级列表 → 二级页；删除账号在数据控制底部（红色）。
## 4. States
正常 / 加载 / 数据缺失（不补 0/50）/ 账号服务不可用（账号、安全只读并说明原因，其他正常，无自动回退）/ 导出或备份中（进度，可取消）/ 删除待生效（剩余 N 天 + [撤销删除]）/ 会话状态未知（显示「状态未知」，可用退出所有设备）。
## 9. Acceptance
- 三种方式可互相关联/解除，最后一种不可解除。
- 删除：30 天内重新登录或点撤销即恢复；满 30 天彻底清除（写入 G19 合规）。
- 导出含资料、主体、采集数据、报告、对话；同账号限时下载。
- 自带 API Key 仅本机安全存储；三语；无主体写死。

---

### ACC-01 — 草图增补：登录/注册（邮箱 · Apple · Google）rev3

> 草稿，待 PO 审核。依据：G18（闭环内，PO 2026-10-14）。不做通行密钥、不做二次验证。

## 5. Desktop
```
┌──────────────── 序境 LUMENIS ────────────────┐
│             登录或创建账号                    │
│  [ Apple 登录 ]   [ Google 登录 ]             │
│  ─────────── 或 ───────────                  │
│  邮箱 [ name@example.com ]  [继续]            │
│   → 6 位验证码（无密码）                      │
│  [ 先不登录，直接使用 ] ← 始终可见            │
│  条款 · 隐私 · 中文 / English / 한국어        │
└───────────────────────────────────────────────┘
验证码页：xx@xx [□□□□□□] [重新发送 59s] [换个邮箱]
首次进入（登录或不登录都问一次）：
┌ 是否允许用你的使用数据改进序境模型？ ┐
│ [允许]  [不允许]   之后可在 设置›数据控制 修改 │
└──────────────────────────────────────┘（无预选项）
```
## 4B. Apple 按钮启用条件：取得 Apple Developer 账号（$99/年）前不显示 Apple 按钮，仅显示 Google 与邮箱验证码；两者均为免费方式。启用后布局如上图。
## 5A. Web：同桌面；Apple/Google 授权后回原页，工作不丢。
## 6. Mobile：Logo → Apple（iOS 置顶）→ Google → 邮箱 → 继续 → 底部「先不登录」。
## 4. States
正常 / 加载（可取消）/ 验证码错或过期（行内提示+重发）/ 第三方取消授权（回本页不弹错）/ 登录服务不可用（「登录暂不可用，可先不登录继续使用」，不自动换方式）/ 同邮箱已有账号（归同一账号，询问是否关联新方式）/ Apple 隐藏邮箱（提示继续用 Apple 或在设置关联真实邮箱）/ 删除待生效账号登录（「账号将于 N 天后删除」[恢复账号] [继续删除]）。
## 9. Acceptance
- 不登录全部主流程可用；本地数据登录后由用户选「合并 / 保持本地」。
- 同邮箱不同方式 = 同一账号；新设备登录发邮件提醒。
- 改进模型询问无预选，未回答前按「不允许」处理且再次询问。
- 三语；无主体写死；不存明文密码。

---

### AI-01 — 草图增补：聊天智能 UI 卡片

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G14,G116。

## 5. Purpose-built desktop composition
```
用户：…
序境：[决策卡：选项A/B 依据▸ 证据▸ (采纳)(修改)]
      [表格卡] [表单卡] [图表卡] [证据卡 来源↗]
顶部切换：(卡片模式)(简洁模式)
```

## 5A. Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition
卡片全宽堆叠。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 用户可选简洁模式。

---

### AI-01 — 草图增补：免命令行工具调用与高风险确认

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G115。

## 5. Purpose-built desktop composition
```
┌ 序境要在内置浏览器执行：提交表单 <站点> ┐
│ 权限范围：本任务  风险：高               │
│ [允许一次] [本任务内允许] [拒绝]          │
└──────────────────────────────────────────┘ 执行后留证据卡
```

## 5A. Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition
底部 Sheet。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 只用注册工具；评论/私信只生成草稿不自动发。

---

### AI-04 — 草图增补：连接器：GitHub（只读、仓库白名单）与 MCP（审查→白名单→人工批准）

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G95,G96。

## 5. Purpose-built desktop composition
```
连接器列表：GitHub [连接] 状态 | 仓库白名单 [+]
MCP 服务器：名称 | 审查结果 | [批准接入] [拒绝]
Token：仅会话内，不落盘
```

## 5A. Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition
同内容。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 不依赖账号体系。

---

### AI-04 — 草图增补：Skills 商店

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G21,G94,G130。

## 5. Purpose-built desktop composition
```
[搜索 Skill…] 分类 ▾
卡片：名称 | 输入 | 验证状态 | 权限 | [安装] [启用] [更新/回滚] [卸载]
详情：未知项列表、版本历史
```

## 5A. Web Workspace composition
同桌面布局；受限后台插件不在商店上架。

## 6. Purpose-built mobile composition
列表 + 详情页。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 升级：从只读目录补齐完整生命周期。

---

### AI-05 — 草图增补：模型设置：自有模型默认 + 一个通用 OpenAI 兼容自带 API

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G50。

## 5. Purpose-built desktop composition
```
模型来源 (●) 序境自有模型（默认）  ( ) 我的 API（OpenAI 兼容）
  Base URL [        ] Model [      ] Key [••••] [测试连接]
说明：不可用时显示「不可用」，不会自动切换
```

## 5A. Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition
同内容纵排。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 无豆包/智谱/Ollama 选项；无自动回退；Key 不落盘明文。

---

### BMP-05 — 草图增补：KOS 三阶漏斗与合规留资

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G118,G119。

## 5. Purpose-built desktop composition
```
曝光 → 互动 → 留资  （每阶：值｜区间｜缺失标注）
CPL / 成本：—（缺失）或数值
[生成评论回复草稿]（不自动发送）
```

## 5A. Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition
纵排。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 

---

### BMP-06 — 草图增补：内容生产台 · 视频剪辑（规划 §14 E1–E11、G105/G64/G170/G171）

> 草稿，待 PO 审核。闭环内。同一编辑器从 SH-01（Shared，无前置）或 BMP-06（品牌内容）进入。自有模型默认，BYO 可选，不可用不切换，手动剪辑始终可用。

## 5. Desktop
```
内容生产台 › 视频 · 《标题》                  画幅 [9:16 ▾ 16:9 1:1 4:5] [导出] [工程交换 ▾]
Brief ✓  分镜 6 镜  审核：READY / NEEDS_REVISION / BLOCKED / NOT_VERIFIED
┌ 素材浏览（独立预览，不动播放头）┬ 预览（安全区线）────────┬ 检查器 ───────────┐
│ clip01 0:42 SHA✓ 30fps 版权未知 │   ┌────────┐            │ 字幕 样式/每行≤14字 │
│ clip02 1:10 VFR⚠                │   │ 字幕区 │            │ 响度 实测/目标      │
│ [自动粗剪提议] [镜头检测]       │   └────────┘            │ B-roll 候选(已授权) │
├ 逐词稿（删词即剪）──────────────┴──────────────────────────┤ 封面 3 候选          │
│ 今天带你看……~~呃~~……这家店的木门是……                         │ AI 标注 含 AI 内容   │
├ 时间线：V1 ▇▇▇|▇▇ ｜ 字幕 ▭▭▭ ｜ 人声 ▅▅ ｜ BGM ▁▁(ducking) ▶ 00:00:18 ───────┤
└──────────────────────────────────────────────────────────────────────────────┘
工程交换预检：⚠ 2 项损失（ducking 无对应、dissolve 不支持）· 时基 UNKNOWN → [查看] [仍导出为新版本] [取消]
```
## 5A. Web：同桌面；大文件上传分片续传。
## 6. Mobile：竖屏优先；逐词稿编辑 + 简化时间线；画幅切换与导出可用；工程交换仅桌面。
## 4. States
空 / 探测中 / 转写中 / 模型不可用（手动剪辑可用）/ 提议待确认 / 渲染中（可取消）/ 渲染失败（原因+重试）/ 版权未知 / 数据缺失 / 权限不足。
## 9. Acceptance
- 素材 100% 有哈希/时长/时基；VFR 标注；序列化无绝对路径。
- 字幕同步 ≤100ms；多画幅不拉伸、字幕在安全区；16:9 与 9:16 分别重排。
- 自动粗剪只是提议，确认后才改 Timeline；词内零切。
- 成片可播放、可重开；工程交换先预检，取消不改项目。
- 产品演示片必须来自真实操作录屏；封面文案兑现正文；AI 素材标注。


## 增补（2026-10-14）
- 预览与播放头分离：悬停临时预览不改时间线、不进撤销栈；切点以播放头为准并在界面标明。
- 参考片学习面板（E12）：全帧数 / 已看帧数 / 峰值时码列表 / 镜头表；未看完显示「部分」。
- 演示片模式（E10）：镜头表每行写「操作→状态→结果」；短版按动作闭环自动建议切点。
- 导出前预检条：逐项损失列表，取消即不改项目。

---

### BMP-07 — 草图增补：营销日历与热点建议

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G120。

## 5. Purpose-built desktop composition
```
月视图：日期格内 节点/热点徽标
右侧：热点建议（依据▸ 置信区间）[加入计划] [忽略]
```

## 5A. Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition
周列表。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 建议可忽略，用户决定。

---

### BMP-08 — 草图增补：播客制作室全链（规划 §14 P1–P12、G106/G79/G107/G128）

> 草稿，待 PO 审核。闭环内。自有模型默认，BYO API 仅用户选择；模型不可用 → 该步显示「不可用」，导入稿/手动剪辑/手动混音照常。Shared 无前置也可从 SH-01 进入同一制作室。

## 5. Desktop
```
播客制作室 · 《节目名》第 N 期                     [保存] [版本 v3 ▾] [导出发布包]
步骤条：①选题 ②嘉宾 ③提纲 ④脚本 ⑤录音/导入 ⑥转写 ⑦剪辑 ⑧配音(可选) ⑨母带 ⑩发布包 ⑪切片 ⑫复盘
┌ 左：稿件（逐词，可编辑）──────────────┬ 右：检查器 ─────────────────┐
│ [S1 主持] 00:00:12 今天我们聊……         │ 章节：01 开场 00:00 [改名]   │
│ [S2 嘉宾] 00:00:31 我第一次……  ~~嗯~~   │       02 …                    │
│  删词=剪掉对应音频；划线=待删语气词      │ 说话人：S1 主持 S2 嘉宾 [合并]│
│ [一键去语气词/长停顿 → 生成提议]         │ 来源：脚本事实句 12/12 有来源 │
├ 下：多轨时间线 ─────────────────────────┤ 响度：实测 -16.2 LUFS ✓       │
│ 人声1 ▁▃▅▇▅▃  人声2 ▂▄▆▄▂  BGM ▁▁▁(ducking)│ 真峰：-1.3 dBTP ✓             │
│ ▶ 播放头 00:12:31   [试听] [循环]         │ AI 标注：脚本「AI 生成」·配音「AI 配音」│
└─────────────────────────────────────────┴──────────────────────────────┘
⑩ 发布包：MP3/M4A · show notes · 章节 JSON · 字幕稿 VTT/SRT · 封面 · RSS 校验 ✓  [确认发布]（不自动发）
⑪ 切片：故事节点候选（时间码+来源）→ 9:16 音频图 / 引语卡 / 各平台包装
⑫ 复盘：故事节点密度 · 情绪/洞察峰值（AI 派生，非权威）· 产出率 · 留存曲线（无平台数据 = 数据缺失）
```
## 5A. Web：同桌面；录音需浏览器麦克风授权，未授权时只可导入。
## 6. Mobile：步骤条横滑；稿件全屏编辑；时间线折叠为波形条；母带与发布包只读确认。
## 4. States
空 / 导入中 / 转写中（进度，可取消）/ 模型不可用（显示原因，可导入已有字幕稿继续）/ 剪辑提议待确认 / 母带不达标（显示实测值与差值，不自动二次施压）/ 版权未知（导出提醒）/ 数据缺失 / 权限不足。
## 9. Acceptance
- 删词剪点误差 ≤1 帧；词内零切；撤销还原原稿与音频。
- 母带实测 -16 LUFS ±1、真峰 ≤ -1 dBTP，数值显示在界面。
- 脚本事实句 100% 有来源或标 UNKNOWN；配音仅用户开启，声音克隆需本人授权。
- 发布包 RSS 含 podcast:transcript / podcast:chapters 并通过校验；发布需确认。
- 新建→编辑→试听→导出→重开修订完整可走通（G55）；三语；无主体写死。


## 增补（2026-10-14 全文读码）
- 播放器全工作区唯一；点逐字稿句子→跳播；点时间轴标记→打开对应故事节点/证据；点故事节点→筛选稿与素材。
- 手机：迷你播放器 + 底部抽屉；桌面：两栏/三栏。
- 选题卡：十信号逐项显示；缺项显示「需补输入」并列出缺哪几项，不出分。
- 嘉宾卡：三标准 Gate 勾选（人工），未过不进入提纲。
- 稿件：原文/校对双视图切换；改稿提示「改稿不改音频」。
- 状态：加载/空/部分/错误/重试/恢复中/成功 均有设计；运行不回传显示「无返回」，不静默。
- 研究阅读器：结论→发现→证据（侧抽屉）→模式与假设→验证状态→可迁移→不可照搬→来源。

---

### BMP-09 — 草图增补：公开数据营销组合与归因

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G166-G169。

## 5. Purpose-built desktop composition
```
主体：<任一已登记主体>  数据来源：年报/中报▸ 统计局▸ 刊例价▸ 采集▸
花费估算：区间 ¥a–b（出处逐项）
渠道贡献：条形+区间；样本不足 → 数据不足
[可选：导入我的数据]
```

## 5A. Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition
纵排。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 数据同权、按用途、重构；不使用付费源。

---

### CTH-09 — 草图增补：数学引擎结果卡（区间/缺失）

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G143-G169。

## 5. Purpose-built desktop composition
```
指标：风险指数 62（95% 区间 54–70）模型 v1.2 · 证据▸
样本不足：「数据不足（n=3 < 14）」—不显示 0/50
[查看回测] [解释（AI，只解释不改数）]
```

## 5A. Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition
同卡片。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- OpenAI Math 主引擎，经典库补充；结果可复现。

---

### SYS-02 — 草图增补：采集：默认 AUTO + 可选手动采集按钮

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：O1,G2。

## 5. Purpose-built desktop composition
```
主体行：<主体名> | 模式 [AUTO ▾] | 上次 hh:mm | [立即采集] [暂停]
平台矩阵：平台 × 状态（运行/冷却/缺失）
缺失字段显示「—（数据缺失）」不显示 0
```

## 5A. Web Workspace composition
同桌面布局；批量：[对所选主体立即采集]

## 6. Purpose-built mobile composition
主体卡 + 同按钮。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 全部已登记主体默认 AUTO；无单主体硬编码；R&D 期风险闸门关、闭环前开（显示当前状态徽标）。

---

### SYS-04 — 草图增补：密钥与数据合规（G19，闭环内）

> 草稿，待 PO 审核。规划依据：G19 优化稿。

## 5. Purpose-built desktop composition
```
安全与权限 › 密钥与合规
密钥
  我的 API Key    ••••3f2a  安全存储 ✓  [轮换] [删除]
  连接器令牌      GitHub ✓  MCP×2 ✓      [逐个撤销]
  平台登录会话    小红书 ✓  抖音 已过期 → [重新登录]（内置浏览器弹窗）
数据合规
  采集来源清单    按用途列出，每条可查看来源与重构记录
  保留期限        [90 天 ▾]（用户选择）
  个人信息处理    默认脱敏 ✓    [查看处理日志]
  [导出合规报告]
```
## 5A. Web Workspace composition
同桌面。
## 6. Purpose-built mobile composition
分组卡片纵排，操作收进「…」菜单。
## 4. State additions
Ready / Loading / 数据缺失 / 会话过期（提示重新登录，不切换来源）/ 权限不足。
## 9. Executable acceptance
- 所有密钥不明文落盘，日志不出现明文；撤销立即生效。
- 合规报告不依赖账号体系即可生成。

---

### SYS-04 — 草图增补：用户开发者模式（G20a）

> 草稿，待 PO 审核。闭环内。参照：Obsidian 受限模式默认开启、插件继承应用全部权限；Chrome 未打包扩展须开发者模式开启；VS Code 扩展与主程序同权限；Android 解锁前警告非官方镜像风险并清除数据。默认关闭，由用户自己选。

## 5. Desktop
```
设置 › 开发者 › 用户开发者模式           [ 关 ○ ]
开启前（必须逐项勾选，[我同意并开启] 才可点）：
┌ 风险与责任协议 v1 ──────────────────────────────┐
│ □ 自行开发/修改的代码拥有与序境相同的权限，        │
│   可读写本机文件、联网、调用已授权平台会话         │
│ □ 由此造成的数据丢失、账号封禁、违法违规后果       │
│   由我本人承担，序境不承担法律责任                 │
│ □ 修改后的版本不享受官方更新保证，问题需先恢复     │
│ □ 开启前已备份账号数据   [立即备份]               │
│ [查看完整条款]   [取消]   [我同意并开启]           │
└──────────────────────────────────────────────────┘
开启后：
  顶部常驻条：⚠ 开发者模式 · 已修改 3 处   [关闭并恢复]
  本地扩展   [加载本地文件夹]  列表：名称/版本/权限/[停用]
  修改记录   每次修改的文件与时间，可逐条撤销
  本地 API   http://127.0.0.1:xxxx  令牌 •••• [复制][重置]
  调用日志   最近 100 次（脱敏）
  备份/恢复  [备份账号数据] [从备份恢复] 列表：时间/大小
  协议记录   v1 · 2026-10-14 同意 · [撤回同意=关闭模式]
```
## 5A. Web：同桌面；本地 API 不提供（浏览器无本机端口）。
## 6. Mobile：只读（状态、修改记录、备份列表）；开启/加载扩展需桌面端。
## 4. States
关闭 / 协议未完成 / 开启 / 扩展出错（自动停用该扩展并显示原因，不影响主程序）/ 备份中 / 恢复中 / 数据缺失 / 权限不足。
## 9. Acceptance
- 未逐项同意不能开启；同意记录（版本、时间）随账号保存并可导出。
- 关闭后所有用户扩展停用但保留在磁盘，可一键恢复官方状态。
- 备份可在另一台设备恢复；不需要登录也能本地备份。
- 关闭时不监听端口；令牌不明文落盘。

---

### SYS-05 — 草图增补：视觉风格 · Logo · 五位角色（闭环内，PO 2026-10-14）

> 草稿，待 PO 审核。沿用已定：角色 Pim/Bram/Ness/Jas/Aris；水印「据实生成 · 来源可溯 · AI生成信息请辛苦核对」；Logo 走 r4 方向，待 PO 选定。零预算。

## 5. Desktop
```
设置 › 通用 › 外观
主题  (●) 跟随系统 ( ) 浅色 ( ) 深色      强调色 [茉莉白 ▾]
字号  [100% ▾]（最高 200%）   减少动态效果 [跟随系统 ▾ / 开 / 关]
角色  [显示角色形象 ✓]  Pim 商业运营 · Bram 品牌市场 · Ness 共享能力 · Jas 系统 · Aris 自研 AI
预览  ┌ 当前页缩略 ┐ 改动即时生效，返回原页面、滚动位置和草稿不丢
```
## 5A/6：Web 同桌面；手机纵排，预览改为整页实时生效。
## 4. States：正常 / 加载 / 素材缺失（显示占位名字，不用他人素材）。
## 9. Acceptance
- 切换主题后路由、滚动、选择、未保存草稿不变（SYS-05 原合同）。
- Logo/角色图为自有矢量稿，许可清楚；AI 草图生成的素材标注来源。
- 200% 字号与减少动态效果下全部屏可用。

---

### SYS-06 — 草图增补：内置浏览器：标签/地址栏/前进后退/折叠/查看原文

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G1,G97。

## 5. Purpose-built desktop composition
```
[◀][▶][⟳] [地址栏 https://… ][☆][⋯]  [⌄折叠]
[标签1 ×][标签2 ×][+]
┌ 真实页面（同一受控会话）┐  右侧：当前任务卡 [返回任务]
└───────────────────────┘  底部：[在外部浏览器查看原文 ↗]（仅用户点，无采集）
```

## 5A. Web Workspace composition
同桌面布局；折叠后收为顶栏胶囊「浏览器·2 个标签」，任务不中断。

## 6. Purpose-built mobile composition
全屏单标签+底部标签切换；折叠为底部条。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 外部打开永不自动触发、永不采集；无 Edge/9222；书签/历史/阅读模式可选。

---

### SYS-06 — 草图增补：产品内登录失效弹窗 LumenisPlatformRecoverySheet

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G51,G133。

## 5. Purpose-built desktop composition
```
┌ 小红书（RedNote·香港账号来源）登录已失效 ┐
│ 任务「<主体> 采集」已暂停，进度已保存      │
│ [扫码登录] [在内置浏览器登录] [稍后]       │
│ 状态：等待验证 / 冷却中 mm:ss             │
└──────────────────────────────────────────┘
```

## 5A. Web Workspace composition
同桌面布局；同一时刻只弹一个；成功后自动回到原任务并续跑。

## 6. Purpose-built mobile composition
底部 Sheet，同内容。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 后台采集本身不弹窗；仅登录失效弹；适用全部平台与全部已登记主体。

---

### SYS-07 — 草图增补：创始人内部开发者模式（G20b）

> 草稿，待 PO 审核。闭环内。仅创始人账号可见。参照：GitHub 受保护分支须状态检查通过、环境审批；electron-builder stagingPercentage 分批推送、回滚须发更高版本；Tauri 更新必须签名；Sparkle 分 7 组逐日推送。

## 5. Desktop
```
设置 › 开发者 › 内部发布（仅创始人）
① 上传更新   [选择代码包/拖入]  或  [从 GitHub 分支 ▾]
             说明 [            ]               [一键上传]
② 测试       构建 ✓  单元 ✓  集成 ⟳  端到端 ○  安全扫描 ○
             任一失败 → 停止，不发布，显示失败项与日志
③ 发布       渠道 (●) 内测 ( ) 正式
             分批  [10%] → [50%] → [100%]  每批观察 [24h]
             签名  ✓ 已签名（未签名不允许发布）
             [发布]（测试全绿才可点）
④ 发布中     v1.3.0 · 10% · 崩溃率 — · 报错 0
             [暂停] [扩大到下一批] [回滚]
             回滚 = 发布更高版本号的上一个稳定版
历史         版本/时间/批次/结果/[查看说明]
```
## 5A. Web：同桌面。 ## 6. Mobile：只看状态，可[暂停][回滚]，不可上传。
## 4. States
空闲 / 上传中 / 测试中 / 测试失败（阻止发布）/ 待发布 / 分批中 / 已暂停 / 已回滚 / 指标缺失（显示「数据缺失」，不显示 0，缺失时不自动扩大批次）。
## 9. Acceptance
- 非创始人账号看不到入口，接口拒绝。
- 测试未全绿、未签名均无法发布。
- 用户端自动更新校验签名；可在 设置›通用 选择「自动更新 / 仅提醒」。
- 回滚后所有批次用户在下次检查时得到稳定版。

---

### SYS-08 — 草图增补：运营与工作区生命周期（G19，闭环内）

> 草稿，待 PO 审核。租户=工作区；工作区备份/恢复/归档/删除与多成员/多租户随账号体系一起在闭环内完成。

## 5. Purpose-built desktop composition
```
可观测性 › 运营
工作区   默认工作区 · 创建于 2026-10-01 · 主体 N 个
  [备份] [恢复] [归档] [删除工作区]（二次确认）
运行      采集成功率 96% · 模型可用 ✓ · 队列 3
告警      抖音会话过期 1 项 [处理]
版本      v0.x  [检查更新]   [导出诊断包]
COMMERCIAL_READY 检查表  合规 ✓ 密钥 ✓ 生命周期 ◐ 运营 ✓ 账号 ◐
```
## 5A / 6
Web 同桌面；手机纵排，检查表折叠。
## 4. State additions
Ready / Loading / 数据缺失（指标未采到显示缺失）/ 不可用（显示原因）。
## 9. Executable acceptance
- 备份可在另一台设备恢复；删除工作区前强制提示导出。
- 指标缺失不显示 0；检查表每项链接到证据。

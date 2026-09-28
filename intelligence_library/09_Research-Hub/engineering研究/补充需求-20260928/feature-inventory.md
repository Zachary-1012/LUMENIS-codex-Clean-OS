# 补充需求 DOCX 逻辑需求与主张清单

## 提取依据与分层

- 原文：`D:\wps云空间\WPS Cloud\WPSDrive\280397037\WPS云盘\补充需求.docx`。
- 完整逐段提取见同目录 `doc-extraction.md`；正文按 XML 顺序编号 `BODY.P001` 至 `BODY.P1193`，其中 802 段非空。以下是去重后的 23 项，不替代逐段原文。
- `BODY.P001–P052` 是前置的任务/验收要求；`BODY.P054–P1054` 主要是解释、设计建议和对代码现状的叙述；`BODY.P1058–P1193` 主要是旧状态诊断、重复的缺口清单和总结。后半段的“当前已有/当前缺少”均为文档作者当时的主张，文中没有逐条证据快照或明确审计时间，须由主控按当前源代码、运行、远端和受保护工作树重新核实。
- 正文实际有 1,193 个 Word 段落、0 个 Word 表格；`BODY.P970–P988` 是以 Markdown 管道符写进普通段落的比较表，已保留为独立段落。无嵌入图片、批注、脚注、尾注、修订插入或修订删除；页眉/页脚各一段且为空。customXml 中无文本。
- 包内核心属性：创建 `2026-09-28T11:33:00Z`，修改 `2026-09-28T11:47:10Z`；文件系统修改时间 `2026-09-28 11:47:28 +08:00`。DOCX app 属性记载 27 页，但内置渲染器因找不到 `soffice.exe` 未能渲染，页数未做视觉复核。提取稿没有发现需遮蔽的凭据样式字面值。

## 去重后的逻辑需求与主张

| # | 原文位置 | 准确意思 | 分类、重复与核验提示 |
|---|---|---|---|
| 1 | BODY.P001–P007 | 目标是把已批准的本地浏览器、采集、授权、Evidence、Canonical 和 SYS-06 能力接成闭环；先核 Git/实际 Core/前端状态，保护有效本地工作，不 reset/clean/覆盖或削弱测试。 | 前段任务要求。与当前 AGENTS 的保留 dirty work、先核远端原则一致；文中要求“继续当前批次/不要中断”的措辞须服从主控当前排程。 |
| 2 | BODY.P009–P013；P064–P080；P736–P845 | 用户选择平台并明确授权；只显示实际支持且验证过的浏览器；需要时让用户在受控窗口正常登录/扫码，失效时提供恢复登录，不承诺永久免登录，也不反复要求用户粘贴 Cookie。 | 核心体验要求，后段多次复述。实现应落在现有 Browser/Permission owner；“授权一次后永不再操作”不是原文要求，也不应作此承诺。 |
| 3 | BODY.P015–P020；P042–P048 | 连接授权要绑定用户/会话、设备、平台身份和数据/操作范围；连接本身不自动采集，Subject/BrandFocus 切换不授权；用户自动采集默认关闭、需另行明确开启；该授权是只读，不能发布、点赞、关注、私信或修改账号；支持再验证、暂停、恢复、撤销，并规定在途任务如何响应撤销。 | 核心 Permission 要求。不要把“连接浏览器”与“开始采集”、产品内部 Evidence 落库、或其他已有独立授权合并成一个许可。撤销与在途策略需遵循现有 Permission/Evidence 合同。 |
| 4 | BODY.P022–P026；P507–P542 | Cookie/Token/Storage State/Profile 等敏感会话数据应留在本地 SYSTEM，不上传云端、AI、GitHub、日志、Evidence 或报告；不得读无关或未授权账号；仅文件存在或 CDP 在线不能显示已连接，需验证平台身份和会话能力。 | 核心安全要求。Cookie、CDP 端口与配置文件均不是授权或成功证据。文中“保护当前排除个人/工作账号”必须按当前明确的身份边界执行。 |
| 5 | BODY.P028–P033；P1161–P1175 | 仅覆盖现有获准平台/字段；公开来源足够时走公开路径，需要登录字段才用获准本地会话；真实输出经 `Source → Capture → Evidence → Canonical → CTH Subject/BMP BrandFocus → 页面/报告/导出`；不得用 AI、默认值或 fixture 补缺失事实。 | 核心数据链要求。与当前“公开研究采集已授权但仍守访问/Permission/Evidence”相容；字段范围、平台映射和全局覆盖需接到当前数据主线，不能据此缩减范围。 |
| 6 | BODY.P375–P450；P1161–P1175 | 按平台与字段诚实区分公开/登录可见性；未登录可能少字段、少结果、限流或不可见；公开源不够再走授权会话，仍拿不到则 `NOT_AVAILABLE/BLOCKED`，不让 AI 补齐。 | 核心真实性要求；P1161–P1175 是后文复述。应保留缺失、未采集、过期、无权限、错误与真实零的不同状态。 |
| 7 | BODY.P031–P033；P044–P045 | 样例必须落入真实 CTH Subject 和真实 BMP BrandFocus，数据进入各自正确业务对象；至少验证一个 CTH Subject 与一个 BMP BrandFocus，但两个样例不能代表所有平台/维度完成。 | 核心验收样例；范围上是最低样例，不是完整商业/全球覆盖证据。文档未给出全量 Subject/BrandFocus 样本计划。 |
| 8 | BODY.P035–P040；P545–P595；P1112–P1155 | SYS-06 应呈现真实浏览器网页 viewport 与地址/来源/状态、必要导航、任务返回和授权控制；要匹配当前会话、页面和版本，不能显示旧画面；网页与 AI 分析要区分；Web/Desktop/Mobile 按批准职责呈现本地执行状态。 | 核心用户可见结果要求。后半段将其重复总结为“状态面板不等于浏览器”；具体屏幕仍需当前 Experience/Screen 规范和实际运行验收。 |
| 9 | BODY.P598–P635 | 文中声称 AI Browser API 已有 sessions/frame/navigate/observe/action/verify/stop/evidence 路由，frame 带 Frame/Target ID、Page Revision、Captured At、宽高等关联信息。 | **历史实现主张**兼有可复用契约提示。不能据此认定当前 API 或跨层绑定仍存在；若源码核验成立，需用版本/会话绑定避免陈旧 viewport。 |
| 10 | BODY.P042–P052 | 在同一候选版本上验证首次授权、登录/复用、限域采集、CTH/BMP 与 Evidence、重启复用、登录失效恢复、撤销拒绝访问；另验只读拒绝写动作、凭据不泄漏、错账号拒绝；核实源码/运行 Core/默认入口为同一验收版本，交付测试、E2E、线上提交和用户入口/剩余授权步骤。 | 核心验收要求。运行环境/平台权限缺失时记 `BLOCKED`，不能伪造完成；不能用源代码/API 成功替代真实用户工作 E2E。 |
| 11 | BODY.P161–P209；P736–P760 | 文中建议在产品 UI 提供“系统默认/Chrome/Edge/序境独立浏览器”选择，并只暴露受支持选项；同时声称当前后端能识别 Windows 默认 Chrome/Edge，但用户级偏好闭环尚缺。 | 选择 UI 是建议；现存识别能力是历史主张。只可按当前可支持/已验证的浏览器展示，不应把默认浏览器选择解释为访问其所有个人 Profile 的授权。 |
| 12 | BODY.P102–P158；P350–P371；P927–P943；P966–P1002 | 文中列举 CDP 附着、持久化 Profile、Cookie 读写、默认浏览器识别和若干 Browser/Collector 能力，并建议把分散能力收敛起来。 | **重复的历史能力盘点**（散布于正文多个章节）；这些不是当前实现证明，也不是新增需求。要逐 owner 重核后复用。 |
| 13 | BODY.P213–P290 | 文中称已有 General Browse、RedNote HK/International、Douyin read-only 三类分离的浏览器身份/Profile，避免不同用途 Cookie 混用。 | **历史实现主张**；保留按来源/平台/用途隔离的安全原则。身份/Profile 名称、端口和在线状态均需当前核验，不能触碰明令禁止的 Mainland XHS 个人账号。 |
| 14 | BODY.P292–P346；P849–P881；P1082–P1110 | 文中称 RedNote HK/International 路径仍由本地 Cookie 文件与身份门禁控制，曾显示 `SESSION_EXPIRED`，建议会话管理而非定期粘贴 Cookie。 | **旧运行状态主张**，文中没有采集时间/日志证据；按当前获准的 HK/国际身份核验。CN 个人账号始终禁止访问。此段不能作为请求 Cookie、探测个人 Profile 或更换身份的依据。 |
| 15 | BODY.P686–P734 | 反对把第三方 Cookie 转换网页作为正常产品流程；若支持手工粘贴 Cookie/JSON/Playwright Storage State，只建议作为隐藏迁移/恢复工具。 | 可选建议，不是验收要求。默认 DEFER；若未来采用须经过现有安全、Permission、Evidence 和 UX gate，不能让它成为常态登录方法。 |
| 16 | BODY.P801–P845 | 建议显示连接/最后验证时间、逐能力可用状态、自动维护关闭、重新验证/断开；失效时显示需重新登录并恢复同一 Profile。 | 对第 2、3、8 项的状态细化与重复，不应视为额外产品线；状态必须来自真实 Session Health 和权限结果。 |
| 17 | BODY.P369；P885–P923；P1004–P1038；P1183–P1189 | 多处提出 `Session Authority`/`Cookie Vault`/`session_handle`，并称其可汇聚 Browser Profile、Storage、会话健康、再认证、授权与撤销。 | **存在内部张力**：P016 明确禁止新增平行 Session Authority；后段又把“唯一 Session Authority”作为收敛目标。适配为复用现有 SYSTEM Browser/Collector/Permission owner 内的统一调用链，不新建第二 owner/DB/架构。 `session_handle` 仅是实现提案。 |
| 18 | BODY.P927–P1000；P1181–P1193 | 文末反复总结“已有后端基础、不新增产品功能/owner，主要收敛既有 Browser/Session/Permission/Collector/Evidence/Canonical/SYS-06”。 | **重复结论**，不是 15 项独立新需求。保留“复用现有 owner、收敛到真闭环”；“后端大半已有”的百分比/状态不采纳为事实。 |
| 19 | BODY.P1042–P1054 | 文档把责任映射到 Round 04 Permission、06 Collector/Browser、08 多端入口、14 SYS-06/体验、15 E2E/Release，明确不建第 16 轮。 | 映射与当前 15 轮名称大体吻合，但只作导航建议；实际进入依赖、当前 taskbook 覆盖和接收线程由主控按当前 owner/顺序确认。 |
| 20 | BODY.P1058–P1080 | 文中声称本地 dirty tree 覆盖新接口，并报告隔离副本 139/139 与主工作树 69 pass/12 fail。 | **需新鲜证据重新核验的旧诊断**，不是本次新跑结果。不能据此重置、覆盖、批量应用、认定 blocker 已解决或把失败改为通过；先对照当前 fresh `origin/main` 与被保护工作树。 |
| 21 | BODY.P637–P684；P947–P952；P1112–P1155 | 文中声称 SYS-06 被标为 unavailable，已有 screen 仍是状态面板而非完整 viewport，建议接上 Browser Runtime。 | **重复的历史 UI 状态主张**。只说明文档作者当时认定的缺口；需查当前 Flutter 主线、Screen/Experience 规范和真实运行界面。不能直接解开 `unavailable` 或按后段草图实现。 |
| 22 | BODY.P970–P988 | 以段落中的 Markdown 对照行列出连接、Session、Profile、默认浏览器、浏览器身份、Tab/frame/API、Permission/Collector、Evidence→Canonical、SYS-06 等“已存在”能力。 | 这是**普通段落里的伪表格**，不属于 Word 表格；多数与第 12、18 项重复，且“已有”全是历史主张，逐条重核才可映射 owner。 |
| 23 | 全文，尤其 BODY.P028–P045、P1042–P1054 | 文档聚焦本地浏览器连接、会话凭据、Permission、SYS-06；没有覆盖主控已给定的更大采集/业务范围。 | **文档遗漏（不可据此缩 scope）**：14 个国家组、CTH 与 BMP 两域各至少 50、GLOBAL/ALL 基线及自动维护、Subject 与 BrandFocus 分离、场内品牌与品牌市场、媒体/社媒/消费者 intelligence、跨平台原生字段映射、缺失诚实、历史序列均未被完整规定；也未覆盖终端用户 MANUAL 默认/AUTO 明确 opt-in、已批准的公开 prelaunch 基线维护，以及视频/音频播客/通用制作三类工作流。应由主控把浏览器/Session 补充嵌入当前主线，而不是替代主线。 |

## 结论供主控使用

1. 可继承的核心补充：用户主动连接/正常登录与恢复；授权与采集分离；本地保管敏感会话；公有来源优先、已授权会话补足、不可得如实标注；Evidence→Canonical→正确 CTH/BMP；SYS-06 必须是可操作真实 viewport；同一候选上的授权、恢复、撤销及真实业务 E2E。
2. 后半部主要是上述要求的解释、重复总结和特定时点的源码/测试断言。除“按已存在 owner 收敛”的方向外，不把其架构名词、完成百分比、路径实现状态、`SESSION_EXPIRED`、`unavailable` 或测试数字当作当前 Product Truth。
3. 该 DOCX 没有任何原生 Word 表格、图片、批注、脚注/尾注或 tracked changes；普通段落里有 19 行 Markdown 管道表格内容。完整正文定位可直接查 `doc-extraction.md`。

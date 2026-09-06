# 线上×本地源码级体检修补增量清单 V1.0（2026-09-06 晚）

> 线上审计基线=main 0dca073（PR#28，两份审计报告）；本地工作分支=lumenis-dual-domain-v3 @ 1085104（已 push origin，领先 main 9 commit / 1007 文件 / +271173 行）。原则：只增量修补、不推翻、不重造、自研；UI 定死最新风格，禁止回退旧 UI。

## 一、仓库状态核对
- 线上 main：0dca073（审计报告基线，v5.9.7）
- 本地/线上 lumenis-dual-domain-v3：1085104（v5.9.10，含双域/账户/迁移/智能库/cookie/三语框架）
- 线上历史功能分支（已开发，必须审计复用，禁止重写）：
  - `feat/i18n-ko-en-zh-v6` 系列（research/impl/impl2/impl3/research-final×3）→ 中英韩三语已有深度研究与实现，取最新实现+韩文词条复用
  - `feat/podcast-table-system-v1`~`v7` → 播客做过 7 版，D1 播客补回直接取 v7 适配
  - `feat/keyboard-shortcuts-modal` → 快捷键模态
  - `feat/video-intelligence-passive-v1` → 视频智能（含合约）
  - `feat/zb-runtime-preflight` → 启动预检 8 项
  - `feat/lumenis-p1-full-product-ui`、`integration/rd-data-function-ui-baseline` → 产品 UI 基线
  - `feat/lumenis-internal-beta-closure`、`fusion-exec`×7、`product-convergence`×系列 → 收敛资产
- 动作：各组先 `git log/ls-tree` 审计上述分支最新实现，可复用的 cherry-pick 或按当前架构适配，标注来源分支；真没有的才新建。

## 二、16 条红线对账（线上报告 R01–R16，本地逐条核）
- R01 AI 不可用核心链仍可运行 / AI 不单独决定主体时间数量周期事实 → 符合（规则内循环+failover），保持
- R02 Cookie/Token/密钥不入库不外发不进 Git → 符合（.gitignore 已覆盖，提交前检查通过）
- R03 禁绕过访问控制/验证码/平台安全 → 符合，采集只读、风控熔断
- R04 主体排除词一票否决 / 五字段命中 / CTH 事实不被 ZBMP 覆盖 → 符合（subject_rules 红线保护），迁移重判守此
- R05 自动采集每天 00:00/12:00 两次+显式开关、手动 30 分钟；TopicCampaign 例外 6~8 次 → **需确认调度门在主链路生效**，补测
- R06 异常不伪装空数据 / session 失效弹可操作恢复窗口 → 符合（auth_recovery_center），保持
- R07 写操作全过 PermissionGate、fail-closed → **进行中**，全面接入写操作
- R08 安全边界写代码不写提示词 / 四层防御 → 符合（security_boundary）
- R09 DB 迁移先备份/新增优先/可回滚 → 符合（历史迁移只增不删）
- R10 新采集器/Adapter 旁路验证等价后才切换 → 符合（全平台 adapter 未通过回归不接管生产）
- R11 跨仓只走版本化 Contract / OSAI·序枢非运行时依赖 / 不调 GGI 生产库 → 符合（三仓规则）
- R12 报告统计走主体硬过滤+DB 口径强写回 / report_id+artifact_hash 可追溯 → **需确认 report_engine 全链路带 artifact_hash**
- R13 风险/情感 unknown 不当负面 / critical≠high / 0/0≠0 → 符合，保持
- R14 KOS 权重全配置化禁硬编码 / KOS 主体层不混 UGC / 复用现有表 → **进行中**，kos_metrics/attribution 改读 config/kos_platform_rules.json
- R15 唯一执行权威 V3 / 先 READ AUDIT 再写代码 / 旧规则分类后才删 → 符合
- R16 发布走完整 Gate+目标环境验证 / 绿检查非充分 → 收口前做九连验

## 三、P0/P1 增量修补（按线上问题矩阵）
**P0（收口前必须）**
1. 数据质量终验：963 notes 中 312 unknown/6 None 按 subject 红线重判，命中归 CTH、真不相关保持 unknown 显式标记，禁硬塞/拿 0 填
2. 自动运行九连验：stop→start、崩溃恢复、调度与 Guardian 自启、AI failover 自动降级、ZBMP/CTH 两域主链 E2E
3. 采集调度门 R05 主链路生效确认+补测
4. 前后端契约自动化对账《对账表》清零断链

**P1**
5. PermissionGate 写操作全面接入（含双域）
6. KOS 指标/归因去固定公式→平台规则 config 驱动（R14）
7. AI 治理审计字段齐全（ai_run_id/target_type/target_id/model_name/model_version/prompt_version/input_hash/output/confidence/system_result/final_result/accepted/human_correction/created_at）
8. 报告全链路 report_id/artifact_hash/generator_version/data_version 可追溯、DB 口径强写回防 AI 误写
9. Legacy 收敛标记（不删）：safety_boundary / system_guardian / compliance_gate / 根 risk_engine / web_monitor_v570 → 新代码用新入口，旧件仅向后兼容
10. 微信两类接入：wechat_notifier 通知链路补全（缺公众号凭证则 BLOCKED）、sogou_wechat 采集 adapter 接入主链+补测
11. ui_view_model 函数驱动可视化接入，首页 source:占位/Provider:detecting 接 lumenis-data 真实绑定

## 四、UI 定死最新风格（不用旧 UI，违者回退）
**唯一 UI 基线（冲突以此为准）**：
- 设计 token：`static/css/lumenis-tokens-v2.css` + `zbc-design-v1.1.css` + `zbc-layout-v1.1.css`
- 标准：`docs/design/LUMENIS-UI-STANDARD-v1.0.md` + `LUMENIS-UI-UX-MASTER-v1.0.md` + `ZBC_UI_UX_LANGUAGE_V2.md`
- 架构：Left Navigation → Main Workspace（LOCKED）；WEB-NO-SCROLL 固定视口有界层级；同级卡片横向叠层滑动+点开展开（iOS 照片式）
- 图标：自研 `static/js/lumenis-icons.js`（24/1.5px 线性/fill=none/currentColor），全站 licon()，禁实心块/emoji/外部图标库
- 多语：`static/js/i18n.js` + `terminology.js` + `static/locales/{zh-CN,en,ko}.json`，复用线上 i18n-v6 研究成果，设置-外观切换默认中文
- 术语：去 ZBC/OSAI/SYS 内部代号，用序境LUMENIS/品牌智能/太古汇智能/系统
- 单一所有权：生产数据一个真相源、业务计算一个规范函数、运行时一个权威 owner、视觉区域一个渲染权威/DOM owner，组件不得竞争改同一区域
- AI Workspace ≤20 动态卡片，单一 stack controller 管 active/位置/缩放/透明度/模糊/z-order
- 禁止：回退旧 production/intelligence IA、Mock 数据、静态成功、假绿、无止境纵向滚动、为每个表面建独立业务逻辑树
- 采集数据表格沿用既有专业模板，不卡片化

## 五、功能完成度矩阵（当前真实状态，禁把 PARTIAL 写成 VERIFIED）
| 域 | 项 | 状态 |
|---|---|---|
| CTH | 启动/DB/主体规则/采集主链/风险/事件/日报 | VERIFIED（采集 cookie 3/8 VERIFIED） |
| CTH | 微博/知乎 cookie | BLOCKED（凭证失效待用户更新） |
| ZBMP | 双域切换/权限/账户/TOTP/品牌/内容/KOS/竞争/风险 | VERIFIED/PARTIAL |
| ZBMP | 六类报告（brand/performance/competitive/growth/content/brand_risk） | PARTIAL（补全中） |
| SYSTEM | Runtime/Guardian/AI/DB/Security/Settings | PARTIAL（九连验中） |
| Shared | Evidence/Trace/Evaluation/智能库 | VERIFIED |
| Shared | 三语/线性图标/术语 | PARTIAL（框架已建，全站替换中） |

## 六、执行顺序
P0（数据终验+九连验+调度门+契约对账）→ P1（权限/KOS配置化/AI字段/报告追溯/Legacy收敛/微信/函数驱动）→ 线上历史分支复用审计（i18n-v6/podcast-v7/快捷键/视频智能/preflight）→ UI 统一落地（定死基线）→ P2/P3 维护期。完成一项在 audit/TODAY_REQUIREMENT_STATUS_LEDGER 销一项并给证据。

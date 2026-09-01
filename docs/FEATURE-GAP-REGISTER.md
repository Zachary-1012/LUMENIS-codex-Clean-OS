# FEATURE-GAP-REGISTER（功能缺口总账）

> 2026-08-31，配合 FEATURE-FINAL-VERIFICATION-MATRIX。原则：宁可多记一个 Gap，不制造一个虚假 ACTIVE；只登记，本轮不改生产代码。
> 严重程度：P0 阻塞生产/数据正确性；P1 阻塞 Release Gate / 安全 / 验证闭环；P2 架构与可维护；P3 文档/口径/清理。
> 「阻塞上线」指阻塞 CTH-POMS 正式 Production Release；「阻塞 UI」指阻塞 UI 一次性施工。

| Gap ID | Feature | 问题（实测事实） | 级别 | 影响 | 原因 | 建议 | 阻塞上线 | 阻塞UI | 需代码 | 需测试 | 需Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GAP-01 | 全局/测试体系 | 统一 `pytest tests` INTERNALERROR：test_api_smoke.py 顶层 sys.exit 打断收集；36 个 test_ 仅 5 个含 def test_（50 用例），31 个脚本式 | P1 | 无统一可重复测试入口，CI/Release Gate 无自动证据 | 历史以独立脚本充当测试 | 脚本迁 scripts/ 或改造为 pytest；统一 run 入口 L0-L10 | 否(生产在跑) | 否 | 是(测试码) | 是 | 是 |
| GAP-02 | SUBJ/EVT/RISK/RPT 红线 | 根 risk_engine、aggregate_events、build_daily_report 仅 test_e2e 集成级覆盖，缺函数级直接单测；test_risk_engine 实参测 collector_guard、test_report_periods 实参测 export_report（名实不符） | P1 | 红线回归靠集成用例，边界/异常分支覆盖不足 | 早期测试按链路写 | 为三个 Owner 补纯函数直接单测（含时间口径/主体边界/空输入） | 否 | 否 | 是 | 是 | 是 |
| GAP-03 ✅RESOLVED(2026-09-01) | CTH-AUTH-001 | ~~主 SPA static/index.html 未引~~ **Step1 已挂主 SPA 并随 main=`580c2cf` 合并，8301 实测统一弹窗正常**；残余：A/B/C 三分支 E2E 与规范 pytest 未补 | P1→残余P2 | 主 SPA 弹窗缺口已闭 | 已随 UI 合并解决 | 补三分支 E2E/pytest（不再阻塞 UI） | 否 | 否(已闭) | 是(测试) | 是 |
| GAP-04 | ZBMP-SETT-001/安全 | 三套可执行代码入口 /api/developer/run、/api/dev/run-code、/api/config/run-code 并存未收口 | P1(安全) | 远程执行面重复、审计分散 | 多窗口迭代叠加 | 单一受控入口+权限+审计，其余 MIGRATION_REQUIRED→回归→退 | 否 | 否 | 是 | 是 | 是 |
| GAP-05 🚧已签字施工中 | CTH-MON-003 | 动态调度仍 shadow-only，未门控生产 | P1 | 固定/动态两套策略并存 | **用户 2026-09-01 已签字门控** | feature flag 默认保守(仍 shadow)→灰度→门控，附回滚；不弱化熔断 | 否 | 否 | 是 | 是 | 是 |
| GAP-06 | CTH-SUBJ-002 | subject_type/content_type 枚举与 /types API 已有，notes 落库列/写入/筛选未贯通；禁 user_type=UGC | P1 | 双维度无法在列表/统计使用 | 只做到 API 层 | 向后兼容加列+写入+筛选 | 否 | 否 | 是 | 是 | 是 |
| GAP-07 | CTH-EVT-002 | 营销/传播/舆情三类 + 触发/衍生/继发/并行四关系未完成（现 16 事件 1 关系） | P1 | 事件演进链不完整 | 图谱刚持久化 | 补类型/关系与前端只读图 | 否 | 否 | 是 | 是 | 是 |
| GAP-08 | 全局/Evidence | app_evidence_records 为外部抓取表且 0 行；测试/运行 Evidence 无统一存储与 L0-L10 归档 | P2 | 「跑过/通过」无版本化证据可追 | 未建 Evidence 层 | 建 Evidence 记录(commit/version/result/artifact) | 否 | 否 | 是 | 是 | 是 |
| GAP-09 | CTH-EVT-003 | 负面评审两套 API（/negative/* 与 /negative-review/*+event-review）并存 | P2 | 状态可能双写不一致 | 新旧实现未退 | 定唯一 Owner，另一标 DUPLICATE→回归→退 | 否 | 否 | 是 | 是 | 是 |
| GAP-10 | CTH-RPT-002 | 报告导出/渲染多实现（报告域 12 路由） | P2 | 维护重复 | 多窗口叠加 | 统计唯一走 build_daily_report，渲染收敛 | 否 | 否 | 是 | 是 | 是 |
| GAP-11 | 跨仓/DCC | DCC 本地 77dd1e4 落后远程 023e2ba 27 提交，且脏 package.json/learning-store.js/persistence.js | P2 | 跨仓基线分叉 | 多窗口并行 | 需授权：先审本地 3 处去留→rebase→回 ZBC 升子模块指针 | 否 | 否 | 否 | 否 | 是 |
| GAP-12 | 治理/文档 | 多份并行基线（两份 PRODUCTION_BASELINE、PHASE1 与 UPA-PHASE1、consolidation-001/002） | P2 | 权威顺序易混 | 阶段叠加 | ADR 标注 Superseded，留一份权威 | 否 | 否 | 否 | 否 | 否 |
| GAP-13 | 数据库 | 51 表无可回滚迁移体系（Alembic 未引入） | P2 | schema 变更缺 Gate/回滚 | 一直 create-if-not-exist | Staging 副本先 baseline，再向后兼容迁移 | 否 | 否 | 是 | 是 | 是 |
| GAP-14 | MON-003/RISK-002/SYS-002/SETT | Feature 登记 API 前缀不精确（schedule/circuit/v4 前缀挂载），功能真实存在 | P3 | 文档与路由表对不上 | 蓝图 url_prefix 嵌套 | 校正 Registry 路径表述 | 否 | 否 | 否 | 否 | 否 |
| GAP-15 | CTH-SYS-002 | daily_git_sync.py:72 `current_version` 漏括号，自动提交标题卡 v5.8.9 | P3 | 版本标题不准(不影响运行) | 调用方笔误 | 改 current_version() 并加断言 | 否 | 否 | 是 | 是 | 是 |
| GAP-16 | CTH-SYS-003 | cloudflared 临时域名，未固化固定域名/HTTPS/断线自愈证据 | P3 | 公网地址会变 | 尚未上固定服务器 | 固定域名/隧道开机自启+健康探针 | 否 | 否 | 是 | 否 | 是 |
| GAP-17 | Runtime | 8200 两个重复 app.py 实例（pid 18852/19916） | P3 | 端口/资源重复 | 历史启动残留 | 授权后保留单一实例 | 否 | 否 | 否 | 是 | 是 |
| GAP-18 | 测试体系 | 31 个脚本式文件命名 test_ 但无 def test_，易被误读为「有测试」 | P3 | 假覆盖错觉 | 同 GAP-01 | 与 GAP-01 一并迁移/改名 | 否 | 否 | 是 | 是 | 是 |
| GAP-19 | Runtime/Browser | Selenium 0 真 import 待回归后退；Browser/Scheduler/Collector/AI 重复调用待按需启动验证（只审计不重构） | P2 | 运行时冗余 | 历史并存 | 引用/运行依赖分析→替代验证→回归→退 | 否 | 否 | 是 | 是 | 是 |
| GAP-20 | 工程清理 | .trae-cn IDE 目录忽略确认；根目录 start_*.bat/.bak/日志收敛 | P3 | 仓库噪声 | 长期堆积 | 分批登记后清理，不边开发边删 | 否 | 否 | 否 | 否 | 否 |
| GAP-21 | ZBMP-IMP-001 | importer 3 个 py 存在，但无前端入口/API/专表 | P2 | 有代码易被误判完成 | 后端先行 | UI 占位；补 API/专表后再升 DEVELOPING | 否 | 是(占位) | 是 | 是 | 是 |
| GAP-22 | ZBMP-BRAND-003 | swire_notes 空表，专题在建 | P2 | 功能无数据 | 尚未灌数 | 保留 UI 占位与空态 | 否 | 是(空态) | 否 | 是 | 是 |

## 汇总
- P0=**0**；P1=7（GAP-01/02/03/04/05/06/07）；P2=8（08/09/10/11/12/13/19/21/22 记 9 项，其中 22 偏 P2-P3）；P3=6（14/15/16/17/18/20）。
- 阻塞当前生产运行：无（8201 v5.9.9 在线、红线 50 用例 PASS）。
- 阻塞 UI 一次性施工：仅 **GAP-03 建议作为前置**，GAP-21/22 需在 IA 中占位（不阻塞，占位即可）。
- 阻塞正式 Release Gate：GAP-01/02（自动测试与红线直接证据）、GAP-04（安全收口）应在上线前关闭；GAP-05 门控可上线后按签字灰度。

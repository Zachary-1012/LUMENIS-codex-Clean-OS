# 线上审计×本地源码 体检修补增量清单 V1.0（UI基线锁死·旧UI禁止带回）

> 线上事实：origin/main=0dca073（PR#28，v5.9.7，2109文件）；本地事实：lumenis-dual-domain-v3=1085104（v5.9.10，领先main 9 commit / 1007文件）。本地是最新事实源。线上两份审计报告只采纳其**规范/红线/治理/业务规则**，其旧UI视觉与旧IA不恢复。

## 一、UI 基线锁死（唯一标准，违反即返工）
- 三域架构：ZBMP(Overview/Brand/Content/KOS/Competition/Risk/Reports)、CTH(Overview/Real-time/Events/Risk/Xiaohongshu/Reports)、SYSTEM(Runtime/Collector/AI/Database/Security/Settings)；Growth并入Overview+Brand Tab，199品牌/9业态=Overview Tab+Real-time筛选器。
- 设计token：static/css/lumenis-tokens-v2.css + zbc-design-v1.1.css；主色#0F766E / CTH#2563EB / SYS#7C3AED，芥子金#C9A961极低频；Inter+Noto Sans SC；默认浅色可切深色；H1 22/600、Data 24/700、Body13、Caption11。
- 线性图标：static/js/lumenis-icons.js（24/1.5px/fill=none/currentColor）全站统一走licon()；左导航小红书实心红块与所有emoji/实心块替换为线性品牌图标，品牌色只描边或小色点；禁止引外部图标库、禁止另画一套。
- 三语：static/js/i18n.js + static/locales/{zh-CN,en,ko}.json，可见文案走key不硬编码，设置-外观切换默认中文整页生效；韩文缺则missing回退中文不机翻。
- 标准用名：去ZBC/OSAI/SYS内部代号，序境LUMENIS/品牌智能/太古汇智能/系统；首页"ZBC生产真相×OSAI智能推理"类文案按术语表替换。
- No-Scroll：PC 100dvh、手机safe-area+dvh，放不下=同级卡片横向叠层滑动+点开展开模态(iOS照片合并样式)，禁止无止境纵向滚动；采集数据表格沿用专业模板不卡片化。
- 函数驱动：ui_view_model.py + lumenis-data.js 真实API绑定，首页source:占位/Provider:detecting接真实数据，无数据empty/错误error，绝不静默成0或假绿。
- 账户：AppleID式界面，ZBMP=TOTP动态验证码(otpauth绑iCloud钥匙串30s6位)、CTH=账号密码可改；设置8分区、双域隔离(CTH设置不出现ZBMP项)、栏目可配、Skill按需启用。
- 动效：lumenis-motion.css + carousel.js，去素加浓不花、reduced-motion降级。
- **禁止带回/引用**：templates/production、templates/intelligence 旧IA与旧视觉、staging旧ZBIP设计、旧launch-screen、任何mock数据/静态成功/假绿/死按钮。线上审计报告里的UI描述仅作规范约束(Left Nav+Main Workspace、单一所有权、tokens版本化、AI Workspace≤20动态卡片、WEB-NO-SCROLL)，不照搬其页面。

## 二、线上审计规范采纳（红线/规则/治理，必须对齐）
- R01-R16 十六条红线全部遵守（AI非生命线、凭证不入库不进git、禁绕过风控、主体排除一票否决、采集调度门、异常不伪装空数据、写操作过PermissionGate、安全写代码不写提示词、DB迁移先备份新增优先、新Adapter旁路验证、跨仓只走Contract、报告DB口径强写回、风险unknown不当负面、KOS权重配置化、唯一执行权威V3、发布走Gate）。
- 采集调度门(RELEASE_AND_AUTORUN_GATE)：自动采集每日00:00/12:00两次+显式开关+普通导航隐藏入口，手动单次30分钟；TopicCampaign独立配额[9,11,13,15,17,19]6次/天+手动上限8次，不消耗主舆情配额；风险信号STOP→COOLDOWN→HUMAN REVIEW；官方账号一律只读禁写操作。
- KOS：权重全部走config/kos_platform_rules.json禁止硬编码系数；kos_metrics/kos_attribution去固定公式→平台官方规则+研究成果驱动、可配置可延展；KOS是主体层不与UGC混淆，复用现有表不重建。
- 风险口径：RISK_LEVELS=(low,medium,high,critical,unknown)、SENTIMENT=(positive,neutral,negative,unknown)，critical≠high、unknown≠negative、0/0≠0；根risk_engine.py仅兼容转发，权威口径=daily_report/report_engine的DB统计。
- 报告：report_engine双域类型(CTH 6类/ZBMP 6类)，生成必验report_id/artifact_hash/generator_version/data_version真实落库，get_bundle区分缓存命中与即时生成防数据漂移。
- AI治理：智谱最大算力glm-5.3、日常glm-4.5-air、豆包ARK doubao-lite-4k最小兜底、Ollama qwen2.5-coder:7b-agent本地兜底；ai_call_logger审计字段14项(ai_run_id/target_type/target_id/model_name/model_version/prompt_version/input_hash/output/confidence/system_result/final_result/accepted/human_correction/created_at)缺一不可；新模型先Shadow Mode旁路；key只进.env。
- 权限：所有写操作过PermissionGate、fail-closed、未注册默认拒绝、高风险人工审批；与AdPermissionGate/agent_security共存统一编排，不替代不删除。
- Legacy收敛(保留不删、新代码用新入口)：safety_boundary.py→security_boundary四层编排；system_guardian.py→runtime_guardian；compliance_gate.py保留多法域裁决；根risk_engine.py仅兼容转发；web_monitor_v570.py→web_monitor.py。

## 三、本地现状对账（已完成，有证据）
双域隔离157测试通过；账户40路由+TOTP通过；历史迁移12353条0失败(963笔记双时间回填、十五周年paused保全)；智能库711 assets前后端；cookie_vault八平台(小红书/B站/抖音VERIFIED)；三语框架i18n.js+locales已建；线性图标lumenis-icons已建；设计token v2已建；服务8201 v5.9.9正常。

## 四、需修补增量（P0/P1，按序）
P0：①数据质量终验——963笔记312 unknown/6 None按subject红线重判收敛(命中归CTH、真不相关保持unknown显式标记，禁硬塞/拿0填)；②采集调度门确认在主链生效(自动窗口/显式开关/TopicCampaign独立配额/官方只读)；③KOS metrics/attribution改平台规则驱动(读config/kos_platform_rules.json，去硬编码)；④AI审计字段14项对齐ai_call_logger；⑤PermissionGate写操作全面接入(双域)；⑥自动运行九连验(stop/start、崩溃恢复、调度与Guardian自启、AI failover降级、两域主链E2E)。
P1：⑦Legacy入口统一收敛(新代码用新入口，Legacy保留委托)；⑧报告双域类型+artifact_hash真实落库验证；⑨226本地已开发模块审计核销(只适配不重写)；⑩前后端契约自动化对账《对账表》；⑪ZBMP六类报告；⑫微信wechat_notifier通知链路+sogou_wechat采集接入(凭证缺BLOCKED不伪造)；⑬UI阶段二按本清单第一节基线统一落地(线性图标/三语/术语/No-Scroll/函数驱动/账户界面/动效，旧UI禁止)。

## 五、外部阻塞(不伪造VERIFIED)
TOTP真机扫码绑iCloud(到步叫用户)；微博/知乎cookie EXPIRED需更新；x/instagram/极光PARTIAL；微信公众号appid/secret、Bark、Apple开发者账号、短信SMTP、广告平台凭证、域名；韩文母语校对。

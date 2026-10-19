# ORG-MECH-07：Creator跨渠道窗口、重复与退款

## 结论前置

**2248冻结候选已纠正方法标签与跨平台作者键，两项修复已存在。** 本轮独立hash比对确认；源状态不代表所有产品闭环通过。

固定main4dab的kos_attribution.py多触点结果是已准入BrandFocus笔记的加权互动份额，不读取购买、订单、用户旅程或退款。不能把这个份额命名为成交贡献、因果ROI或Creator佣金依据。现有scope、作者缺失、互动缺失与零分母保护保留；真实当前运行/结果未验收。

本轮先读domain_analysis §6.2–6.3及原相关需求：已闭Shapley/Markov的非因果边界、DiD/MMM理论，本研究不再重复。新增的是数据账本/时间窗口/跨平台身份/净退款的可执行口径。原Owner C1来源、C3/BMP方法、C5版本及证据，G149/G152–155、原能力18及24章、BMP-05/07/09/11；不把业务J编号错套前端同号页面。

## 官方公开原始方法

- GA4归因设置把模型、可分信用渠道、lookback分开；模型变更可重算历史/未来，而窗口变更只向后生效。默认天数是该产品设置，不是序境应复制的统计标准。[官方](https://support.google.com/analytics/answer/10597962?hl=en)
- 官方交易去重仅声明Web stream，不覆盖App stream；交易ID必须逐订单唯一且不含个人识别数据，空ID会误去重。不能推断跨所有平台自动去重。[官方](https://support.google.com/analytics/answer/12313109?hl=en)
- refund需要原transaction_id，item_id与quantity支持商品级退款；购买与退款事件不同，不能用删除旧销售替代退款记录。[官方](https://developers.google.com/analytics/devguides/collection/ga4/ecommerce#make_a_purchase_or_issue_a_refund)

本轮只读对应设置/去重/购买退款段，没有登录、安装tag、获取用户旅程或发起广告。以下是现Owner适配，不声称GA4保证因果、全平台身份或产品实现。

## 当前主规划与指定候选对照

product-plan-full.md:430的G149要求公开行为路径Markov/Shapley、DiD/合成控制、有对照才uplift、区间与相关非因果/拒答条件。没有要求此KOS份额代理必须按实际时间衰减，也没有给它半衰期参数。G147:428的半衰期属于Hawkes传播扩散，不能移植为G149硬要求。config/kos_platform_rules.json:7–15只有time_weight_coeff=0.5/time_weight_range=1.0及阈值，没有half_life/window。不要为了纠正误导标签私自更换算法。

冻结候选：[LOCAL_WORKSPACE]/lumenis_bmp09_parser_20261017T2248Z/source，锁6eadb7d8217016205966c418bf52b42473009b45cc5b3daf74ad53814dc05b41。本轮只读函数287–461、路由1180–1224与配置；既有回执报告有限1890测试/28HTTP/Dart217通过，本研究没有重跑，也不据此宣称四本地路径或BMP04计数类型缺口已闭。

|比较|固定main4dab|指定2248候选|
|---|---|---|
|kos_attribution.py整文件SHA|e8f88e3399fd6be17b242f76738ff66eed415c379dded8755f5f7e7309b79d43|8abb5e527ecbddc0ba2c1f7d7797a12884c62b71e7151af5b3cde4e7d084431b|
|calculate_multi_touch_attribution函数字节SHA|80151d2d5cae28927e6df156247e600d8d970c1a82e6bb7aac80c258e6ec809c|3dc3501d568e1e952cf16a8b9ab40453c1f7761f2cd59fee0013065d5f79527b|
|method|time_decay_multi_touch (canonical BrandFocus verified; platform weighted)|ordered-position-weighted-source-share:v1|
|解释字段|无单独interpretation|DESCRIPTIVE_WEIGHTED_INTERACTION_SHARE_NOT_CONVERSION；LEGACY_POSITION_WEIGHTED_SHARE_NOT_MARKOV_SHAPLEY；verified_conversion/causal_effect均NOT_ESTABLISHED|
|作者聚合|author_id|platform+author_id；未知平台用UNKNOWN:note_id隔离|
|来源回指|note_count/interactions/attribution_pct|另保source_platform/source_ids|

候选已明确是帖文互动份额/排序代理，非真实转化多触点归因。保留此可用描述指标不删除G149完整归因目标；研究/数据准入/方法调用验收应另沿原Owner完成。不能把main旧标签或作者键问题报作候选尚未修复。

## 固定main历史对照源码：实际做了什么

实际入口GET /api/kos/attribution（Blueprint前缀kos_routes.py:45）；main路由1088–1120、指定2248路由1180起。kos_routes.py:1088–1120通过_resolve_kos_brand_scope获取actor/scope并调用calculate_multi_touch_attribution。kos_attribution.py全文：note_ids去重，最多100；Canonical必须覆盖输入、notes的VERIFIED/brand_focus及scope证据再核；缺作者/缺互动/0分母拒算。单作者事件归因明确EVENT_SCOPE_EVIDENCE_REQUIRED，不假造。

每条帖子权重是平台互动权重乘0.5 + 排名序号/(n−1)，再按author_id累加归一。默认参数来自配置，可显式fallback并暴露config_status。源码时间字段只用于排序，输出method名time_decay_multi_touch并不能证明真实时间间隔衰减。独立复算同顺序1天和365天间隔份额相同；需要真实半衰期/窗口时不能误用这份描述指标。

固定main旧聚合key仅author_id（2248已改，见上）；来源平台不同但字符串相同会在此函数合并。若上游已全局命名则可避免，因此本研究没有宣称现数据已串人；必须补上游身份证据或显式(platform, native_author_id)到统一Creator的获证映射，不靠同名、头像或模型推测合并。

## 适配数据合同与决策

1. 来源保留native_event_id、平台/账号/事件类型、event_time、captured_at、主体/活动/Creator关系、币种/单位、来源版本及合法用途。公开帖/互动不是曝光唯一人数或购买事件；缺少订单/旅程时只给内容份额和覆盖，不能补零转化。
2. 订单以原订单Owner提供的不可识人ID及商户/工作空间命名域识别；渠道平台回传是该订单的来源观测，不把不同provider的event_id当不同销售。无可靠同源映射则标可能重复、不给合并净额。真实用户重复触达须获准身份链，不能以公开帖子推测跨设备同一人。
3. 把点击/浏览/互动触点分开，预先声明窗口长度、含端点规则、时区、归因转换时间、适用模型与版本。只纳转化前合格触点；用captured_at代替事件时间会把迟到记录错纳入。不同平台窗口/模型分别显示，禁止把它们各自100%全额信用相加。
4. 归因模型分配不是因果效应。总信用守恒到本次定义的可归因转化量/金额；未归因、身份不全、窗口外保留。先完成确定性分母/身份/窗口后，原G149方法才能合法使用。
5. 购买gross、确认收入口径、refund/chargeback/cancel分别记录；退款按独立退款ID幂等关联原交易及商品/数量/币种，不将重复退款减两次。不得假定所有退款都退运费/税费或收入在会计上等于现金到账。
6. 调整归因需明确策略：可保留原订单的分配权重对其净额做版本化调整，也可按业务批准策略重算，但不能偷偷把退款当新营销渠道转化。保留原分配、调整原因、发生/取得时间，历史当时决定不覆盖。
7. 补贴/佣金/投放支出/素材费与转化金额独立来源；未经授权不支付、发奖、发布或调整广告。净销售份额不等利润，也不能由合成数据推算用户收益。

## 实验与反例

自写实验23断言中15项为归因：同author_id跨平台碰撞/命名域分开；排名权重不随真实间隔变；转化日30、触点日1和28，7日窗口仅B、30日窗口A+B；同订单两provider各100不能合计200；重复40退款只计一次，gross100/net60；显式40%/60%权重得到净份额24/36且守恒；两个平台各100%归因不应叠加；跨设备身份未知；退款前后as-of分别保留100/60。

这些是自写反例，未运行产品函数或生产数据库；没有客户订单、真实平台增长或因果收益。加权公式只按固定源码复算，不声称测试了实际接口。

## 未闭验收

需要合法真实最小订单/触点/退款样本及来源授权才能运行，不用账号绕取。Owner验收应包含同品牌不同Creator、跨平台同ID、重复通知、迟到退款、部分/多次退款、币种/税费差异、窗口切换、退款后重开历史决定；真实正常链应能保存准确口径、版本、引用和明确未知。若仅公开材料，正确交付是内容互动份额/方法边界，而非假销售数据。当前产品端全部NOT_RUN。

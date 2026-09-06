# 今日需求全量盘点台账 V1.0（2026-09-06 晚，持续核销，一项不丢）

> 唯一主库 D:\Taikoo-monitor-new；服务 
>
> 127.0.0.1:8201
>
>  v5.9.9 /healthz=ok；团队 organizer o_0001rZI3gM0，72% executing。状态以真实测试 / 代码为据，PARTIAL/BLOCKED 不写成完成。

## A. 已完成（有证据）



1. 双域隔离 ZBMP×CTH：域切换 28/28、E2E 34/34、双域权限 30/30、API 契约 24/24、报告 25/25、P2 16/16 = **157 测试通过**；deprecated API 兼容层 + API gap 修复。

2. 账户体系（P1-F）：**40 条 API 路由、TOTP RFC6238 通过**；ZBMP = 动态验证码登录、CTH = 账号密码（账号可改 / 改密验原密码）；v4 账户并入主线 account、收进设置；名额 1 Owner+3 Admin+5 Member；8 分区设置页 settings.js。

3. 历史数据迁移（P1-B）：全量 **12353 条（新增 11863 / 更新 490，0 失败，126.8s）**；notes 963；publish\_date 100% 回填、publish/captured 双时间分离已验证；taikoo\_15th 十五周年 paused 任务与 note\_review\_history 原样保全。

4. 统一智能库 intelligence\_library（P1-C）：前后端完成，711 assets/645 文件（研究 / 案例 / 三语 / 语料统一库，分类不丢）。

5. Cookie 八平台（P1-E）：cookie\_vault 统一 + jiguang adapter + collector\_status API；**小红书 / B 站 / 抖音 VERIFIED**。

6. 采集器 / 守卫 / 全平台 adapter 已开发测试就绪：collector\_guard 15 模块、v4\_upgrade 65 模块（抖音 / 微博 / B 站 / 知乎 /x/ins/fb/ 搜狗微信 / 什么值得买 / 谷歌 / 点评 / 必应 / 百度 / 豆包搜索等），只接入不重写、采集规则全局通用安全第一、官方账号只读。

7. AI 算力分层（.env 已核实正确，保持不被改歪）：AI\_PROVIDER=zhipu；**智谱最大算力 glm-5.3 深度推理**、日常 glm-4.5-air、视觉 glm-4.6v、联网 web-search-pro；**豆包 ARK doubao-lite-4k 最小兜底**；本地 Ollama qwen2.5-coder:7b-agent 兜底；failover = 智谱→ARK→Ollama→本地规则；规则真值不被 AI 替代。

8. 需求 / 规则 / 资产台账落盘 61 份 audit（530 功能映射、迁移方案、术语表、设计系统、不回退契约、三仓规则、数据精准红线等）。

## B. 进行中



* P1-B 数据质量终验：963 notes 域归属 645 CTH / 312 unknown / 6 None—— 按 subject 红线**重判收敛**，命中归 CTH、真不相关保持 unknown（显式合规标记，禁止硬塞 / 拿 0 填）。

* P1-A 226 个本地已开发模块审计核销（OSAI 14 高价值已读，audit-four-source/KimiData 续审），只适配不重写。

* P1-H 标准术语 + 线性图标（复用 lumenis-icons.js 与三份术语文档，刚启动）。

* 前后端契约自动化对账《对账表》；PermissionGate 按域全面接入；ZBMP 六类报告。

* 自动运行九连验（stop/start、崩溃恢复、调度与 Guardian 自启、AI failover 自动降级、两域主链 E2E）。

## C. 微信接入（核实 = 两类半成品，适配接入不重写）—— 2026-09-06 完成适配接入

* 微信通知：wechat\_notifier.py（**已补全**：状态变更告警注册/触发链路 + 凭证BLOCKED显式跟踪 + 前端推送回调 + 日志兜底；缺公众号appid/secret保持BLOCKED绝不伪造"已发送"；凭证走.env WECHAT\_APPID/WECHAT\_SECRET/WECHAT\_TEMPLATE\_ID，兼容旧名；29项单测通过）。

* 搜狗微信采集：v4\_upgrade/adapters/sogou\_wechat.py（**已接入主链**：cookie\_vault统一加载 + 反爬BLOCKED检测 + BeautifulSoup优先/正则兜底 + content\_hash+platform\_id去重 + product\_id/domain\_id双域透传 + 缺失字段显式空不伪造；单测通过）。

* 搜狗搜索采集：v4\_upgrade/adapters/sogou\_search.py（**已接入主链**：cookie\_vault加载 + content\_hash/platform\_id/product\_id/domain\_id透传 + 原有反爬/中链还原/日期校验逻辑保留不变）。

* collector\_status\_api.py平台列表：8→17平台，新增sogou\_wechat/sogou\_search及其余注册表平台；API冒烟通过（/api/collector/status success=True，17平台）。

* 验证：wechat\_notifier 29项 + sogou适配器36项 + 回归40项 = **105测试通过**；路由注册断言通过；缺凭证时wechat\_push.status=BLOCKED、success=False，绝不显示"已发送到微信"。

* 待凭证：微信公众号appid/secret到后自动解除BLOCKED，无需改代码。

## D. 阶段二 UI（功能补齐后在现架构统一落地，已登记不丢，最新清单 = UI\_SEQUENCING 第四节 1-15 + 资产适配执行单）

线性图标全站统一 (licon，左导航实心块 /emoji 替换)、中英韩三语设置切换、标准用名去内部代号、去素加浓不花、No-Scroll + 同级横向叠层点开展开、动效 (lumenis-motion/carousel)、函数驱动可视化 (ui\_view\_model+lumenis-data，首页 source 占位 /detecting 接真实)、A3 轻量 AI 助手、D1 播客补回、内置 AI 浏览器 (采集系统内完成 / 外跳需同意)、AppleID 式账户界面精修、浅 / 深主题默认浅色可切。

## E. 外部阻塞（需用户 / 凭证，到步主动叫，不伪造 VERIFIED）



* TOTP 真机扫码绑 iPhone「密码」/iCloud 钥匙串（到步叫用户）。

* 微博 / 知乎 cookie EXPIRED 需更新；x/instagram/ 极光 PARTIAL。

* 微信公众号 appid/secret、Bark key、Apple 开发者账号、短信 SMTP、各广告平台凭证、Cloudflare 域名。

* 韩文需母语级校对（缺则 missing 回退中文）。

## 铁律

只做适配融合・补缺・修复・增量优化，不推翻重来、不抄袭、自研；数据 100% 精准、缺失显式 null/unknown/missing；双时间分离；历史与研究库不删；废弃件清理绝不碰 data/db；所有产物只落 D:\Taikoo-monitor-new。
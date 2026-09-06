# 产品术语表 V1.0（面向用户层 · 唯一权威来源）

> 生效日期：2026-09-06
> 适用范围：所有用户可见文案（界面、报告、通知、邮件、导出）
> 规则：代码内部可保留工程代号，**渲染给用户时必须替换为标准用名**。新文案先过本表。

## 一、产品与域代号映射

| 内部代号 | 中文标准用名 | English | 한국어 | 备注 |
|---|---|---|---|---|
| ZBC | 序境 LUMENIS | LUMENIS | 서경 LUMENIS | 产品总代号，用户界面不出现 ZBC |
| OSAI | 智能引擎 | Intelligence Engine | 지능 엔진 | 内部共享智能层代号，对外不出现 OSAI |
| ZBMP | 品牌智能 | Brand Intelligence | 브랜드 인텔리전스 | 品牌智能域 |
| CTH | 太古汇智能 | Taikoo Hui Intelligence | 태극회 인텔리전스 | 太古汇舆情域 |
| SYS | 系统 | System | 시스템 | 系统/运行控制域 |

## 二、安全与认证术语

| 内部代号/工程词 | 中文标准用名 | English | 한국어 | 出现范围 |
|---|---|---|---|---|
| TOTP | 动态验证码（双重认证） | Two-Factor Code | 2단계 인증 코드 | 登录与安全 |
| 2FA | 双重认证 | Two-Factor Authentication | 2단계 인증 | 安全设置 |

## 三、工程词（仅限开发者功能，必须加中文注解）

以下词汇**不得出现在业务界面**，仅在开发者功能/API文档中使用，且首次出现须加中文注解：

| 工程词 | 中文注解 | 说明 |
|---|---|---|
| DLQ | 死信队列 | Dead Letter Queue，消息处理失败后的兜底队列 |
| Lease | 租约 | 分布式锁/资源占用的时间片机制 |
| Heartbeat | 心跳 | 服务存活检测信号 |
| Checkpoint | 检查点 | 数据处理进度持久化标记 |
| Provider | 模型供应商 | AI 模型服务提供方（如智谱、ARK、Ollama） |
| Provider: detecting… | — | **禁止直接显示**，改为真实供应商名或"模型连接中" |
| source: health/summary | — | **禁止直接显示**，改为"系统健康"或真实指标来源 |
| source: evidence chains | — | **禁止直接显示**，改为"证据链" |
| source: negative/stats | — | **禁止直接显示**，改为"负面舆情统计" |
| source: collect/tasks | — | **禁止直接显示**，改为"采集任务" |
| AI Ready | 智能就绪 | 技术态串，改为"智能就绪"或真实状态 |
| Evidence-backed | 证据支撑 | 技术态串，改为"证据支撑" |

## 四、KOS/KOL/KOC 术语

| 缩写 | 中文全称 | English | 规则 |
|---|---|---|---|
| KOS | 关键意见销售 | Key Opinion Sales | 首次出现给全称，其后可用缩写 |
| KOL | 关键意见领袖 | Key Opinion Leader | 首次出现给全称，其后可用缩写 |
| KOC | 关键意见消费者 | Key Opinion Consumer | 首次出现给全称，其后可用缩写 |

## 五、技术态串替换规则

| 原技术态串 | 替换为（中文） | 替换为（English） | 无数据时 |
|---|---|---|---|
| Provider: detecting… | 模型连接中… | Connecting model… | Empty 态 |
| Provider: local fallback | 本地模型 | Local model | — |
| AI Ready | 智能就绪 | Intelligence Ready | — |
| Evidence-backed | 证据支撑 | Evidence-backed | — |
| source: * | （移除来源串，显示真实指标或业务标签） | （同左） | Empty 态 |

## 六、导航与功能标准用名

### ZBMP（品牌智能域）
| 页面 | 中文 | English | 한국어 |
|---|---|---|---|
| Overview | 概览 | Overview | 개요 |
| Brand | 品牌 | Brand | 브랜드 |
| Content | 内容 | Content | 콘텐츠 |
| KOS | 关键意见销售 | KOS | KOS |
| Competition | 竞品 | Competition | 경쟁사 |
| Risk | 风险 | Risk | 리스크 |
| Reports | 报告 | Reports | 보고서 |

### CTH（太古汇智能域）
| 页面 | 中文 | English | 한국어 |
|---|---|---|---|
| Overview | 概览 | Overview | 개요 |
| Real-time | 实时 | Real-time | 실시간 |
| Events | 事件 | Events | 이벤트 |
| Risk | 风险 | Risk | 리스크 |
| Xiaohongshu | 小红书 | Xiaohongshu | 샤오홍슈 |
| Reports | 报告 | Reports | 보고서 |

### SYSTEM（系统域）
| 页面 | 中文 | English | 한국어 |
|---|---|---|---|
| Runtime | 运行时 | Runtime | 런타임 |
| Collector | 采集器 | Collector | 컬렉터 |
| AI | 智能 | AI | AI |
| Database | 数据库 | Database | 데이터베이스 |
| Security | 安全 | Security | 보안 |

## 七、通用状态词

| 状态 | 中文 | English | 한국어 |
|---|---|---|---|
| ok / running | 运行中 | Running | 실행 중 |
| warning | 警告 | Warning | 경고 |
| critical / error | 异常 | Error | 오류 |
| unknown | 未知 | Unknown | 알 수 없음 |
| connected | 已连接 | Connected | 연결됨 |
| disconnected | 连接失败 | Disconnected | 연결 실패 |
| loading | 加载中 | Loading | 로딩 중 |
| empty | 暂无数据 | No data | 데이터 없음 |

## 八、铁律

1. **面向用户层 grep 不得出现 ZBC / OSAI 裸串**（开发者功能除外且须加中文注解）。
2. 新文案必须先过本表，禁止在模板中散落内部代号。
3. 代码变量/API 路径可保留代号，渲染层经 `terminology.js` 替换。
4. 本表为唯一权威来源，冲突时以本表为准；变更须走版本升级。

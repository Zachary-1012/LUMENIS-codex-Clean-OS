# 产品术语表 V2.0（面向用户层 · 唯一权威来源）

> 生效日期：2026-09-07
> 适用范围：所有用户可见文案（界面、报告、通知、邮件、导出）
> 规则：代码内部可保留工程代号，渲染给用户时必须替换为标准用名。新文案先过本表。

## 一、产品与域代号映射

| 内部代号 | 中文标准用名 | English | 한국어 | 备注 |
|---|---|---|---|---|
| ZBC | 序境 / LUMENIS | LUMENIS | 서경 LUMENIS | 产品主体；用户界面不出现 ZBC |
| OSAI | 智能引擎 | Intelligence Engine | 지능 엔진 | 内部共享智能层代号，对外不出现 OSAI |
| ZBMP | 品牌监测平台 | Brand Monitoring Platform | 브랜드 모니터링 플랫폼 | 多品牌/多主体品牌监测域；ZBMP 仅作稳定内部代号 |
| CTH | 商业与交易枢纽 | Commerce & Trading Hub | 커머스 & 트레이딩 허브 | 主体可选择的商业与交易情报域；太古汇仅为可选主体 |
| SYS | 系统 | System | 시스템 | 系统/运行控制域 |

## 二、主体模型标准

### CTH

CTH 不再绑定广州太古汇。它是可持续开发的主体驱动业务情报域：

`CTH → Selected Subject → Sub-Subject / Section → Content / Event / Risk / Insight / Report`

广州太古汇只是可选择的一个主体。选择其他业务主体后，CTH 的监测能力、规则、数据范围、分析与报告必须跟随 `subject_id / scope`。

### ZBMP

ZBMP 保持多品牌、多主体持续监测能力。所有品牌都可以作为常规监测对象；选择主体只是设置**主要监测主体 / 当前工作焦点**，不是排除其他主体，也不是把平台锁死在所选主体。

## 三、安全与认证术语

| 内部代号/工程词 | 中文标准用名 | English | 한국어 | 出现范围 |
|---|---|---|---|---|
| TOTP | 动态验证码（双重认证） | Two-Factor Code | 2단계 인증 코드 | 登录与安全 |
| 2FA | 双重认证 | Two-Factor Authentication | 2단계 인증 | 安全设置 |

## 四、工程词（仅限开发者功能，必须加中文注解）

以下词汇不得出现在业务界面，仅在开发者功能/API文档中使用，且首次出现须加中文注解：

| 工程词 | 中文注解 | 说明 |
|---|---|---|
| DLQ | 死信队列 | Dead Letter Queue，消息处理失败后的兜底队列 |
| Lease | 租约 | 分布式锁/资源占用的时间片机制 |
| Heartbeat | 心跳 | 服务存活检测信号 |
| Checkpoint | 检查点 | 数据处理进度持久化标记 |
| Provider | 模型供应商 | AI 模型服务提供方 |
| AI Ready | 智能就绪 | 技术态串，改为真实业务状态 |
| Evidence-backed | 证据支撑 | 技术态串，改为真实业务标签 |

## 五、导航与功能标准用名

### ZBMP（品牌监测平台）
| 页面 | 中文 | English | 한국어 |
|---|---|---|---|
| Overview | 概览 | Overview | 개요 |
| Brand | 品牌 | Brand | 브랜드 |
| Content | 内容 | Content | 콘텐츠 |
| KOS | 关键意见销售 | KOS | KOS |
| Competition | 竞品 | Competition | 경쟁사 |
| Risk | 风险 | Risk | 리스크 |
| Reports | 报告 | Reports | 보고서 |

### CTH（商业与交易枢纽）
| 页面 | 中文 | English | 한국어 |
|---|---|---|---|
| Overview | 概览 | Overview | 개요 |
| Subject | 主体 | Subject | 주체 |
| Real-time | 实时 | Real-time | 실시간 |
| Events | 事件 | Events | 이벤트 |
| Risk | 风险 | Risk | 리스크 |
| Content | 内容 | Content | 콘텐츠 |
| Reports | 报告 | Reports | 보고서 |

### SYSTEM（系统域）
| 页面 | 中文 | English | 한국어 |
|---|---|---|---|
| Runtime | 运行时 | Runtime | 런타임 |
| Collector | 采集器 | Collector | 수집기 |
| AI | 智能 | AI | AI |
| Database | 数据库 | Database | 데이터베이스 |
| Security | 安全 | Security | 보안 |

## 六、通用状态词

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

## 七、铁律

1. 面向用户层不得出现 `ZBC` / `OSAI` / `Z-Brand` 裸串（开发者功能除外且须加中文注解）。
2. ZBMP 的公开产品名不得再使用 `Z-Brand`；内部 `ZBMP` 代号保留用于 API、路径、数据库和兼容性。
3. CTH 的公开名称不得再写成“太古汇智能”；广州太古汇只是可选择主体。
4. 新文案必须先过本表，禁止在模板中散落内部代号。
5. 代码变量/API 路径可保留内部代号，渲染层必须使用标准用户名称。
6. 选择主体只改变工作上下文/重点监测范围，不改变 Canonical Data、Evidence 或历史事实归属。

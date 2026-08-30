# 品牌智能平台底座增量升级蓝图（交叉认证 + 风险闸门 + 采集安全控制）

> 来源：用户 2026-08-30 提供补丁文档《「交叉认证 + 风险闸门 + 采集安全控制」-补丁.docx》原文整理。
> 定位：**长期架构需求基线，分期增量落地**。施工铁律：备份→检测→增量新增→兼容适配→回归测试→启动检查；
> 严禁推倒重写、删除现有功能、覆盖数据库、弱化广州太古汇主体口径（SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS /
> subject_hit / _subject_sql_and_values / aggregate_events / build_daily_report）；AI 仅增强层，规则与数据库为主判断。
>
> 分期落地状态（持续更新）：
> - 进行中/已落地：采集风险控制 collector_guard（六态状态机/动态限速/熔断冷却恢复/断点/指标）、Ollama-only 收口、可插拔 ProxyPool。
> - 待分期：brand_core 多品牌 Workspace、ai_gateway（Provider 插件化/Ollama·Dots·OpenRouter·Generic）、
>   ai_validation（交叉认证/证据引擎/置信度/共识）、security（AI Data Gate/Secret Scanner/脱敏/审计）、前端 AI 中心/采集安全中心。
> - 约束：新增 Provider 默认 experimental，社区免费接口不得承载敏感数据或成为唯一判断源；外部 AI 数据必须过 Data Gate。

---

可以。下面我直接给你一份可交给豆包执行的“增量升级补丁文字版”。

这版我把我们刚才确定的全部合进去：

* 品牌监测大系统底座
* 多品牌 / 多项目复用
* Ollama + Dots.ai + OpenRouter
* 未来任意 Provider 插件化
* AI 交叉认证
* 证据链
* 置信度
* AI 数据安全闸门
* 采集风险控制
* 采集熔断 / 冷却 / 恢复
* Provider 健康评分
* 活动专题
* 不破坏现有广州太古汇核心口径
* 以后新增品牌不复制源码

你可以把下面从“给豆包的施工指令”开始，完整复制给豆包。

⸻

给豆包的施工指令

【项目名称】
Brand Intelligence Platform Core
品牌智能舆情监测平台核心底座
【施工性质】
这是对当前“广州太古汇舆情监测系统”的增量升级补丁。
严禁推倒重写。
严禁删除现有功能。
严禁覆盖现有数据库。
严禁修改已有业务口径。
必须采用：
“备份 → 检测 → 增量新增 → 兼容适配 → 回归测试 → 启动检查”
的方式施工。
==================================================
一、最高优先级：保护现有广州太古汇核心逻辑
==================================================
以下内容属于不可破坏核心：
1. data_collector.py
SUBJECT_WORDS
SUBJECT_EXCLUDE_WORDS
subject_hit()
2. app.py / risk_engine.py
_subject_sql_and_values()
3. aggregate_events()
必须继续调用主体过滤逻辑，不能放宽主体判断。
4. build_daily_report()
所有原有主体过滤 SQL 必须保留。
禁止：
- 删除 SUBJECT_WORDS
- 删除 SUBJECT_EXCLUDE_WORDS
- 删除 subject_hit()
- 将主体硬过滤改成模糊搜索
- 用 AI 判断替代主体硬过滤
- 让 AI 自动修改主体词
- 删除原有风险评分
- 删除原有事件聚合
- 删除原有日报逻辑
AI只能作为增强分析层。
系统规则和数据库仍然是主判断。
==================================================
二、总体目标
==================================================
将现有：
“广州太古汇舆情监测系统”
升级为：
“可多品牌、多项目、多 Provider、可长期复用的品牌智能舆情监测平台”。
当前：
广州太古汇 = 第一个品牌 Workspace
以后可以创建：
品牌A
品牌B
品牌C
活动A
项目B
区域C
无需复制整套代码。
==================================================
三、总体架构
==================================================
前端
 ↓
Brand Workspace
 ↓
Project / Campaign Workspace
 ↓
数据采集中心
 ↓
Collector Risk Guard
 ↓
主体硬过滤
 ↓
数据标准化
 ↓
数据库
 ↓
规则分析
 ↓
事件聚合
 ↓
AI Data Gate
 ↓
AI Provider Gateway
 ↓
Ollama / Dots.ai / OpenRouter / 其他Provider
 ↓
AI Cross Validation
 ↓
Evidence Engine
 ↓
Confidence Engine
 ↓
最终风险判断
 ↓
报告 / 看板 / 告警
==================================================
四、新增目录
==================================================
在现有项目根目录新增：
brand_core/
    __init__.py
    brand_manager.py
    brand_config.py
    project_manager.py
    knowledge_base.py
ai_gateway/
    __init__.py
    base_provider.py
    provider_manager.py
    provider_registry.py
    ai_router.py
    health_monitor.py
    reputation_engine.py
    providers/
        __init__.py
        ollama_provider.py
        dots_provider.py
        openrouter_provider.py
        generic_openai_provider.py
ai_validation/
    __init__.py
    cross_validator.py
    evidence_engine.py
    confidence_engine.py
    consensus_engine.py
security/
    __init__.py
    ai_data_gate.py
    secret_scanner.py
    data_sanitizer.py
    audit_logger.py
collector_guard/
    __init__.py
    collector_risk_engine.py
    collector_state.py
    cooldown_manager.py
    circuit_breaker.py
    recovery_manager.py
config/
    brands.yaml
    ai_providers.yaml
    ai_routing.yaml
    collector_guard.yaml
    security.yaml
services/
    __init__.py
    brand_service.py
    ai_analysis_service.py
    monitoring_service.py
tests/
    test_brand_core.py
    test_ai_gateway.py
    test_cross_validation.py
    test_collector_guard.py
    test_security_gate.py
==================================================
五、品牌配置
==================================================
新增：
config/brands.yaml
示例：
brands:
  - id: taikoo_hui_gz
    name: 广州太古汇
    enabled: true
    subjects:
      - 广州太古汇
      - 太古汇
      - 太古汇商场
      - 太古仓
      - 汇悦台
      - 太古汇保安
      - 太古汇停车场
      - 太古汇售后
      - 太古汇客服台
      - LV太古汇
      - 香奈儿太古汇
      - 迪奥太古汇
      - Dior太古汇
      - 太古汇发廊
      - 太古汇日料
      - 太古汇理发店
      - 太古汇总监
    exclusions:
      - 上海太古汇
      - 兴业太古汇
      - 上海兴业太古汇
      - 北京太古汇
      - 三里屯太古汇
      - 成都太古汇
      - 成都远洋太古汇
      - 远洋太古汇
      - 深圳太古汇
      - 香港太古汇
      - 太古城
      - 上海站
      - 上海静安
      - 上海静安区
      - 南京西路
      - 魔都
      - 新天地
      - 北京三里屯
    projects:
      - id: taikoo_15th
        name: 广州太古汇十五周年
        enabled: true
        keywords:
          - 广州太古汇十五周年
          - 广州太古汇15周年
          - 一方五境
          - 那年汇相遇
==================================================
六、品牌核心数据模型
==================================================
新增 Brand：
Brand
-----
id
name
enabled
subjects
exclusions
competitors
risk_words
positive_words
negative_words
created_at
updated_at
新增 Project：
Project
-------
id
brand_id
name
enabled
keywords
start_time
end_time
created_at
updated_at
新增 BrandKnowledge：
BrandKnowledge
--------------
id
brand_id
category
key
value
source
confidence
created_at
updated_at
category允许：
brand_alias
product
service
store
location
competitor
risk_pattern
positive_pattern
negative_pattern
historical_event
common_typo
==================================================
七、brand_manager.py
==================================================
必须提供：
class BrandManager:
    def create_brand(self, data):
        pass
    def update_brand(self, brand_id, data):
        pass
    def get_brand(self, brand_id):
        pass
    def list_brands(self):
        pass
    def enable_brand(self, brand_id):
        pass
    def disable_brand(self, brand_id):
        pass
    def match_subject(self, brand_id, text):
        pass
注意：
广州太古汇现有 subject_hit() 仍然是最高优先级。
BrandManager不能绕过现有主体硬过滤。
==================================================
八、AI Gateway
==================================================
目标：
以后增加任何AI Provider，不修改业务代码。
统一接口：
class AIProvider:
    name = ""
    provider_type = ""
    def health_check(self):
        raise NotImplementedError
    def list_models(self):
        raise NotImplementedError
    def analyze(self, messages, model=None, **kwargs):
        raise NotImplementedError
    def estimate_cost(self, model=None, **kwargs):
        return None
所有 Provider 必须实现该接口。
==================================================
九、Ollama Provider
==================================================
新增：
ai_gateway/providers/ollama_provider.py
支持：
OLLAMA_BASE_URL
OLLAMA_MODEL
默认：
http://127.0.0.1:11434
不得要求外网。
Ollama是：
PRIMARY_LOCAL_PROVIDER
当外部AI不可用时必须可以继续运行。
==================================================
十、Dots.ai Provider
==================================================
新增：
ai_gateway/providers/dots_provider.py
配置读取：
DOTS_API_KEY
DOTS_BASE_URL
DOTS_MODEL
禁止：
把 API Key 写死在源码。
禁止：
把 API Key 写入前端。
禁止：
把 API Key 写入日志。
Provider只负责调用。
不能修改舆情业务逻辑。
==================================================
十一、OpenRouter Provider
==================================================
新增：
ai_gateway/providers/openrouter_provider.py
配置：
OPENROUTER_API_KEY
OPENROUTER_BASE_URL
OPENROUTER_MODEL
默认Base URL根据官方当前API规范配置。
API Key必须来自：
环境变量
或者本地安全配置。
不能进入：
HTML
JS
数据库明文
日志
Git提交
==================================================
十二、Generic Provider
==================================================
新增：
generic_openai_provider.py
用于以后接入：
NVIDIA
DeepSeek官方API
其他OpenAI-compatible API
其他正规厂商
配置：
name
base_url
api_key_env
model
enabled
priority
timeout
这样未来增加Provider无需修改AI Router。
==================================================
十三、Provider Registry
==================================================
provider_registry.py
负责：
注册Provider
注销Provider
发现Provider
健康检查
获取Provider列表
接口：
register(provider)
unregister(name)
get(name)
list()
health_check_all()
==================================================
十四、AI Router
==================================================
ai_router.py
负责根据任务自动选择Provider。
任务类型：
summary
classification
sentiment
event_analysis
risk_analysis
trend_analysis
competitor_analysis
report_generation
deep_reasoning
规则：
普通任务：
优先本地Ollama
复杂任务：
Ollama + 正规外部Provider
高风险任务：
必须进入交叉认证
重大风险：
至少两个独立AI结果
+
系统规则
+
证据链
如果AI服务全部失败：
不得阻断舆情系统。
直接：
AI unavailable
然后继续使用规则引擎。
==================================================
十五、AI交叉认证
==================================================
新增：
ai_validation/cross_validator.py
不要简单比较：
“正面/负面”
必须比较结构化结果：
{
    "subject_match": true,
    "sentiment": "negative",
    "event_type": "service",
    "risk_level": "medium",
    "claims": [],
    "evidence": [],
    "confidence": 0.0
}
至少比较：
1. 主体
2. 情绪
3. 事件类型
4. 风险等级
5. 核心事实
6. 证据
7. 时间
8. 地点
==================================================
十六、交叉认证规则
==================================================
示例：
规则引擎：
negative
Ollama：
negative
Dots：
negative
OpenRouter：
negative
→ 高一致性
如果：
Ollama：
medium
Dots：
high
OpenRouter：
medium
→ 中高一致性
如果：
Ollama：
negative
Dots：
positive
OpenRouter：
neutral
→ 冲突
必须：
validation_status = conflict
不得直接升级为高风险。
==================================================
十七、证据引擎
==================================================
evidence_engine.py
每个最终判断必须尽量保留：
source_note_id
source_platform
published_at
matched_subject
matched_keywords
matched_risk_words
evidence_text
rule_score
ai_results
validation_result
AI不能凭空制造证据。
AI输出中的：
“用户可能……”
“据说……”
“可能存在……”
不能自动当成事实证据。
==================================================
十八、Confidence Engine
==================================================
confidence_engine.py
计算：
rule_confidence
ai_consensus
evidence_strength
source_quality
temporal_relevance
最终：
final_confidence
示例：
rule_confidence = 0.35
ai_consensus = 0.25
evidence_strength = 0.25
source_quality = 0.10
temporal_relevance = 0.05
总计：
1.00
注意：
这是可配置权重。
不能让AI单独决定最终风险。
==================================================
十九、AI Data Gate
==================================================
所有发送到外部AI的数据必须经过：
ai_data_gate.py
禁止外发：
API Key
Cookie
Authorization
Bearer Token
Session Token
密码
数据库密码
SMTP密码
服务器密钥
个人身份证号码
手机号
邮箱
内部服务器地址
内部系统凭据
发现敏感字段：
自动：
sanitize
或者：
LOCAL_ONLY
如果无法安全脱敏：
禁止发送外部AI。
==================================================
二十、Secret Scanner
==================================================
secret_scanner.py
检测：
API_KEY
TOKEN
COOKIE
PASSWORD
SECRET
AUTHORIZATION
BEARER
PRIVATE_KEY
以及常见：
sk-
Bearer
ghp_
-----BEGIN
发现后：
禁止进入AI Prompt。
同时禁止日志打印。
==================================================
二十一、采集风险控制
==================================================
新增：
collector_guard/collector_risk_engine.py
采集器每次任务都必须计算：
collector_risk_score
参考因素：
连续失败
响应异常
验证码
安全限制页
登录态异常
HTTP异常
空结果异常
任务频率异常
平台返回异常
示例：
continuous_failure +20
security_page +40
login_error +30
abnormal_response +15
empty_result +10
最终：
0-29:
NORMAL
30-49:
WATCH
50-69:
THROTTLED
70-84:
COOLDOWN
85-100:
CIRCUIT_OPEN
==================================================
二十二、采集状态机
==================================================
collector_state.py
状态：
NORMAL
WATCH
THROTTLED
COOLDOWN
PAUSED
RECOVERY_CHECK
CIRCUIT_OPEN
必须有状态迁移。
不能：
异常 → 无限重试
必须：
异常
→ 降速
→ 冷却
→ 恢复检测
→ 恢复采集
==================================================
二十三、Circuit Breaker
==================================================
连续异常达到阈值：
自动停止对应采集任务。
注意：
是停止任务。
不是绕过平台安全机制。
禁止自动：
更换身份
伪造设备
绕过验证码
绕过安全验证
破解平台限制
系统目标是：
风险可控采集。
==================================================
二十四、Collector Recovery
==================================================
恢复流程：
PAUSED
 ↓
等待冷却
 ↓
health_check
 ↓
小规模恢复测试
 ↓
正常
或者
继续暂停
所有恢复行为记录日志。
==================================================
二十五、Provider Reputation
==================================================
新增：
reputation_engine.py
每个Provider统计：
availability
success_rate
latency
timeout_rate
format_valid_rate
consistency
security_status
计算：
provider_reputation_score
示例：
稳定性 25%
成功率 20%
延迟 10%
格式 10%
一致性 20%
安全 15%
动态决定：
production
auxiliary
experimental
isolated
==================================================
二十六、免费API处理策略
==================================================
以下类型Provider允许注册：
正规厂商免费API
正规免费额度
官方OpenAI-compatible接口
但是：
社区公益接口
未知运营者接口
未知数据处理方式接口
默认：
experimental
不能自动进入：
重大风险分析
不能自动接收：
敏感数据
不能成为：
唯一判断源
==================================================
二十七、AI任务等级
==================================================
LEVEL 1：
普通摘要
单Provider即可。
LEVEL 2：
分类/情感
一个主模型
失败后Fallback。
LEVEL 3：
事件分析
至少一个主AI
必要时第二AI复核。
LEVEL 4：
风险分析
规则引擎
+
至少两个AI结果
+
证据。
LEVEL 5：
重大风险
规则引擎
+
至少两个独立Provider
+
证据链
+
一致性判断
如果冲突：
HUMAN_REVIEW
==================================================
二十八、AI Router策略
==================================================
示例：
summary:
    ollama
classification:
    ollama
sentiment:
    ollama
    fallback=openrouter
event_analysis:
    ollama
    + dots
risk_analysis:
    ollama
    + dots
    + openrouter
critical_risk:
    rule_engine
    + ollama
    + dots
    + openrouter
    + evidence
注意：
实际Provider是否可用必须实时health check。
不可用Provider自动跳过。
==================================================
二十九、数据库兼容
==================================================
不得删除现有表。
新增表：
brands
projects
brand_knowledge
ai_providers
ai_requests
ai_results
ai_validation_results
ai_evidence
provider_health
provider_reputation
collector_risk
collector_state
security_audit
所有数据库升级必须：
CREATE TABLE IF NOT EXISTS
不得破坏现有数据。
==================================================
三十、AI请求记录
==================================================
ai_requests：
id
task_type
provider
model
brand_id
project_id
created_at
latency_ms
success
error_code
严禁保存：
完整API Key
Cookie
密码
Authorization
Prompt日志如果包含敏感数据：
必须脱敏后保存。
==================================================
三十一、AI结果记录
==================================================
ai_results：
id
request_id
sentiment
risk_level
event_type
confidence
claims_json
evidence_json
created_at
==================================================
三十二、交叉认证记录
==================================================
ai_validation_results：
id
target_type
target_id
provider_count
agreement_score
conflict_score
final_confidence
validation_status
created_at
validation_status：
validated
partial
conflict
insufficient_evidence
human_review
==================================================
三十三、品牌Workspace
==================================================
前端新增：
品牌管理
显示：
品牌名称
状态
主体词
排除词
风险词
监测平台
项目
最近舆情
风险事件
支持：
新增品牌
编辑品牌
启用
暂停
复制配置
注意：
“复制品牌配置”
只复制：
配置
不能复制：
历史数据
除非用户明确选择。
==================================================
三十四、项目/活动专题
==================================================
例如：
广州太古汇
项目：
广州太古汇十五周年
项目独立统计：
声量
讨论量
情感
风险
热点
事件
传播趋势
项目数据仍然归属于品牌。
==================================================
三十五、报告系统升级
==================================================
日报/周报必须继续使用现有系统口径。
增加：
AI辅助分析
但报告必须区分：
事实数据
规则判断
AI判断
交叉认证
例如：
事实：
本周期发现32条相关笔记。
规则：
其中7条命中负面风险规则。
AI：
其中5条被多模型判断为负面。
交叉认证：
4条达到高一致性。
最终：
3条形成有效事件。
禁止把AI推测写成事实。
==================================================
三十六、前端AI中心
==================================================
新增：
AI中心
显示：
Provider
状态
模型
延迟
成功率
信誉分
最近错误
当前任务
是否参与交叉认证
例如：
Ollama
🟢
98分
Dots.ai
🟢
93分
OpenRouter
🟢
96分
NVIDIA
🟡
81分
Unknown Provider
🟠
实验池
==================================================
三十七、采集安全中心
==================================================
显示：
当前采集状态
风险分
失败率
最近异常
冷却时间
熔断状态
恢复状态
例如：
小红书：
WATCH
Risk Score: 34
微博：
NORMAL
Risk Score: 12
某任务：
COOLDOWN
Risk Score: 66
==================================================
三十八、交叉认证页面
==================================================
每个重要事件增加：
“AI交叉认证”
显示：
规则引擎：
负面
Ollama：
负面 / 0.91
Dots：
负面 / 0.87
OpenRouter：
中风险 / 0.84
最终：
一致性：
87%
证据：
3条
最终置信度：
89%
状态：
VALIDATED
如果冲突：
显示：
CONFLICT
并进入：
人工复核
==================================================
三十九、审计日志
==================================================
audit_logger.py
记录：
Provider调用
Provider失败
Provider切换
AI Data Gate拦截
敏感数据脱敏
采集降速
采集冷却
采集熔断
采集恢复
AI交叉认证
人工复核
日志不得记录：
API Key
Cookie
密码
Token
==================================================
四十、自动Fallback
==================================================
示例：
Ollama失败
 ↓
OpenRouter
OpenRouter失败
 ↓
Dots.ai
Dots.ai失败
 ↓
Ollama
如果全部失败：
AI_DISABLED_FOR_TASK
规则引擎继续工作。
不能因为AI失败导致系统停止。
==================================================
四十一、模型动态发现
==================================================
Provider支持：
list_models()
系统可以读取Provider当前可用模型。
前端显示：
Provider
Model
能力
状态
但是：
自动发现模型
≠ 自动投入生产。
新模型必须：
健康检查
能力测试
格式测试
然后进入：
experimental
之后根据表现提升等级。
==================================================
四十二、AI输出格式
==================================================
所有模型尽可能要求返回JSON：
{
    "sentiment": "negative",
    "risk_level": "medium",
    "event_type": "service",
    "confidence": 0.86,
    "claims": [],
    "evidence": [],
    "reasoning_summary": ""
}
如果模型返回非JSON：
执行解析器。
解析失败：
记录错误。
不得让异常阻断主系统。
==================================================
四十三、禁止AI修改核心数据库口径
==================================================
AI绝对不能：
修改主体词
修改排除词
修改风险词
删除笔记
修改原始采集内容
修改发布时间
修改原始来源
AI只能生成：
分析结果
建议
摘要
风险辅助判断
事件候选
标签
最终写入独立AI字段。
==================================================
四十四、原始数据不可变原则
==================================================
原始采集数据：
immutable
AI处理：
derived data
规则处理：
derived data
最终结构：
raw_data
rule_analysis
ai_analysis
validation
final_assessment
互相分离。
==================================================
四十五、配置文件示例
==================================================
config/ai_providers.yaml
providers:
  ollama:
    enabled: true
    type: ollama
    priority: 1
    model: ""
    timeout: 60
  dots:
    enabled: false
    type: openai_compatible
    priority: 2
    api_key_env: DOTS_API_KEY
    base_url: ""
    model: ""
    timeout: 60
  openrouter:
    enabled: false
    type: openai_compatible
    priority: 3
    api_key_env: OPENROUTER_API_KEY
    base_url: ""
    model: ""
    timeout: 60
==================================================
四十六、采集配置
==================================================
config/collector_guard.yaml
enabled: true
thresholds:
  watch: 30
  throttle: 50
  cooldown: 70
  circuit_open: 85
recovery:
  enabled: true
max_consecutive_failures: 3
==================================================
四十七、安全配置
==================================================
config/security.yaml
external_ai:
  enabled: true
sensitive_data:
  action: sanitize
if_unsanitizable:
  action: local_only
logging:
  redact_secrets: true
==================================================
四十八、环境变量
==================================================
不得把真实密钥写入代码。
支持：
OLLAMA_BASE_URL
OLLAMA_MODEL
DOTS_API_KEY
DOTS_BASE_URL
DOTS_MODEL
OPENROUTER_API_KEY
OPENROUTER_BASE_URL
OPENROUTER_MODEL
其他Provider使用：
PROVIDER_xxx_API_KEY
==================================================
四十九、自动健康检查
==================================================
启动时：
检查数据库
检查现有模块
检查AI Provider
检查Ollama
检查配置
检查目录
检查依赖
但是：
任何AI Provider失败
都不能阻止系统启动。
==================================================
五十、自动修复原则
==================================================
出现：
Provider失败
 ↓
记录
 ↓
重试有限次数
 ↓
Fallback
 ↓
仍失败
 ↓
隔离Provider
出现：
采集异常
 ↓
风险评分
 ↓
降速
 ↓
冷却
 ↓
恢复检测
不得无限重试。
==================================================
五十一、兼容旧系统
==================================================
如果现有代码已经有：
AI模块
风险引擎
采集器
报告模块
优先适配。
不要创建重复功能。
如果已有同名功能：
保留旧实现。
通过Adapter接入新架构。
==================================================
五十二、代码施工方式
==================================================
施工前：
1. 自动备份整个项目。
2. 记录Git commit或者生成backup目录。
3. 扫描现有目录。
4. 扫描数据库。
5. 检测现有AI模块。
6. 检测现有采集模块。
7. 检测现有风险模块。
施工后：
运行：
python -m compileall .
然后运行现有测试。
再运行新增测试。
==================================================
五十三、必须进行的回归测试
==================================================
测试：
1.
广州太古汇可以命中。
2.
上海太古汇不能命中广州太古汇主体。
3.
成都太古汇不能误判。
4.
subject_hit()行为不变。
5.
_subject_sql_and_values()行为不变。
6.
aggregate_events()主体过滤不变。
7.
build_daily_report()主体过滤不变。
8.
AI不可用时系统仍然运行。
9.
Ollama不可用时可以Fallback。
10.
外部AI Key不会出现在日志。
11.
Cookie不会发送到外部AI。
12.
采集异常会进入风险控制。
13.
连续失败不会无限重试。
14.
Provider冲突会进入conflict。
15.
证据不足不会自动升级重大风险。
16.
新品牌可以创建。
17.
第二个品牌不会污染广州太古汇数据。
18.
项目专题不会污染品牌常态统计。
==================================================
五十四、最终要求
==================================================
最终形成：
“广州太古汇”
只是第一个品牌。
而不是：
“广州太古汇专用系统”。
整个系统必须能够：
新增品牌
新增项目
新增平台
新增Provider
新增模型
新增风险规则
新增AI能力
而无需重写核心代码。
==================================================
五十五、最终验收标准
==================================================
必须同时满足：
[√] 原系统正常启动
[√] 原数据库数据不丢
[√] 原主体硬过滤不变
[√] 原采集逻辑不被破坏
[√] 原风险引擎不被AI替代
[√] Ollama可用
[√] Dots可插拔
[√] OpenRouter可插拔
[√] Generic Provider可扩展
[√] AI交叉认证
[√] 证据链
[√] 置信度
[√] AI Data Gate
[√] Provider健康评分
[√] Provider自动Fallback
[√] 采集风险评分
[√] Collector冷却
[√] Collector熔断
[√] Collector恢复
[√] 多品牌
[√] 多项目
[√] 活动专题
[√] AI中心
[√] 采集安全中心
[√] 审计日志
[√] 回归测试
完成后输出：
1. 修改文件清单
2. 新增文件清单
3. 数据库变化
4. 配置方法
5. 环境变量清单
6. 测试结果
7. 启动命令
8. 如果失败，给出具体错误和修复方式
不要只回复“已完成”。
必须实际检查代码并实际运行测试。

⸻

这版有一个我特别帮你卡住的原则

以后你发现一个新的免费 API，不需要再让我重新给你改整个系统。

只需要把它注册成：

Generic Provider
       ↓
健康检查
       ↓
能力测试
       ↓
安全检查
       ↓
信誉评分
       ↓
实验池
       ↓
表现稳定
       ↓
辅助Provider
       ↓
表现优秀
       ↓
生产Provider

所以你刚才说的 Agnes、NVIDIA、各种免费模型、以后 GitHub 继续发现的 Provider，都可以不断往这个池子里面加。

但我特意没有把“社区免费节点”默认提升成生产级，因为免费 ≠ 稳定，也不等于适合承载你的真实舆情数据。

另外，这个版本把你刚才强调的两件事真正分开了：

采集风险可控 ≠ AI风险可控

前者保护采集器、账号和系统运行；后者保护分析结果、数据隐私和最终判断。

再往上，就是你想要的品牌监测大系统：广州太古汇只是第一个 Workspace，未来换品牌、换客户、换项目，都复用同一套底座。

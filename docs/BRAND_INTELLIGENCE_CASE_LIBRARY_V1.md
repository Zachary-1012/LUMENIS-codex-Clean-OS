# Z-Brand-Core｜Global Brand Intelligence Case Library v1

> 生效日期：2026-09-01
> 用途：为 ZBMP / Global BIL 提供跨品牌、跨行业、跨市场的研究样本与指标设计参考
> 性质：研究资产 / Benchmark 方法库，不是生产事实数据库

## 1. 核心原则

ZBMP 已经拥有大量品牌，不应把少数案例硬编码成系统规则。本库用于从不同商业模型提炼可复用的品牌行为模式，验证 BIL 指标覆盖度，并为 ZBMP 现有品牌建立 Benchmark。

案例必须经过：

`Case → Evidence → Pattern → Hypothesis → Cross-brand Validation → Metric → Shadow → Regression → Production Insight`

外部案例中的具体结果数字只能作为来源方披露的证据，不能直接变成 ZBMP 权重、当前品牌状态或因果系数。

## 2. 第一批跨行业案例矩阵

| Brand / Group | 研究类型 | 应学习能力 |
|---|---|---|
| Jacquemus | 高端设计师 / 视觉社交 | Cultural Signal / Creator / Product / Geography |
| Patagonia | 户外 / 价值观 / 社群 | Community / Values / UGC / Loyalty |
| SHUSHU/TONG | 中国设计师 / 全球化 | Design Identity / Celebrity / Local-to-Global |
| BY FAR | 社交爆发 / 生命周期 | Momentum / Lifecycle / Offline-vs-Social divergence |
| Molly Goddard | 小众设计师 / 审美 | Taste-maker / Cultural relevance / Niche UGC |
| Nike | 全球运动 / Gen Z | Persona / Product / Culture / Community |
| Adidas | 运动 / 音乐 / 艺术 / 合作 | Collaboration / Cultural Network |
| Uniqlo | 全球大众零售 | Product Utility / Local Market / Scale |
| Lululemon | 社群型运动生活方式 | Community / Offline Events / Local Density |
| Glossier | DTC / 社群共创 | Consumer Experience / Advocacy / Co-development |
| Miu Miu | 奢侈时尚 / 社交文化 | Cultural Momentum / Product Symbol |
| Loewe | 奢侈品 / 艺术文化 | Craft / Cultural Collaboration / Event |
| Dr. Martens | 亚文化 / 社群 | Subculture / Identity / Resale |
| On | 新兴运动品牌 | Awareness / Consideration / Athlete / Innovation |
| Gymshark | Creator-first fitness | Creator Network / UGC / Community |
| The Ordinary | 功效护肤 / 教育 | Problem-Solution / Search / Reviews |
| Gentle Monster | 视觉零售 / 全球扩张 | Store Experience / Cultural Installation |
| Aesop | 高端生活方式 / 门店体验 | Sensory Identity / Local Culture |
| Crocs | 产品符号 / 联名 | Collaboration / Customization / Meme / UGC |
| Unilever portfolio | 全球多品牌集团 | Multi-brand / Segmentation / UGC-to-purchase |

## 3. 从案例提炼的核心能力

### Brand Health

品牌健康不能只用 Social Voice 表示。全球品牌 tracking 实践通常同时观察 awareness、consideration、intent、perception、competitor standing，并进行跨市场比较。YouGov 的公开案例即采用品牌、campaign、competitor tracking，并对不同消费者群体进行 purchase funnel 分析；国际时尚品牌案例也按多个市场追踪 awareness、buzz、purchase consideration 和 intent。

BIL 因此保留：

`Awareness / Consideration / Preference / Purchase Intent / Advocacy / Trust / Social Voice / UGC / Cultural Relevance / Offline Presence`

### Social Intelligence

PVH（Calvin Klein / Tommy Hilfiger 母集团）的消费者洞察实践将 social listening 用于 share of voice、产品趋势、消费者情绪和 customer support，并进行品牌与市场的竞争分析。

BIL 应形成：

`Mention → Topic → Emotion → Need → Behavior → Intent → Action`

而不是停留在正负面。

### UGC Intelligence

Unilever 的公开案例显示，UGC/reviews 可用于购买意向、搜索转化、忠诚度、消费者洞察与产品创新；其中具体提升数字属于其案例披露，不能直接迁移为 ZBMP 因果系数。

UGC 应拆成：

`Discovery / Consideration / Purchase / Ownership / Review / Advocacy / Service / Resale / Co-creation`

### Community Intelligence

Glossier 的学术案例研究显示，消费者个人经验分享可以推动线上品牌社区的 engagement、advocacy、品牌学习、共创和消费者关系。

因此增加：

`Repeat Contributors / Peer Recommendation / Consumer Stories / Brand Rituals / Co-creation / Advocacy / Community Retention`

粉丝数不能代替社区强度。

### Creator Intelligence

当前 influencer marketing 越来越重视 micro / niche creator 的社区契合度、内容相关性、可信度和长期合作，而非 follower count 单指标。

因此 Creator Entity 应记录：

`Reach / Engagement / Audience Fit / Brand Fit / Topic Authority / Local Relevance / Conversion Signal / Content Quality / Repeat Collaboration`

## 4. Global Geography Intelligence

跨国 social listening 案例显示，多市场品牌分析需要同时处理国家、语言、品牌 tracking、竞品、内容和 influencer/network analysis。

ZBMP Geography 不应只是 country 字段，应支持：

`Global → Region → Country → State/Province → City → District → Commercial Area → Venue → Store/Stockist`

核心切片：

`Brand × Geography × Platform × Time`

广州只是其中一个 City Scope，不得成为底层架构上限。

## 5. Local-to-Global

本地门店型品牌案例说明，creator-first + UGC + geo targeting 可以同时建立 local brand equity 与整体社交增长。

BIL 应支持：

`Global Brand → Local Market → Local Creator → Local UGC → Local Awareness → Local Store/Sales Signal → Global Learning`

因此全球品牌与城市品牌是同一 Brand Entity 的不同 Geography Scope。

## 6. Campaign Intelligence

Campaign 不应只统计曝光：

`Objective / Market / Audience / Creator / Content / Platform / Reach / Engagement / UGC / Search Lift / Consideration / Purchase Intent / Store Traffic Signal / Post-campaign Momentum`

品牌 tracking 案例已经出现将广告触达与 purchase funnel、消费习惯、购买原因结合的做法，因此 Campaign 必须能进入 Consumer Intelligence。

## 7. Brand Lifecycle

禁止使用：

`声量下降 = 品牌衰退`

应联合观察：

`Social Voice + UGC + Search + Product Heat + Consumer Intent + Creator Activity + Offline Presence + Resale + Community`

重点识别：

`Social ↑ / Sales ↓`
`Social ↓ / Sales ↑`
`Offline ↓ / UGC →`
`Followers ↑ / Trust ↓`

这些指标分裂本身就是 Insight。

BY FAR 等品牌用于验证“社交资产生命周期与线下商业存在度不同步”的假设，但正式数据必须经过时间与 Evidence 验证。

## 8. Product Intelligence

品牌必须下沉到 Product Entity：

`Brand → Product → SKU/Model/Collection → Mention → UGC → Review → Intent → Trend`

时尚品牌不应只统计品牌声量，还要识别包、鞋、系列、颜色、穿搭场景、价格讨论、明星穿着等产品级信号。

## 9. Store / Experience Intelligence

体验驱动品牌的门店不是 store_count。应记录：

`Location / Commercial Area / Opening-Closing / Experience / Store Mention / Visit UGC / Product Trial / Purchase Intent / Service / Local Cultural Fit`

因此 Geography Intelligence 必须能和 Social Intelligence 关联。

## 10. Collaboration Intelligence

合作型品牌应建立：

`Brand A / Brand B / Creator-Artist / Product / Market / Launch Date / Social Voice / UGC / Earned Media / Search Momentum / Post-launch Persistence`

可进一步计算 `Audience Transfer Signal`，但它只能作为分析指标，不能未经验证地声明因果关系。

## 11. Benchmark 四种类型

### Direct
同品类、同价格、同消费者。

### Aspirational
品牌希望成为谁。

### Cultural
消费者文化语境中的竞争对象。

### Attention
争夺同一用户注意力但不一定属于同品类的品牌。

例如 Patagonia 的 Direct 可以是 Arc'teryx / The North Face，而 Cultural / Attention 竞争可以来自更广泛的户外、旅行、生活方式与创作者生态。

## 12. ZBMP 已有品牌：不要重建品牌库

正确路线：

`Existing ZBMP Brand → Brand Entity Resolution → BIL Capability Mapping → Reuse Existing Brand/Campaign/Consumer/Event/Content → Add Missing Fields Only When Necessary`

每个品牌生成：

`Entity Coverage / Platform Coverage / Geography Coverage / Product Coverage / UGC Coverage / Consumer Intent Coverage / Campaign Coverage / Store Coverage / Benchmark Coverage / Lifecycle Coverage`

因此 ZBMP 已有的大量品牌应该成为第一批真实验证池，而不是另外创建一个五品牌数据库。

## 13. Benchmark Dimensions v1

`Brand Awareness`
`Social Voice`
`Organic UGC`
`UGC Share`
`Consumer Intent`
`Purchase Intent`
`Brand Trust`
`Brand Preference`
`Cultural Relevance`
`Creator Influence`
`Community Strength`
`Product Heat`
`Campaign Momentum`
`Search Momentum`
`Local Presence`
`Offline Presence`
`Store Experience`
`Competitive Pressure`
`Lifecycle Momentum`

指标均为可选维度，按品牌类型动态选择，不要求每个品牌全部具备。

## 14. Research Evidence Notes

- YouGov：品牌、campaign、competitor tracking，以及 awareness / purchase funnel / audience segmentation 方法。
- Brandwatch / PVH：social listening、share of voice、产品趋势、情绪与消费者洞察。
- Bazaarvoice / Unilever：UGC 与 reviews 的消费者洞察及购买意向应用。
- Glossier 学术案例：消费者经验分享、advocacy、共创与品牌社区。
- Convosphere：跨国家、语言、竞品、内容、influencer/network 的 social intelligence。
- TikTok / 7 Brew：本地市场 + creator + UGC + geo targeting。
- Vogue Business：micro/niche creator、社区契合度、可信度与长期合作趋势。

## 15. 下一阶段

**不再继续手工扩充品牌名单。**

下一步直接读取 ZBMP 真实品牌库，生成：

`Existing Brands × BIL Capability Coverage Matrix`

然后自动选择具有代表性的 20–50 个现有品牌作为第一批真实 Benchmark，覆盖：

- 国际奢侈
- 设计师
- 大众零售
- 户外
- 运动
- 美妆
- 生活方式
- 餐饮/消费
- 中国品牌全球化
- 本地品牌全球扩张
- 多品牌集团

最终形成可持续扩展的 **Global Brand Case Library + Benchmark Engine**，而不是静态案例列表。

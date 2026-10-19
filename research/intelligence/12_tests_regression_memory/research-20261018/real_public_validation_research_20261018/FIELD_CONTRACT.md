# 字段合同、基线与拒绝条件

原CSV/XLSX保存原拼写；下列是研究解释合同，不是新平台API规范。未获官方细定义的单位不猜测为秒/人数/收入。计数缺失不填0。三个样本均按原行导入；无原始采集时间或修订时间，不能保证as-of可用。

## Online Retail：8列

InvoiceNo：发票标识，C前缀表取消。ID不可求平均；同发票有多行。
StockCode：原始货号，含特殊代码可能非商品，不在缺字典时删。
Description：商品描述，可缺失；不能当品牌归属的确证。
Quantity：每明细数量，保留正负，非订单数。
InvoiceDate：交易日期时间。XLSX Excel 1900日期系统解析（基日1899-12-30），不推断时区。
UnitPrice：sterling单价，保留原精度及零/负；未证明含税或不含税。
CustomerID：名义客户标识，可缺失，不合并缺失客户、不反向识别。
Country：客户居住国，非发货地/门店所在地。

派生signed_line_value=Quantity×UnitPrice；拒绝把此字段命名为审计净营收或利润。预测粒度日历日，总额含所有原行；对照在同样输入、同样损失下进行，不能让一方去掉异常另一方不去。naive7(t)=y(t-7)，same_weekday_mean4(t)=sum(y(t-7j),j=1..4)/4；均不使用t当日及未来数值。MAE为sum(abs(y-pred))/N。

## Facebook：19列

发布前候选7列：Page total likes、Type、Category、Post Month、Post Weekday、Post Hour、Paid。只有Type/月份进入本研究基线；Category的1/2/3业务标签、weekday数值编码/时区未在本批正文独立确认，不用于推荐发布日。Paid的空值是UNKNOWN，不并入0。

事后影响12列：Lifetime Post Total Reach、Lifetime Post Total Impressions、Lifetime Engaged Users、Lifetime Post Consumers、Lifetime Post Consumptions、Lifetime Post Impressions by people who have liked your Page、Lifetime Post reach by people who like your Page、Lifetime People who have liked your Page and engaged with your post、comment、like、share、Total Interactions。

按原标签区分reach、impressions、users、consumers、consumptions与互动事件，不能互换。总互动核验只在三个分量完整时进行。Lifetime表示结果累计成熟时间未给，不自动可作历史时点特征。本数据无平台post ID、正文、资产或实际销售；禁止声称能计算真正创作质量/平台全量/因果转化。

基线1=1–9月所有篇的触达中位数；基线2=1–9月同Type触达中位数；新类型回退基线1。固定10–12月测试，不以Paid/最终曝光等结果字段挑选。两基线均不代表已训练生成模型。互动/触达的逐篇均值与合并比率各有明确权重，不能同名展示。

## Shoppers：18列

Administrative、Informational、ProductRelated：会话中相应页面类别数量。
Administrative_Duration、Informational_Duration、ProductRelated_Duration：相应类别累计停留时长，原页在本批可读段未明确单位；不输出“秒”换算。
BounceRates、ExitRates：原发布方引用的历史Google Analytics页面指标，非当前GA4指标合同。
PageValues：访问页关联的平均价值指标，目标时点可用性待核，不纳入本轮预测。
SpecialDay：与特殊日期接近程度，数值不当日历天。
Month：月份类别，仅10个出现值；June拼写保留，缺月份不补会话。
OperatingSystems、Browser、Region、TrafficType：分类代码，不能以代码大小视为连续量，也不猜code对应平台/国家。
VisitorType：新/回访等类别，非用户身份。
Weekend：布尔类别。
Revenue：是否购买布尔标签，单位不是钱。

常数参照p=非10–12月购买数/相应会话数；Brier=mean((p-y)^2)，未使用后块比例拟合。全负参照p=0；accuracy只代表样本标签命中，recall购买=TP/(TP+FN)，balanced_accuracy=(TPR+TNR)/2。未产生任何真实用户评分或营销行动。

## 后续产品接入统一验收（全部NOT_RUN）

正常样本应能产出有用结论，并保留原件/许可/时间范围/分母与方法；缺失、异常、字段冲突不会被静默转0。原始金额、数量和中间结果可追溯到文件行；只允许显式选择不同业务清理方案。实际产品输出、导出、保存重开与本研究同口径数值匹配。跨平台必须重新映射原生定义与权限，不把2014 Facebook经验当2026抖音、小红书、YouTube、Instagram或韩国平台的统一规律。

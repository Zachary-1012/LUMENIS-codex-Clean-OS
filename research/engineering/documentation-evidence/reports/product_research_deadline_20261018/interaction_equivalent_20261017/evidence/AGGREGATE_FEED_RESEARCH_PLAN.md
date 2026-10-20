# 主体/品牌聚合阅读：下一条独立审核方案

状态：部分独立实现并完成Node/最小DOM合同回归，视觉与产品接入尚未验收。第72入口已有稳定纸卡、双轴导航、异步人工分页和阅读恢复；环形/随机轨迹视觉模式仍待审核实现。它接续现有产品和用户明确新增的聚合展示要求，不另造采集服务、平台页面、事实库或排行榜。最新测试总数见ENTRY_AND_TEST_INDEX.json，不等同覆盖数。

## 用户问题、收益与新增负担
用户需在同一商业主体/品牌查看多个平台材料，不应往返各个平台页面。空间化浏览可以帮助记住邻近内容，但移动目标、轴冲突和装饰会增加误触、阅读负担。目标是减少找回来源与切换平台所需步骤；其价值必须以任务完成时间、误切换次数、回到原材料成功率、键盘步数以及总帧/内存负担验证。不能以“看起来丰富”代替收益。默认只有稳定阅读与明确的上/下平台、前/后内容操作；空间扇面是可关闭的呈现增强。

## 当前来源与边界
- 用户明确要求：所有平台内容回到主体/品牌重构视觉，全球模式可随机选择；环形卡牌/随机轨迹/上下平台/左右内容应考虑密度、轴锁、正文滚动、误触、可访问性与恢复。属于审核设计授权，不是最终官方页面定稿。
- 当前main完整规划、Architecture/Experience/Source Owner仍决定业务、证据、权限与状态。两稿J02/J09/J13/J18关联保留；该新视觉方案不得改变原来源或补指标。
- `lumenis/system/collector/adapters/platform_naming.py`明确Raw原生字段保留，Canonical显式映射，缺失为None/unknown，不填零；类别与注册不证明实时可采。实际registry由原Collector注入，设计不能硬编码六平台上限。
- 最新产品工作树与冻结main是不同版本；在绑定任何真正接口前核读当前Owner。独立示例仅用人工材料，平台能力全部保留UNBOUND/NOT_VERIFIED边界。

## 研究依据与设计判断
已实际读取W3C [Pointer Events Level3](https://www.w3.org/TR/pointerevents3/) §8–9与[APG Carousel Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/carousel/)（2026-10-17）。Level2页面已标superseded，因此后续以Level3研究，不沿用旧规范版本作为当前依据。

Pointer Events的touch-action须在手势开始前确定；不能在pointerdown后切换并期望接管浏览器滚动。设计采用分离操作区域：正文保留原生滚动和缩放；小型可见导航把手负责明确的双轴切换，按钮提供完全等价直接路径。pointercancel、第二指、失焦都取消本次切换，不推断保存。这个区域划分是本项目设计推论，不是规范替我们决定的最佳布局。

APG提醒轮播需明确命名与键盘控制，自动轮转会影响阅读。这里不自动轮转；随机只在用户明确“换一组探索”时发生，随后位置稳定。选中材料与其交互命中区域在按下到抬起之间不能移位；离开、减弱动态或打开详情取消动画。实际读屏和触控兼容仍需设备验收。

## 输入/状态合同草案
注入registry[{id,label,capabilityState}]，不自行从平台名猜能力。注入records，每条包含不可变source/native ID、原文、发布/采集/观测时间各自字段、主体/品牌归属、来源引用、媒体类型、字段缺失原因、指标值/单位/分母/时间/来源及权益可用性。null与0严格不同；没有同口径证明不能合计或排序。

scope={kind:subject|brand|global,id|null}只是审核示例过滤条件，不是授权。生产必须先Owner准入并注入已授权投影；仅传对象id不能获得访问。scope变化清旧gesture/选择，并使用新scope可用记录；异步回包须携带scope/revision，不符不采用。原文与事实不因布局、随机或过滤改变。

state记录当前平台、每平台当前材料ID、过滤、详情展开、正文滚动锚、探索seed、gesture owner及其开始时布局版本。分页cursor是后端给出的opaque值；没有真服务只演示已载入记录，不假装加载全部。当前小样例最多挂载选中与两侧相邻视觉页，完整计数必须来自真实总数或明确“已载入数”。

## 冲突、适配与默认
1. 正文原生滚动优先，正文内拖拽不切平台；文内选区/链接/菜单不被全局手势抢占。
2. 导航把手起手后先过阈值再锁轴，一次只切一个方向；斜向不明确时不切。松手之前可Escape/取消，第二指不抢owner。
3. 点击与拖拽分开；已超过阈值的手势不产生材料点击。被浏览器cancel时不补一次点击。
4. 键盘上下平台、左右同平台材料仅在专属导航控件有焦点时生效；输入、正文选择和读屏普通浏览不被拦截。显式按钮一直存在。
5. 有限透视/厚度/接触阴影帮助层级；高密度、窄屏、减弱动态、未知性能时回到平面固定布局。不要把不同颜色/角度计为独立交互。
6. 所有动力学偏好集中统一设置，默认不需调参；空间布局不会改内容顺序的业务含义。全球探索随机与质量、热度、相关性、权限均无关，并明确标注。
7. 空平台显示无已载入内容；不可用/未配置/失败/无权限分别显示，不把失败当空。重试只恢复该平台范围，不重置别的平台阅读位置；真实登录/API/采集仍由Owner与授权流程处理。

## 必须验证后才算可交接
纯逻辑：registry扩展不改代码、scope隔离、未知平台拒绝、原文/缺失保真、随机可复现且不改变来源、轴锁/第二指/取消、每平台位置保留、边界不越界、分页版本fence、相同条件适配可解释。
适配层：控件命名、焦点返回、正文滚动不触发切换、拖后不误点、失焦/卸载取消、统一设置保存与恢复不丢正文、存储失败明确。
实际浏览器：手机/桌面、触控/键盘/读屏、200%字号、RTL/长文本/缺图、快速切换与分页、帧耗时/内存、减少动态。当前连接边界未解决前不声称通过。
产品接线：与现有Collector/Subject/BrandFocus/Permission/SourceUse/Canonical owner核合同、真实范围和字段、成功失败恢复。示例数据和纯测试不能代替此项。

## 13:31 first implementation evidence and remaining scope
New `aggregate-feed.mjs` separates projection/scope/filtering, deterministic exploration, unknown metric display, pointer owner/axis lock/cancel, adaptation and presentation-only readback from `aggregate-study.mjs` view72. Eight pure contracts and five mounted-adapter contracts passed; integrated suite260/260 with offline rebuild. Default stable paper fan uses only bounded adjacent presentation; reduced/narrow states are flat. The shared tilt preference changes only a display angle and is wired through the unified settings event, not a new business setting. Body content has no pointer-navigation handlers; the small explicitly labelled navigation zone owns its own gestures. No actual platform content is loaded.

Twenty-two labels show scope, not support:15 social-platform labels carry self-authored synthetic materials; retained event/research/web labels deliberately remain empty. This fixture is not a registry sync or proof of collection capability. Product catalogue/Owner scope injection, authentic rows, native field schemas, real pagination cursors and Owner authorization (synthetic asynchronous failure/retry is now implemented; see AGGREGATE_PAGE_INTEGRATION.md), full orthographic image/video bodies and actual browser/RTL/reader/mobile/performance verification remain open. The local bounded data set and three-neighbor projection do not establish production virtualization at arbitrary scale. Random input order never claims relevance, heat, confidence or source quality. The ring/random-trajectory visual variant remains a proposal; this first stable fan is not a claim to have completed every requested spatial mode.

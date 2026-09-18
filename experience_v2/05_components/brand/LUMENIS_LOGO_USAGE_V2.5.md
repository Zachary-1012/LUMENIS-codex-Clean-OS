# LUMENIS Logo Usage Guidelines V2.5
三版本：standard（mark+序境+LUMENIS）、korean（mark+서경+LUMENIS）、symbol（纯图形）。

## 1. 版本选择
| 场景 | 版本 |
|---|---|
| 顶栏/启动/关于/正式封面 | standard |
| 韩文环境（locale=ko） | korean（서경） |
| favicon / app icon / dock / 24–64 小尺寸 / 加载角标 | symbol |
| 深色底 | 对应 *-silver（白银）版本 |

## 2. 安全区（Clearspace）
以 Mark 宽度（symbol viewBox 宽 48 单位）的 0.5 倍 = 24 单位为最小留白，四周不得压字、压线、压图。lockup 以其高度 X 计：上下 ≥ 0.4X，左右 ≥ 0.5X。

## 3. 最小尺寸
- 屏幕 symbol：≥24px 高（24/32/64/128 已导出）；印刷 ≥8mm。
- lockup：屏上 ≥128px 宽；小于该宽度改用 symbol。
- favicon：SVG 矢量优先，回退 32px PNG；app icon 512。
- 24px 时双层 Boundary 仍需清晰（线宽已按 viewBox 归一，不要二次描边）。

## 4. 背景适配
- 浅底（#EBECEE/白/浅雾）：ink 版（黑银）。
- 深底（#060709/黑铬/图片暗部）：silver 版（白银）。
- 复杂图片底：加一层对应金属 scrim（浅底 rgba(251,251,252,.72) / 深底 rgba(6,7,9,.72)），或置于金属面内。
- 禁止把 Icy Point 单独当 logo 使用（Point 只是序轴顶端，不独立成标）。

## 5. 禁用示例（Don'ts）
1. 禁止拉伸/压扁（必须等比，保持 48:64 / 232:64 比例）。
2. 禁止旋转序轴（轴必须垂直，Point 永远在顶端）。
3. 禁止改色为紫/靛/金/彩虹/渐变描边（仅金属灰阶 + 唯一 Icy Point）。
4. 禁止加投影/外发光/玻璃厚效果/描边外框。
5. 禁止更换字体或把 LUMENIS 改成其它字距（mono，letter-spacing .56em）。
6. 禁止使用旧版手写体与彩色液态海版本（归档于 legacy，不出现在当前产品）。
7. 禁止在低对比花底上直接使用、禁止旋转/镜像/加图案填充容器。
8. 禁止把 Mark 与其它图标拼合造成双 Truth 标识。

## 6. 间距与对齐
lockup 中 Mark 与文字基线对齐：CJK 垂直居中于 Mark 几何中心偏上，LAT 紧随其下，间距固定（SVG 内 x=62），不得手调。

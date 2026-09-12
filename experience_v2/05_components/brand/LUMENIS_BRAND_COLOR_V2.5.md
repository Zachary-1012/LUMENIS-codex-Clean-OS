# LUMENIS Brand Color V2.5 — 单色金属 + 唯一 Icy Point
跟随 V2.5 单色金属生态，旧 Logo Brief 的彩色域全部退役；结构哲学保留，色彩不沿用。

## 1. 新品牌色（与 tokens.css 单一真源一致）
### 黑银（Light 主题，SH-01）
| 角色 | Token | HEX |
|---|---|---|
| Mark / 字标主色（墨） | --lum-text | #14161B |
| 金属辅助（text-3，海平线/LAT） | --lum-text-3 | #6A6E78 |
| 唯一 Point（数据生命） | --lum-c-icy-500 | #4FC4E8 |
| 背景 | --lum-bg | #EBECEE |

### 白银（Dark 主题，AI-01，精确反相）
| 角色 | Token | HEX |
|---|---|---|
| Mark / 字标主色（银） | --lum-text | #F2F3F5 |
| 金属辅助 | --lum-text-3 | #9AA0AB |
| 唯一 Point | --lum-c-icy-500 | #6FD6F2 |
| 背景 | --lum-bg | #060709 |

原则：除唯一 Icy Point 外，品牌标识为**无色相金属灰阶**；Icy 只出现在顶端 Point（以及产品内的数据/状态语义），不用于字标描边、不做渐变、不做发光堆叠。

## 2. 旧彩色域退役与映射（旧 Brief 仅历史证据）
| 旧色（不沿用） | 旧 HEX | V2.5 映射 |
|---|---|---|
| Clear Mist（液态海浅底） | — | --lum-bg 铂金雾 #EBECEE / 深 #060709 |
| Opal Lilac（蛋白石紫） | #B8A8FF | 退役 → 金属墨 #14161B / 银 #F2F3F5 |
| Deep Indigo（深靛） | #2A2468 | 退役 → 黑铬渐变 brand-grad |
| Aurora Cyan（极光青） | #8BE7FF | 收敛为唯一 Icy #4FC4E8/#6FD6F2（仅 Point/状态） |
| Pale Gold（淡金） | #F4D38A | 退役（金属感改由灰阶高光表达，不用金） |
| Moon Silver | — | 并入白银灰阶 |
| 手写体字标 | — | 归档；正式字标 = display serif（Fraunces/宋体）+ Geist Mono LAT |

## 3. App Icon
- blackchrome：黑铬圆角底（linear-gradient(168,#2a2d34,#05060a)，圆角 112/512 ≈ 22%），银 Mark + Icy Point。
- silver：白银圆角底（#FFF→#A6ACB6），墨 Mark + Icy Point。
- 单色小尺寸（24/32）Icy Point 仍保留但允许视觉权重略降，禁止变成全灰失去识别点。

## 4. 对比
- 墨 #14161B on #EBECEE 对比 ≈ 14.6:1；银 #F2F3F5 on #060709 对比 ≈ 17:1；均远超 4.5:1。
- Icy #4FC4E8 on 浅底不作文字色，仅 ≥3px 点/线/数据高亮，避免低对比小字。

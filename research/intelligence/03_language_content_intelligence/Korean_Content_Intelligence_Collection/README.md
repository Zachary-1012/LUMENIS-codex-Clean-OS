# Korean Content Intelligence Collection

中文名：韩语内容语境与本地化研究集

状态：`INDEXED`（Collection 内仅部分重点资产完成来源核验）
Owner：Shared Capability / Content & Creation
Production Runtime：None

## 1. 范围

本 Collection 保护：真实语感、韩剧表达机制、字幕与汉化语境、文化转译、敬语与人物关系、情绪克制、中文本地化、中英韩表达、i18n、用户纠偏、研究案例与防回归规则。

它不把韩语研究变成第三产品线，也不允许历史 AI/NLP 建议直接进入生产。

## 2. 全分支谱系事实

Z-Brand-Core 中匹配 Korean/K-drama/Fansub/Translation/i18n 的远程分支共 40 个，但只对应 3 个不同尖端：

| Tip Commit | 分支别名数 | 事实 |
|---|---:|---|
| `b4ba2a89da28a3dbfa2cf650c4091046b0843b17` | 31 | Dialogue Research 提交；是当前原仓 main 的祖先 |
| `4cb2cc19fdde5429768abf1c301037172bf98dc9` | 8 | i18n/创意机制提交；是当前原仓 main 的祖先 |
| `10dd7c42e6d2bc86307c5b08eb53a67f71a09958` | 1 | Fansub Study 分叉提交；不是当前原仓 main 的祖先 |

因此，31 个 `study/translation/final2...final12` 名称不是 31 份增量成果，8 个 `i18n ... final` 名称也不是 8 份增量成果。分支名不决定版本价值。

## 3. 文件与 Blob 统计

| 指标 | 数量 |
|---|---:|
| 历史路径×Blob 版本 | 32 |
| 唯一 Blob | 16 |
| 精确重复附加版本 | 16 |
| 当前清洁库完全相同 Blob | 11 |
| 同路径但内容不同 | 4 |
| 无当前精确等价 | 1 |
| 只存在于历史过程/非当前尖端的路径×Blob 版本 | 5 |
| 近似语义候选 | 1 |

完整来源见 `KOREAN_SOURCE_POINTERS.csv` 与总账 `../../_inventory/ASSET_PROVENANCE_LEDGER.csv`。

## 4. 已确认的知识资产

### K-drama Dialogue Craft

- Current path：`docs/content-learning/KDRAMA_DIALOGUE_RESEARCH_2023_2026.md`
- Blob：`9403f6622f9f1411a029f685e9030f42dd152536`
- Origin Commit：`b4ba2a89da28a3dbfa2cf650c4091046b0843b17`
- 判断：`KEEP / VERIFIED SOURCE LINEAGE`
- 核心知识：场景先行、潜台词、人物专属声音、克制、对照与反转、短句记忆锚、留白、原创迁移。

### Fansub & Chinese Localization Method

- Current Blob：`6007236b829b63ebe7fbfb2b5aed61d216571795`
- Historical fork Blob：`e8bd07ecb97ec01e272fabde3e28f22a36639843`
- Fork Commit：`10dd7c42e6d2bc86307c5b08eb53a67f71a09958`
- 判断：`MERGE KNOWLEDGE / DO NOT COPY OLD FILE OVER CURRENT`
- 核心知识：原意、人物关系、敬语、潜台词、直译/意译/增省译、情绪等值、文化转译、术语统一与人工审校。

两个 Blob 的主体内容近似；历史分叉额外点名 Instagram，当前版本改为“公开社交平台”。该差异被保留为谱系事实，但不是恢复旧文件覆盖当前版本的理由。

### Emotional Resonance & Content Creation

- Blob：`ad924a9eb9eb303092a3109b9547a52258dddc9e`
- 当前多路径完全相同，含 Z-Brand 与 OSAI 学习镜像。
- 判断：`KEEP AS METHOD / EXACT DEDUP`
- 核心知识：具体细节 × 抽象情感 × 张力结构；创作需避免直接复刻受版权保护表达。

### Korean NLP Landscape

- Blob：`97174ccbdccefb9ccefb88dd417f6be9e79ab312`
- 判断：`REFERENCE_ONLY / SOURCE AND LICENSE VERIFICATION PENDING`
- 原因：文件包含模型、性能、发布时间、硬件和第三方来源声明；这些事实具有时效性，且部分来源不是一手官方来源。本轮只保留研究问题、韩语处理难点和候选技术图谱，不提升模型选择或性能数字为当前事实。

## 5. i18n 与防回归资产

当前可见资产包括：

- `static/js/i18n.js` 当前 Blob `848cefbdc13ef3d52597f5159a82e27237e136d7`；
- `scripts/localization_guard.py` 当前 Blob `f7956fa67e795ea1e962196a0cd21fb02d14c050`；
- `scripts/fix_i18n_keys.py`、`scripts/scan_i18n_keys.py`；
- `tests/test_localization_guard.py`；
- I18N Coverage 与 Terminology Audit。

历史 `static/js/xujing-i18n.js` Blob `99074d6f8487dcf5a32553a9e84af4726f8c83bc` 当前无精确尖端等价，只作为历史实现保存。正式命名必须以当前 LUMENIS Canonical Registry 为准，不能恢复旧 `Xujing/ZBMP` 用户可见命名。

## 6. 不可丢失规则

1. 不用“final”文件名判断最终版本；
2. 不把粉丝字幕天然视为优于官方字幕；
3. 不复制完整台词、字幕或受限语料；
4. 内容创作学习表达机制，不模仿具体作品或作者；
5. AI 翻译不得覆盖原文、人工修正或语言事实；
6. 韩文分析必须保留语言、敬语、否定、上下文与置信度；
7. UI 三语完成状态必须由真实 key coverage、渲染和回归证明；
8. Korean NLP 模型与指标在一手来源、许可、真实评测完成前不得 Promotion。

## 7. 待验证

- 当前页面的中英韩完整渲染与移动端长度回归；
- 历史 `xujing-i18n.js` 是否存在当前实现未覆盖的独有 key；
- Korean NLP 文档中模型发布、性能、许可和硬件数字的一手来源；
- 两个用户视频样本的合法音频读取、转录授权和内容分析；
- 韩语舆情规则、样本集与 Evaluation 尚未形成 Production Evidence。
